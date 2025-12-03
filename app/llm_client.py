# app/llm_client.py
# 统一管理大模型调用，提供配置
import configparser
from pathlib import Path
import dashscope

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = BASE_DIR / "config.cfg"

config = configparser.ConfigParser()
config.read(CONFIG_FILE, encoding="utf-8")

ALIYUN_API_KEY = config.get("default", "ALIYUN_API_KEY", fallback=None)
ALIYUN_MODEL = config.get("default", "ALIYUN_MODEL")


def init_llm():
    """在Flask启动时调用一次，设置api_key"""
    if not ALIYUN_API_KEY:
        print("[WARN] No ALIYUN_API_KEY configured in config.cfg")
    dashscope.api_key = ALIYUN_API_KEY


def chat_with_model(messages: list[dict]) -> str:
    """调用大模型进行对话

    Args:
        messages (list[dict]): 消息列表，格式参考OpenAI Chat API

    Returns:
        str: 模型回复内容
    """
    if not ALIYUN_API_KEY:
        raise ValueError("No ALIYUN_API_KEY configured")

    response = dashscope.Generation.call(
        model=ALIYUN_MODEL,
        messages=messages,
    )
    print(f"raw response: {response}")
    answer = response["output"]["choices"][0]["message"]["content"]
    return answer