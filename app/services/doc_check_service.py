# app/services/doc_check_service.py
from typing import Optional
from ..prompt_loader import load_latest_prompt
from ..llm_client import chat_with_model
import re


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


def parse_doc_check_answer(answer: str) -> dict:
    """
    把大模型返回的“文本报告”解析成结构化 bug 列表。

    约定格式示例：
      问题编号：#001
      问题类型：术语错误
      问题描述：xxx
      优化建议：yyy

    Args:
        answer (str): 模型返回的原始回答字符串

    Returns:
        dict: 解析后的结构化结果
    """
    bugs = []
    # 注意中文、英文类型冒号都要匹配到来
    segments = re.split(r'问题编号[:：]', answer)
    print(f"[parse_doc_check_answer] split segments: {len(segments)}")
    for seg in segments[1:]:
        seg = seg.strip()
        if not seg:
            continue

        m = re.match(r"[#﹟]?\s*(\d+)\s*(.*)", seg, re.S)
        if m:
            bug_id =m.group(1)
            rest = m.group(2).strip()
        else:
            bug_id = None
            rest = seg

        lines = [l.strip() for l in rest.splitlines() if l.strip()]
        bug = {"id": bug_id}
        for line in lines:
            if line.startswith("问题类型"):
                bug["type"] = line.split("：", 1)[-1].strip()
            elif line.startswith("问题描述"):
                bug["description"] = line.split("：", 1)[-1].strip()
            elif line.startswith("优化建议"):
                bug["suggestion"] = line.split("：", 1)[-1].strip()
            else:
                bug.setdefault("extra", []).append(line)

        bugs.append(bug)

    return {
        "bugs": bugs,
        "raw_answer": answer,}


def run_doc_check_structured(doc: str,
                             product: Optional[str] = None,
                             feature: Optional[str] = None) -> dict:
    """
    进行文档检测，并返回结构化结果。

    Args:
        doc (str): 待检测文档内容
        product (Optional[str], optional): 产品名称. Defaults to None.
        feature (Optional[str], optional): 功能点名称. Defaults to None.

    Returns:
        dict: 结构化检测结果
    """
    answer = run_doc_check(doc, product, feature)
    structured_result = parse_doc_check_answer(answer)
    structured_result['meta'] = {
        "product": product,
        "feature": feature,
    }
    return structured_result