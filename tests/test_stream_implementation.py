#!/usr/bin/env python3
"""
测试流式输出转非流式输出的实现
"""

import os
import sys
import unittest
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.config import config
from utils.llm_client import LLMClient

class TestStreamImplementation(unittest.TestCase):
    """测试流式输出转非流式输出的实现"""
    
    def setUp(self):
        """测试前设置"""
        # 检查API密钥
        if not config.llm.api_key:
            self.skipTest("未设置 DEEPSEEK_API_KEY 环境变量")
    
    def tearDown(self):
        """测试后清理"""
        # 恢复默认配置
        config.llm.stream = False
    
    def test_non_stream_mode(self):
        """测试非流式模式"""
        print("\n=== 测试非流式模式 ===")
        
        # 确保流式模式关闭
        config.llm.stream = False
        
        client = LLMClient()
        
        response = client.chat("你好，请简单介绍一下你自己")
        
        # 验证响应
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)
        print(f"非流式响应: {response[:100]}...")
        print("✓ 非流式模式测试成功")
    
    def test_stream_mode(self):
        """测试流式模式"""
        print("\n=== 测试流式模式 ===")
        
        # 启用流式模式
        config.llm.stream = True
        
        client = LLMClient()
        
        response = client.chat("你好，请简单介绍一下你自己")
        
        # 验证响应
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)
        print(f"流式聚合响应: {response[:100]}...")
        print("✓ 流式模式测试成功")
    
    def test_context_chat_non_stream(self):
        """测试带上下文的非流式聊天"""
        print("\n=== 测试带上下文的非流式聊天 ===")
        
        # 测试非流式
        config.llm.stream = False
        client = LLMClient()
        
        messages = [
            {"role": "system", "content": "你是一个有用的助手"},
            {"role": "user", "content": "你好"}
        ]
        
        response = client.chat_with_context(messages)
        
        # 验证响应
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)
        print(f"非流式上下文响应: {response[:50]}...")
        print("✓ 非流式上下文聊天测试成功")
    
    def test_context_chat_stream(self):
        """测试带上下文的流式聊天"""
        print("\n=== 测试带上下文的流式聊天 ===")
        
        # 测试流式
        config.llm.stream = True
        client = LLMClient()
        
        messages = [
            {"role": "system", "content": "你是一个有用的助手"},
            {"role": "user", "content": "你好"}
        ]
        
        response = client.chat_with_context(messages)
        
        # 验证响应
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)
        print(f"流式上下文响应: {response[:50]}...")
        print("✓ 流式上下文聊天测试成功")
    
    def test_mode_switching(self):
        """测试模式切换"""
        print("\n=== 测试模式切换 ===")
        
        client = LLMClient()
        test_prompt = "说一个数字"
        
        # 测试非流式
        config.llm.stream = False
        response1 = client.chat(test_prompt)
        
        # 测试流式
        config.llm.stream = True
        response2 = client.chat(test_prompt)
        
        # 验证两种模式都能正常工作
        self.assertIsInstance(response1, str)
        self.assertIsInstance(response2, str)
        self.assertGreater(len(response1), 0)
        self.assertGreater(len(response2), 0)
        
        print(f"非流式响应: {response1[:30]}...")
        print(f"流式响应: {response2[:30]}...")
        print("✓ 模式切换测试成功")

def run_manual_test():
    """手动运行测试的函数"""
    print("开始测试流式输出转非流式输出实现...")
    
    # 检查API密钥
    if not config.llm.api_key:
        print("⚠️  警告: 未设置 DEEPSEEK_API_KEY 环境变量")
        print("请在 PowerShell 中设置环境变量后再运行测试:")
        print("$env:DEEPSEEK_API_KEY='your_api_key_here'")
        return
    
    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromTestCase(TestStreamImplementation)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 总结结果
    print(f"\n=== 测试总结 ===")
    total = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    passed = total - failures - errors
    
    print(f"通过: {passed}/{total}")
    
    if failures == 0 and errors == 0:
        print("🎉 所有测试通过！流式输出转非流式输出实现成功")
    else:
        print("❌ 部分测试失败，请检查实现")
        if failures:
            print(f"失败: {failures}")
        if errors:
            print(f"错误: {errors}")

if __name__ == "__main__":
    run_manual_test()
