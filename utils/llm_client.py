"""
LLM 客户端模块
支持文本和视觉模型的统一接口
"""

import base64
import io
import logging
from typing import Optional, Dict, Any, List
from PIL import Image
import requests
from openai import OpenAI

from config.config import config
from prompts import DocumentCheckerPrompts

logger = logging.getLogger(__name__)


class LLMClient:
    """文本 LLM 客户端"""
    
    def __init__(self, llm_config=None):
        self.config = llm_config or config.llm
        self.client = OpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url
        )
    
    def chat(self, prompt: str, system_prompt: str = None) -> str:
        """发送聊天请求"""
        try:
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


class VisionClient:
    """视觉模型客户端"""
    
    def __init__(self, vision_config=None):
        self.config = vision_config or config.vision
        self.client = OpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url
        )
    
    def analyze_image(self, image_path: str, prompt: str = None) -> str:
        """分析图像并返回描述"""
        try:
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
