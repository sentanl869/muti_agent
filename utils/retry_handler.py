"""
重试处理器模块
提供带退避等待的重试机制
"""

import time
import random
import logging
from typing import Callable, Any, Type, Tuple, Optional
from functools import wraps
import requests
from openai import OpenAI

logger = logging.getLogger(__name__)


class RetryConfig:
    """重试配置类"""
    
    def __init__(self,
                 max_retries: int = 10,
                 initial_delay: float = 1.0,
                 max_delay: float = 30.0,
                 backoff_factor: float = 2.0,
                 enable_jitter: bool = True,
                 retryable_exceptions: Tuple[Type[Exception], ...] = None):
        """
        初始化重试配置
        
        Args:
            max_retries: 最大重试次数
            initial_delay: 初始延迟时间（秒）
            max_delay: 最大延迟时间（秒）
            backoff_factor: 退避因子
            enable_jitter: 是否启用随机抖动
            retryable_exceptions: 可重试的异常类型
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.enable_jitter = enable_jitter
        
        # 默认可重试的异常类型
        if retryable_exceptions is None:
            self.retryable_exceptions = (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.HTTPError,
                ConnectionError,
                TimeoutError,
                Exception  # OpenAI 相关异常的基类
            )
        else:
            self.retryable_exceptions = retryable_exceptions


class BackoffRetry:
    """退避重试处理器"""
    
    def __init__(self, config: RetryConfig):
        """
        初始化退避重试处理器
        
        Args:
            config: 重试配置
        """
        self.config = config
    
    def calculate_delay(self, attempt: int) -> float:
        """
        计算延迟时间
        
        Args:
            attempt: 当前重试次数（从0开始）
            
        Returns:
            延迟时间（秒）
        """
        # 指数退避计算
        delay = self.config.initial_delay * (self.config.backoff_factor ** attempt)
        
        # 限制最大延迟时间
        delay = min(delay, self.config.max_delay)
        
        # 添加随机抖动（±20%）
        if self.config.enable_jitter:
            jitter_range = delay * 0.2
            jitter = random.uniform(-jitter_range, jitter_range)
            delay = max(0, delay + jitter)
        
        return delay
    
    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """
        判断是否应该重试
        
        Args:
            exception: 发生的异常
            attempt: 当前重试次数
            
        Returns:
            是否应该重试
        """
        # 检查重试次数
        if attempt >= self.config.max_retries:
            return False
        
        # 检查异常类型
        if not isinstance(exception, self.config.retryable_exceptions):
            return False
        
        # 特殊处理 HTTP 错误
        if isinstance(exception, requests.exceptions.HTTPError):
            if hasattr(exception, 'response') and exception.response is not None:
                status_code = exception.response.status_code
                # 4xx 错误（除了 429）通常不应该重试
                if 400 <= status_code < 500 and status_code != 429:
                    return False
        
        return True
    
    def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """
        执行函数并在失败时重试
        
        Args:
            func: 要执行的函数
            *args: 函数参数
            **kwargs: 函数关键字参数
            
        Returns:
            函数执行结果
            
        Raises:
            最后一次执行的异常
        """
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                logger.debug(f"执行函数 {func.__name__}，尝试 {attempt + 1}/{self.config.max_retries + 1}")
                result = func(*args, **kwargs)
                
                if attempt > 0:
                    logger.info(f"函数 {func.__name__} 在第 {attempt + 1} 次尝试后成功")
                
                return result
                
            except Exception as e:
                last_exception = e
                
                if not self.should_retry(e, attempt):
                    logger.error(f"函数 {func.__name__} 执行失败，不再重试: {e}")
                    raise e
                
                if attempt < self.config.max_retries:
                    delay = self.calculate_delay(attempt)
                    logger.warning(f"函数 {func.__name__} 执行失败 (尝试 {attempt + 1}/{self.config.max_retries + 1}): {e}")
                    logger.info(f"等待 {delay:.2f} 秒后重试...")
                    time.sleep(delay)
        
        # 如果所有重试都失败了
        logger.error(f"函数 {func.__name__} 在 {self.config.max_retries + 1} 次尝试后仍然失败")
        raise last_exception


def retry_with_backoff(config: RetryConfig = None):
    """
    重试装饰器
    
    Args:
        config: 重试配置，如果为 None 则使用默认配置
        
    Returns:
        装饰器函数
    """
    if config is None:
        config = RetryConfig()
    
    retry_handler = BackoffRetry(config)
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return retry_handler.execute_with_retry(func, *args, **kwargs)
        return wrapper
    
    return decorator


# 预定义的重试配置
DEFAULT_RETRY_CONFIG = RetryConfig(
    max_retries=10,
    initial_delay=1.0,
    max_delay=30.0,
    backoff_factor=2.0,
    enable_jitter=True
)

LLM_RETRY_CONFIG = RetryConfig(
    max_retries=10,
    initial_delay=1.0,
    max_delay=30.0,
    backoff_factor=2.0,
    enable_jitter=True,
    retryable_exceptions=(
        ConnectionError,
        TimeoutError,
        Exception  # 包含 OpenAI 的各种异常
    )
)

HTTP_RETRY_CONFIG = RetryConfig(
    max_retries=10,
    initial_delay=1.0,
    max_delay=30.0,
    backoff_factor=2.0,
    enable_jitter=True,
    retryable_exceptions=(
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.HTTPError,
        ConnectionError,
        TimeoutError
    )
)
