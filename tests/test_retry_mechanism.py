#!/usr/bin/env python3
"""
测试退避重试机制
"""

import logging
import time
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.retry_handler import BackoffRetry, RetryConfig
from utils.llm_client import LLMClient, VisionClient
from agents.document_fetcher import DocumentFetcher

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_retry_config():
    """测试重试配置"""
    print("=== 测试重试配置 ===")
    
    config = RetryConfig(
        max_retries=3,
        initial_delay=0.5,
        max_delay=5.0,
        backoff_factor=2.0,
        enable_jitter=True
    )
    
    retry_handler = BackoffRetry(config)
    
    # 测试延迟计算
    for attempt in range(5):
        delay = retry_handler.calculate_delay(attempt)
        print(f"尝试 {attempt + 1}: 延迟 {delay:.2f} 秒")


def test_retry_with_failure():
    """测试重试机制（模拟失败）"""
    print("\n=== 测试重试机制（模拟失败）===")
    
    config = RetryConfig(
        max_retries=3,
        initial_delay=0.1,
        max_delay=1.0,
        backoff_factor=2.0,
        enable_jitter=False
    )
    
    retry_handler = BackoffRetry(config)
    
    call_count = 0
    
    def failing_function():
        nonlocal call_count
        call_count += 1
        print(f"函数调用第 {call_count} 次")
        if call_count < 3:
            raise ConnectionError(f"模拟连接失败 (第 {call_count} 次)")
        return "成功！"
    
    try:
        start_time = time.time()
        result = retry_handler.execute_with_retry(failing_function)
        end_time = time.time()
        print(f"结果: {result}")
        print(f"总耗时: {end_time - start_time:.2f} 秒")
    except Exception as e:
        print(f"最终失败: {e}")


def test_retry_with_success():
    """测试重试机制（立即成功）"""
    print("\n=== 测试重试机制（立即成功）===")
    
    config = RetryConfig(
        max_retries=3,
        initial_delay=0.1,
        max_delay=1.0,
        backoff_factor=2.0,
        enable_jitter=False
    )
    
    retry_handler = BackoffRetry(config)
    
    def success_function():
        print("函数立即成功")
        return "立即成功！"
    
    try:
        start_time = time.time()
        result = retry_handler.execute_with_retry(success_function)
        end_time = time.time()
        print(f"结果: {result}")
        print(f"总耗时: {end_time - start_time:.2f} 秒")
    except Exception as e:
        print(f"失败: {e}")


def test_llm_client_retry():
    """测试LLM客户端重试机制"""
    print("\n=== 测试LLM客户端重试机制 ===")
    
    # 创建一个自定义的重试配置（更短的延迟用于测试）
    test_retry_config = RetryConfig(
        max_retries=2,
        initial_delay=0.1,
        max_delay=1.0,
        backoff_factor=2.0,
        enable_jitter=False
    )
    
    try:
        client = LLMClient(retry_config=test_retry_config)
        print("LLM客户端创建成功，重试配置已应用")
        print(f"最大重试次数: {client.retry_handler.config.max_retries}")
        print(f"初始延迟: {client.retry_handler.config.initial_delay}")
        print(f"最大延迟: {client.retry_handler.config.max_delay}")
    except Exception as e:
        print(f"LLM客户端创建失败: {e}")


def test_document_fetcher_retry():
    """测试文档获取器重试机制"""
    print("\n=== 测试文档获取器重试机制 ===")
    
    # 创建一个自定义的重试配置
    test_retry_config = RetryConfig(
        max_retries=2,
        initial_delay=0.1,
        max_delay=1.0,
        backoff_factor=2.0,
        enable_jitter=False
    )
    
    try:
        fetcher = DocumentFetcher(retry_config=test_retry_config)
        print("文档获取器创建成功，重试配置已应用")
        print(f"最大重试次数: {fetcher.retry_handler.config.max_retries}")
        print(f"初始延迟: {fetcher.retry_handler.config.initial_delay}")
        print(f"最大延迟: {fetcher.retry_handler.config.max_delay}")
    except Exception as e:
        print(f"文档获取器创建失败: {e}")


def test_max_delay_limit():
    """测试最大延迟限制"""
    print("\n=== 测试最大延迟限制（30秒上限）===")
    
    config = RetryConfig(
        max_retries=10,
        initial_delay=1.0,
        max_delay=30.0,
        backoff_factor=2.0,
        enable_jitter=False
    )
    
    retry_handler = BackoffRetry(config)
    
    print("各次重试的延迟时间:")
    total_delay = 0
    for attempt in range(10):
        delay = retry_handler.calculate_delay(attempt)
        total_delay += delay
        print(f"第 {attempt + 1} 次重试: {delay:.2f} 秒")
    
    print(f"总延迟时间: {total_delay:.2f} 秒")
    print(f"是否符合30秒上限: {'是' if all(retry_handler.calculate_delay(i) <= 30.0 for i in range(10)) else '否'}")


if __name__ == "__main__":
    print("开始测试退避重试机制...\n")
    
    test_retry_config()
    test_retry_with_failure()
    test_retry_with_success()
    test_llm_client_retry()
    test_document_fetcher_retry()
    test_max_delay_limit()
    
    print("\n测试完成！")
