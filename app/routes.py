# app/routes.py
from flask import jsonify, request
from .llm_client import chat_with_model
from .prompt_loader import load_latest_prompt
from .services.doc_check_service import run_doc_check_structured

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
        """测试与大模型的对话功能"""
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
        """使用最新的Prompt与大模型对话"""
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
        
        except Exception as e:
            print("Doc check error:", repr(e))
            return jsonify({"error": str(e)}), 500
