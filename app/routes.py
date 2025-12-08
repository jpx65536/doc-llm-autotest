# app/routes.py
from flask import jsonify, request, Blueprint, render_template
from .llm.llm_client import chat_with_model
from .prompt_loader import load_latest_prompt
from .llm.doc_check_llm import run_doc_check_structured
from .services import doc_check_service, file_service
from app.llm.llm_client import LLMRetryableError
import logging

bp = Blueprint('main', __name__)


@bp.route("/tasks/page/", methods=["GET"])
def tasks_page():
    """任务管理页面"""
    return render_template("tasks.html")


@bp.route('/')
def hello():
    """测试路由是否通畅"""
    return 'Hello, World!'


@bp.route("/llm_test/")
def llm_test():
    """测试与大模型的对话功能，只用看是否联通即可"""
    try:
        messages = [
            {'role': 'system', 'content': 'You are a helpful assistant.'},
            {'role': 'user', 'content': '你是谁？'}
        ]
        answer = chat_with_model(messages)
        return jsonify({"answer": answer})
    except Exception as e:
        print("LLM error:", repr(e))
        return jsonify({"error": str(e)}), 500
    

@bp.route("/llm_with_prompt/")
def llm_with_prompt():
    """测试最新的Prompt与大模型对话，只用看是否联通即可"""
    prompt = load_latest_prompt()
    if not prompt:
        return jsonify({"error": "No prompt available"}), 500
    try:
        messages = [
            {
                'role': 'system', 
                'content': prompt
            },
            {
                'role': 'user', 
                'content': "请用一两句话，概括一下这个文档测试规范的核心目标。"
            }
        ]
        answer = chat_with_model(messages)
        return jsonify({"answer": answer})
    
    except Exception as e:
        print("LLM with prompt error:", repr(e))
        return jsonify({"error": str(e)}), 500
    

@bp.route("/doc_check/", methods=["POST"])
def doc_check():
    """
    文档检测接口：
    - 入参：JSON { doc, product, feature }
    - 逻辑：读取 latest prompt + doc → 调用通义模型
    - 出参：先返回模型原始回答，后面可以改成结构化 JSON
    """
    data = request.get_json(silent=True) or {}
    doc = data.get("doc", "").strip()
    product = data.get("product", None)
    feature = data.get("feature", None)

    if not doc:
        return jsonify({"error": "No doc provided"}), 400
    
    try:
        result = run_doc_check_structured(doc, product, feature)
        return jsonify(result)
    except LLMRetryableError as e:
        logging.warning(f"LLM backend unavailable after retries: {repr(e)}")
        return jsonify({"error": "LLM service temporarily unavailable"}), 503
    
    except RuntimeError as e:
        logging.error(f"Doc check runtime error: {repr(e)}")
        return jsonify({"error": "Doc check failed: " + str(e)}), 502
    
    except Exception as e:
        logging.exception(f"Unexpected doc_check error")
        return jsonify({"error": "Internal server error"}), 500


@bp.route("/tasks/", methods=["POST"])
def create_doc_task():
    """
    提交文档检查任务
    入参：JSON { task_name, doc }
    出参：JSON { service_code, msg, task_id }

    新的文件上传方式：
        Content-Type: multipart/form-data
        form fields:
            task_name: 文本
            product: 文本（可选）
            feature: 文本（可选）
            file: 文件
        此时 doc 字段会被写成：minio://doc-llm-bucket/{task_id}_{filename}
    """
    if request.content_type and "multipart/form-data" in request.content_type:
        return _create_task_with_file()

    return _create_task_with_json()


def _create_task_with_file():
    """"""
    form = request.form
    files = request.files

    task_name = form.get("task_name")
    product = form.get("product")
    feature = form.get("feature")
    file_obj = files.get("file")

    if task_name is None or not str(task_name).strip():
        return jsonify({"service_code": 4001, "msg": "task_name 是必填字段"}), 400
    if not file_obj:
        return jsonify({"service_code": 4001, "msg": "file 是必填字段"}), 400
    
    task_name = str(task_name).strip()
    try:
        placeholder_doc = "__PENDING_FILE__"
        task_id = doc_check_service.submit_doc_task(task_name=task_name, doc=placeholder_doc, product=product, feature=feature)
        doc_path = file_service.save_task_file(task_id, file_obj)
        doc_check_service.update_task_doc(task_id, doc_path)
        return jsonify({
            "service_code": 2000,
            "msg": "任务创建成功（文件已上传）",
            "task_id": task_id,
            "doc": doc_path,
        })
    except Exception as e:
        logging.exception("Failed to create doc task with file")
        return jsonify({
            "service_code": 5001,
            "msg": "任务创建失败: " + str(e),
        }), 500


