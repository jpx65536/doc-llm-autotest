# app/llm/llm_client.py
# 统一管理大模型调用，提供配置
import configparser
from pathlib import Path
import dashscope
import logging

from http import HTTPStatus
from app.common import BackoffConfig, RetryableError, retry_with_backoff


class LLMRetryableError(RetryableError):
    """LLM 调用中属于『短暂错误、适合重试』的异常."""
    pass


_llm_backoff_config = BackoffConfig(
    max_retries=5,
    base_delay=1.0,
    factor=2.0,
    jitter=True,
    max_delay=30.0,
    retry_exceptions=(LLMRetryableError,),
)


BASE_DIR = Path(__file__).resolve().parents[2]
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


@retry_with_backoff(_llm_backoff_config)
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

    status = getattr(response, "status_code", None)
    logging.info(f"[LLM RAW] status={status}, resp={response}")

    if status == HTTPStatus.OK:
        answer = response["output"]["choices"][0]["message"]["content"]
        return answer
    
    retryable_status = {
        HTTPStatus.TOO_MANY_REQUESTS,      # 429 限流
        HTTPStatus.INTERNAL_SERVER_ERROR,  # 500
        HTTPStatus.BAD_GATEWAY,            # 502
        HTTPStatus.SERVICE_UNAVAILABLE,    # 503
        HTTPStatus.GATEWAY_TIMEOUT,        # 504
    }

    if status in retryable_status:
        raise LLMRetryableError(
            f"LLM transient error, status={status}, "
            f"code={getattr(response, 'code', None)}, "
            f"message={getattr(response, 'message', None)}"
        )
    
    raise RuntimeError(
        f"LLM call failed, status={status}, "
        f"code={getattr(response, 'code', None)}, "
        f"message={getattr(response, 'message', None)}"
    )