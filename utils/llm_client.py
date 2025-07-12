"""
LLM 客户端模块
支持文本和视觉模型的统一接口
"""

import base64
import io
import logging
import time
from typing import Optional, Dict, Any, List
from PIL import Image
import requests
from openai import OpenAI

from config.config import config
from prompts import DocumentCheckerPrompts

logger = logging.getLogger(__name__)


class RateLimiter:
    """请求频率限制器"""
    
    def __init__(self, interval: float = 1.0):
        """
        初始化频率限制器
        
        Args:
            interval: 请求间隔时间（秒）
        """
        self.interval = interval
        self.last_request_time = 0.0
    
    def wait_if_needed(self):
        """如果需要，等待到下一个允许的请求时间"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.interval:
            wait_time = self.interval - time_since_last_request
            logger.debug(f"频率限制：等待 {wait_time:.2f} 秒")
            time.sleep(wait_time)
        
        self.last_request_time = time.time()
    
    def update_interval(self, interval: float):
        """更新请求间隔"""
        self.interval = interval


class LLMClient:
    """文本 LLM 客户端"""
    
    def __init__(self, llm_config=None):
        self.config = llm_config or config.llm
        self.client = OpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url
        )
        self.rate_limiter = RateLimiter(self.config.request_interval)
    
    def chat(self, prompt: str, system_prompt: str = None) -> str:
        """发送聊天请求"""
        try:
            # 频率限制
            self.rate_limiter.wait_if_needed()
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                timeout=self.config.timeout
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"LLM 请求失败: {e}")
            raise
    
    def chat_with_context(self, messages: List[Dict[str, str]]) -> str:
        """发送带上下文的聊天请求"""
        try:
            # 频率限制
            self.rate_limiter.wait_if_needed()
            
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                timeout=self.config.timeout
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"LLM 上下文请求失败: {e}")
            raise
    
    def update_rate_limit(self, interval: float):
        """更新请求频率限制"""
        self.rate_limiter.update_interval(interval)
        logger.info(f"LLM 客户端请求间隔已更新为 {interval} 秒")


class VisionClient:
    """视觉模型客户端"""
    
    def __init__(self, vision_config=None):
        self.config = vision_config or config.vision
        self.client = OpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url
        )
        self.rate_limiter = RateLimiter(self.config.request_interval)
    
    def analyze_image(self, image_path: str, prompt: str = None) -> str:
        """分析图像并返回描述"""
        try:
            # 频率限制
            self.rate_limiter.wait_if_needed()
            
            # 读取并处理图像
            image_base64 = self._encode_image(image_path)
            
            # 默认提示词
            if not prompt:
                prompt = DocumentCheckerPrompts.IMAGE_ANALYSIS_DEFAULT
            
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}",
                                "detail": self.config.description_detail
                            }
                        }
                    ]
                }
            ]
            
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                max_tokens=1000,
                timeout=60
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"图像分析失败: {e}")
            return f"图像分析失败: {str(e)}"
    
    def _encode_image(self, image_path: str) -> str:
        """将图像编码为 base64"""
        try:
            # 打开并调整图像大小
            with Image.open(image_path) as img:
                # 转换为 RGB 模式
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # 调整图像大小
                max_size = tuple(map(int, self.config.max_image_size.split('x')))
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # 转换为 base64
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=85)
                image_bytes = buffer.getvalue()
                
                return base64.b64encode(image_bytes).decode('utf-8')
                
        except Exception as e:
            logger.error(f"图像编码失败: {e}")
            raise
    
    def update_rate_limit(self, interval: float):
        """更新请求频率限制"""
        self.rate_limiter.update_interval(interval)
        logger.info(f"视觉客户端请求间隔已更新为 {interval} 秒")


class MultiModalClient:
    """多模态客户端，整合文本和视觉功能"""
    
    def __init__(self):
        self.text_client = LLMClient()
        self.vision_client = VisionClient()
    
    def analyze_text(self, text: str, system_prompt: str = None) -> str:
        """分析文本内容"""
        return self.text_client.chat(text, system_prompt)
    
    def analyze_image(self, image_path: str, prompt: str = None) -> str:
        """分析图像内容"""
        return self.vision_client.analyze_image(image_path, prompt)
    
    def analyze_mixed_content(self, text: str, image_paths: List[str], prompt: str) -> str:
        """分析混合内容（文本+图像）"""
        try:
            # 首先分析所有图像
            image_descriptions = []
            for i, image_path in enumerate(image_paths, 1):
                image_prompt = DocumentCheckerPrompts.IMAGE_DESCRIPTION_FOR_MIXED_CONTENT.format(image_number=i)
                description = self.analyze_image(image_path, image_prompt)
                image_descriptions.append(f"图片{i}描述: {description}")
            
            # 使用 PromptBuilder 构建混合内容分析提示词
            from prompts import PromptBuilder
            full_prompt = PromptBuilder.build_mixed_content_analysis_prompt(prompt, text, image_descriptions)
            return self.text_client.chat(full_prompt)
            
        except Exception as e:
            logger.error(f"混合内容分析失败: {e}")
            raise
    
    def update_config(self, llm_config=None, vision_config=None):
        """更新配置"""
        if llm_config:
            self.text_client = LLMClient(llm_config)
        if vision_config:
            self.vision_client = VisionClient(vision_config)
    
    def update_rate_limits(self, llm_interval: float = None, vision_interval: float = None):
        """更新请求频率限制"""
        if llm_interval is not None:
            self.text_client.update_rate_limit(llm_interval)
        if vision_interval is not None:
            self.vision_client.update_rate_limit(vision_interval)
        
        logger.info("多模态客户端频率限制已更新")
    
    def get_rate_limit_info(self) -> Dict[str, float]:
        """获取当前频率限制信息"""
        return {
            "llm_interval": self.text_client.rate_limiter.interval,
            "vision_interval": self.vision_client.rate_limiter.interval
        }
