# app/services/doc_check_service.py
from typing import Optional
from ..prompt_loader import load_latest_prompt
from ..llm_client import chat_with_model


def run_doc_check(doc: str,
                  product: Optional[str] = None,
                  feature: Optional[str] = None) -> str:
    """
    使用 latest prompt + 文档内容，调用大模型进行“文档检查”。

    暂时返回的是模型原始回答字符串，
    以后可以改成返回结构化 JSON（错误列表等）。
    """
    prompt = load_latest_prompt()
    if not prompt:
        raise RuntimeError("No prompt available")
    
    user_content_parts = []
    if product:
        user_content_parts.append(f"产品：{product}")

    if feature:
        user_content_parts.append(f"功能点：{feature}")
    
    user_content_parts.append("以下是需要你进行测试/审查的文档内容：")
    user_content_parts.append(doc)
    print(f"------------------user_content_parts: {user_content_parts}-----------------------")

    user_content = "\n\n".join(user_content_parts)

    messages = [
        {
            "role": "system",
            "content": prompt,
        },
        {
            "role": "user",
            "content": user_content,
        },
    ]

    answer = chat_with_model(messages)
    return answer