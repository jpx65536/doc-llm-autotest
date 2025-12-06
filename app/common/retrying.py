# app/common/retrying.py

import time
import random
import functools
import logging
from dataclasses import dataclass
from typing import Callable, Type, Any, Tuple, TypeVar

T = TypeVar('T')


class RetryableError(Exception):
    """自定义可重试异常类型"""
    pass


@dataclass
class BackoffConfig:
    """
    配置指数退避的因子
    """
    max_retries: int = 5          # 最大重试次数
    base_delay: float = 1.0       # 基础延迟时间（秒）
    factor: float = 2.0           # 每次失败后delay = delay * factor
    jitter: bool = True           # 随机抖动比例
    max_delay: float | None = None  # 最大延迟时间（秒）
    retry_exceptions: Tuple[Type[Exception], ...] = (RetryableError,)  # 可重试的异常类型


def _calc_sleep(delay: float, cfg: BackoffConfig) -> float:
    """根据配置计算本次睡眠等待时间"""
    sleep_time = delay

    if cfg.jitter:
        sleep_time = random.uniform(delay * 0.8, delay * 1.2)

    if cfg.max_delay is not None:
        sleep_time = min(sleep_time, cfg.max_delay)

    return sleep_time


def retry_with_backoff(
    cfg: BackoffConfig | None = None,
    **cfg_kwargs: Any,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """指数退避装饰器
    @retry_with_backoff(BackoffConfig(max_retries=3, base_delay=0.5))

    @retry_with_backoff(max_retries=3, base_delay=0.5)
    """
    if cfg is None:
        cfg = BackoffConfig(**cfg_kwargs)

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            delay = cfg.base_delay
            last_exc: BaseException | None = None

            for attempt in range(cfg.max_retries):
                try:
                    return func(*args, **kwargs)
                except cfg.retry_exceptions as e:
                    last_exc = e

                    # 最后一次重试失败，抛出异常
                    if attempt == cfg.max_retries - 1:
                        logging.error(f"[RETRY] final failure after {cfg.max_retries} attempts: {e}")
                        raise

                    sleep_time = _calc_sleep(delay, cfg)
                    logging.error(
                        f"[RETRY] func={func.__name__}, attempt={attempt+1}/{cfg.max_retries}, "
                        f"sleep={sleep_time:.2f}s, err={e}"
                    )
                    time.sleep(sleep_time)
                    delay *= cfg.factor

            if last_exc is not None:
                raise last_exc
            raise RuntimeError("Unreachable code in retry_with_backoff")
        return wrapper
    return decorator