def _create_task_with_json():
    """通过 JSON 提交任务的处理逻辑"""
    data = request.get_json(silent=True) or {}
    doc = data.get("doc")
    product = data.get("product")
    feature = data.get("feature")
    task_name = data.get("task_name")
    if doc is None or not str(doc).strip():
        return jsonify({"service_code": 4001, "msg": "doc 是必填字段"}), 400
    if task_name is None or not str(task_name).strip():
        return jsonify({"service_code": 4001, "msg": "task_name 是必填字段"}), 400
    
    doc = str(doc).strip()
    task_name = str(task_name).strip()

    try:
        task_id = doc_check_service.submit_doc_task(task_name, doc, product, feature)
        return jsonify({
            "service_code": 2000,
            "msg": "任务创建成功",
            "task_id": task_id,
        })
    except Exception as e:
        logging.exception("Failed to create doc task")
        return jsonify({
            "service_code": 5001,
            "msg": "任务创建失败: " + str(e),
        }), 500
    

@bp.route("/tasks/<int:task_id>/", methods=["GET"])
def get_doc_task(task_id: int):
    if task_id <= 0:
        return jsonify({"service_code": 4001, "msg": "无效的 task_id"}), 400
    try:
        task_detail = doc_check_service.get_task_detail(task_id)
        if not task_detail:
            return jsonify({"service_code": 4004, "msg": "任务不存在"}), 404
        return jsonify({
            "service_code": 2000,
            "msg": "任务获取成功",
            "task": task_detail,
        })
    except Exception as e:
        logging.exception("Failed to get doc task")
        return jsonify({
            "service_code": 5001,
            "msg": "任务获取失败: " + str(e),
        }), 500
    

@bp.route("/tasks/", methods=["GET"])
def list_doc_tasks():
    """
    获取所有任务列表
    """
    try:
        tasks = doc_check_service.list_all_tasks()
        return jsonify({
            "service_code": 2000,
            "msg": "任务列表获取成功",
            "tasks": tasks,
        })
    except Exception as e:
        logging.exception("Failed to list doc tasks")
        return jsonify({
            "service_code": 5001,
            "msg": "任务列表获取失败: " + str(e),
        }), 500
    

@bp.route("/tasks/delete/", methods=["POST"])
def delete_doc_tasks():
    """
    删除文档检查任务
    入参：JSON { task_ids: [int, int, ...] }
    出参：JSON { service_code, msg, deleted_count }
    """
    data = request.get_json(silent=True) or {}
    task_ids = data.get("task_ids")
    if not task_ids or not isinstance(task_ids, list):
        return jsonify({"service_code": 4001, "msg": "task_ids 必须是非空列表"}), 400
    
    try:
        deleted_count = doc_check_service.delete_tasks(task_ids)
        return jsonify({
            "service_code": 2000,
            "msg": f"成功删除 {deleted_count} 个任务",
            "deleted_count": deleted_count,
        })
    except Exception as e:
        logging.exception("Failed to delete doc tasks")
        return jsonify({
            "service_code": 5001,
            "msg": "任务删除失败: " + str(e),
        }), 500
    

@bp.route("/task/retry/", methods=["POST"])
def retry_task():
    """
    手动重试某个任务
    入参：JSON { task_id }
    出参：JSON { service_code, msg }
    """
    data = request.get_json(silent=True) or {}
    task_id = data.get("task_id")
    if not task_id:
        return jsonify({"service_code": 4001, "msg": "task_id 是必填字段"}), 400

    try:
        task = doc_check_service.retry_task(task_id)
    except doc_check_service.TaskNotFoundError as e:
        return jsonify({"service_code": 4040, "msg": "任务不存在"}), 404
    except doc_check_service.InvalidTaskStatusError as e:
        return jsonify({"service_code": 4003, "msg": str(e)}), 400
    except Exception:
        logging.exception("retry_task error")
        return jsonify({"service_code": 5000, "msg": "内部错误"}), 500
    
    return jsonify({
        "service_code": 2000,
        "msg": "任务已重试，已重新放入队列",
        "task": task.to_dict()
    }), 200
        