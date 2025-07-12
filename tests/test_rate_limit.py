#!/usr/bin/env python3
"""
测试频率控制功能
"""

import time
import logging
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.llm_client import LLMClient, VisionClient, MultiModalClient
from config.config import LLMConfig, VisionConfig

# 设置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_llm_rate_limit():
    """测试LLM客户端频率控制"""
    print("=== 测试 LLM 客户端频率控制 ===")
    
    # 创建测试配置（2秒间隔）
    test_config = LLMConfig(
        base_url="https://api.deepseek.com/v1",
        api_key="test_key",  # 测试用，不会真正发送请求
        model="deepseek-chat",
        request_interval=2.0
    )
    
    client = LLMClient(test_config)
    
    print(f"配置的请求间隔: {client.rate_limiter.interval} 秒")
    
    # 模拟多次请求（不实际发送）
    start_time = time.time()
    for i in range(3):
        print(f"第 {i+1} 次请求开始...")
        request_start = time.time()
        
        # 只测试频率限制，不实际发送请求
        client.rate_limiter.wait_if_needed()
        
        request_end = time.time()
        elapsed = request_end - request_start
        total_elapsed = request_end - start_time
        
        print(f"第 {i+1} 次请求完成，等待时间: {elapsed:.2f} 秒，总耗时: {total_elapsed:.2f} 秒")
    
    print()


def test_vision_rate_limit():
    """测试视觉客户端频率控制"""
    print("=== 测试视觉客户端频率控制 ===")
    
    # 创建测试配置（1.5秒间隔）
    test_config = VisionConfig(
        base_url="https://api.deepseek.com/v1",
        api_key="test_key",
        model="deepseek-vl",
        request_interval=1.5
    )
    
    client = VisionClient(test_config)
    
    print(f"配置的请求间隔: {client.rate_limiter.interval} 秒")
    
    # 模拟多次请求
    start_time = time.time()
    for i in range(3):
        print(f"第 {i+1} 次请求开始...")
        request_start = time.time()
        
        # 只测试频率限制
        client.rate_limiter.wait_if_needed()
        
        request_end = time.time()
        elapsed = request_end - request_start
        total_elapsed = request_end - start_time
        
        print(f"第 {i+1} 次请求完成，等待时间: {elapsed:.2f} 秒，总耗时: {total_elapsed:.2f} 秒")
    
    print()


def test_multimodal_rate_limit():
    """测试多模态客户端频率控制"""
    print("=== 测试多模态客户端频率控制 ===")
    
    client = MultiModalClient()
    
    # 获取当前频率限制信息
    rate_info = client.get_rate_limit_info()
    print(f"当前频率限制: {rate_info}")
    
    # 更新频率限制
    client.update_rate_limits(llm_interval=0.5, vision_interval=0.8)
    
    # 获取更新后的信息
    updated_rate_info = client.get_rate_limit_info()
    print(f"更新后频率限制: {updated_rate_info}")
    
    print()


def test_rate_limit_update():
    """测试频率限制动态更新"""
    print("=== 测试频率限制动态更新 ===")
    
    client = LLMClient()
    
    print(f"初始间隔: {client.rate_limiter.interval} 秒")
    
    # 测试第一次请求
    start_time = time.time()
    client.rate_limiter.wait_if_needed()
    print(f"第1次请求完成，耗时: {time.time() - start_time:.2f} 秒")
    
    # 更新间隔为0.5秒
    client.update_rate_limit(0.5)
    print(f"更新后间隔: {client.rate_limiter.interval} 秒")
    
    # 测试第二次请求
    start_time = time.time()
    client.rate_limiter.wait_if_needed()
    print(f"第2次请求完成，等待时间: {time.time() - start_time:.2f} 秒")
    
    # 测试第三次请求
    start_time = time.time()
    client.rate_limiter.wait_if_needed()
    print(f"第3次请求完成，等待时间: {time.time() - start_time:.2f} 秒")
    
    print()


if __name__ == "__main__":
    print("开始测试频率控制功能...\n")
    
    try:
        test_llm_rate_limit()
        test_vision_rate_limit()
        test_multimodal_rate_limit()
        test_rate_limit_update()
        
        print("✅ 所有测试完成！")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        logger.exception("测试过程中发生错误")
