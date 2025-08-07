"""
配置管理模块
管理 LLM API 配置、文档获取配置等
"""

import os
from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class LLMConfig:
    """LLM 配置"""
    base_url: str
    api_key: str
    model: str
    temperature: float = 0.1
    max_tokens: int = 4000
    max_context_length: int = 64000  # 最大上下文长度
    timeout: int = 120
    request_interval: float = 1.0  # 请求间隔（秒），默认1秒
    stream: bool = True  # 是否启用流式输出并自动聚合


@dataclass
class VisionConfig:
    """视觉模型配置"""
    base_url: str
    api_key: str
    model: str
    max_image_size: str = "1024x1024"
    image_quality: str = "high"
    description_detail: str = "detailed"
    request_interval: float = 1.0  # 请求间隔（秒），默认1秒


@dataclass
class RetryConfig:
    """重试配置"""
    max_retries: int = 10
    initial_delay: float = 1.0
    max_delay: float = 30.0
    backoff_factor: float = 2.0
    enable_jitter: bool = True


@dataclass
class DocumentConfig:
    """文档获取配置"""
    cookies_file: str = "config/cookies.txt"
    timeout: int = 30
    max_retries: int = 3  # 保留原有配置以兼容性，但会被 RetryConfig 覆盖
    chunk_size: int = 32000  # 32K 字符，确保不超过模型上下文限制


@dataclass
class ReportConfig:
    """报告生成配置"""
    template_file: str = "templates/report.html"
    output_dir: str = "reports"
    include_images: bool = True


@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = "info"
    log_dir: str = "logs"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5


@dataclass
class CheckConfig:
    """检查功能配置"""
    # 默认配置：结构检查开启，内容检查关闭
    enable_structure_check: bool = True
    enable_content_check: bool = False
    enable_image_check: bool = False  # 图像检查在内容检查内部进行
    
    def get_enabled_checks(self) -> List[str]:
        """获取启用的检查类型列表"""
        enabled = []
        if self.enable_structure_check:
            enabled.append('structure')
        if self.enable_content_check:
            enabled.append('content')
        return enabled
    
    def has_any_check_enabled(self) -> bool:
        """检查是否有任何检查功能启用"""
        return (self.enable_structure_check or 
                self.enable_content_check)


class Config:
    """主配置类"""
    
    def __init__(self):
        self.llm = LLMConfig(
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.siliconflow.cn/v1"),
            api_key=os.getenv("DEEPSEEK_API_KEY", ""),
            model=os.getenv("DEEPSEEK_MODEL", "Pro/deepseek-ai/DeepSeek-V3")
        )
        
        self.vision = VisionConfig(
            base_url=os.getenv("VISION_BASE_URL", "https://api.siliconflow.cn/v1"),
            api_key=os.getenv("VISION_API_KEY", ""),
            model=os.getenv("VISION_MODEL", "Qwen/Qwen2.5-VL-72B-Instruct")
        )
        
        self.document = DocumentConfig()
        self.report = ReportConfig()
        self.logging = LoggingConfig()
        self.retry = RetryConfig()
        
        # 检查功能配置，支持环境变量覆盖
        self.check = CheckConfig(
            enable_structure_check=self._get_bool_env('ENABLE_STRUCTURE_CHECK', True),
            enable_content_check=self._get_bool_env('ENABLE_CONTENT_CHECK', False),
            enable_image_check=self._get_bool_env('ENABLE_IMAGE_CHECK', False)
        )
        
        # 创建输出目录
        os.makedirs(self.report.output_dir, exist_ok=True)
        os.makedirs(self.logging.log_dir, exist_ok=True)
        os.makedirs("temp", exist_ok=True)
    
    def _get_bool_env(self, key: str, default: bool) -> bool:
        """从环境变量获取布尔值"""
        value = os.getenv(key)
        if value is None:
            return default
        return value.lower() in ('true', '1', 'yes', 'on')
    
    def update_llm_config(self, base_url: str = None, api_key: str = None, model: str = None):
        """更新 LLM 配置"""
        if base_url:
            self.llm.base_url = base_url
        if api_key:
            self.llm.api_key = api_key
        if model:
            self.llm.model = model
    
    def update_vision_config(self, base_url: str = None, api_key: str = None, model: str = None):
        """更新视觉模型配置"""
        if base_url:
            self.vision.base_url = base_url
        if api_key:
            self.vision.api_key = api_key
        if model:
            self.vision.model = model
    
    def validate(self) -> bool:
        """验证配置是否完整"""
        if not self.llm.api_key:
            raise ValueError("LLM API key is required")
        if not self.vision.api_key:
            raise ValueError("Vision API key is required")
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "llm": {
                "base_url": self.llm.base_url,
                "model": self.llm.model,
                "temperature": self.llm.temperature,
                "max_tokens": self.llm.max_tokens
            },
            "vision": {
                "base_url": self.vision.base_url,
                "model": self.vision.model,
                "max_image_size": self.vision.max_image_size
            },
            "document": {
                "chunk_size": self.document.chunk_size,
                "timeout": self.document.timeout
            }
        }


# 全局配置实例
config = Config()
