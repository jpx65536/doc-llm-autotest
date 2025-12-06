# app/routes.py
from flask import jsonify, request
from .llm_client import chat_with_model
from .prompt_loader import load_latest_prompt
from .services.doc_check_service import run_doc_check_structured
from app.llm_client import LLMRetryableError
import logging

def register_routes(app):
    """
    把所有路由注册到传入的app上
    """
    @app.route('/')
    def hello():
        """测试路由是否通畅"""
        return 'Hello, World!'


    @app.route("/llm_test/")
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
        

    @app.route("/llm_with_prompt/")
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
        
    
    @app.route("/doc_check/", methods=["POST"])
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
