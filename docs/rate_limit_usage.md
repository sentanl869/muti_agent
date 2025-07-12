# LLM 客户端频率控制使用指南

## 概述

本项目的 LLM 客户端现在支持可配置的请求频率控制，可以有效防止 API 调用过于频繁而触发限流。

## 功能特性

- ✅ 支持文本和视觉模型的独立频率控制
- ✅ 默认请求间隔为 1 秒
- ✅ 支持运行时动态调整频率
- ✅ 透明集成，不影响现有代码调用方式
- ✅ 详细的日志记录

## 配置方式

### 1. 通过配置文件

在 `config/config.py` 中，可以通过环境变量或直接修改配置：

```python
# 设置 LLM 请求间隔（秒）
llm_config.request_interval = 2.0

# 设置视觉模型请求间隔（秒）
vision_config.request_interval = 1.5
```

### 2. 通过环境变量

```bash
# 设置请求间隔
export LLM_REQUEST_INTERVAL=2.0
export VISION_REQUEST_INTERVAL=1.5
```

### 3. 运行时动态调整

```python
from utils.llm_client import LLMClient, VisionClient, MultiModalClient

# 单独调整 LLM 客户端
llm_client = LLMClient()
llm_client.update_rate_limit(2.0)  # 设置为 2 秒间隔

# 单独调整视觉客户端
vision_client = VisionClient()
vision_client.update_rate_limit(1.5)  # 设置为 1.5 秒间隔

# 批量调整多模态客户端
multimodal_client = MultiModalClient()
multimodal_client.update_rate_limits(
    llm_interval=2.0,
    vision_interval=1.5
)

# 查看当前频率限制
rate_info = multimodal_client.get_rate_limit_info()
print(rate_info)  # {'llm_interval': 2.0, 'vision_interval': 1.5}
```

## 使用示例

### 基本使用

```python
from utils.llm_client import LLMClient

# 创建客户端（使用默认 1 秒间隔）
client = LLMClient()

# 正常调用，自动应用频率控制
response1 = client.chat("你好")  # 立即执行
response2 = client.chat("再见")  # 等待 1 秒后执行
```

### 自定义配置

```python
from config.config import LLMConfig
from utils.llm_client import LLMClient

# 创建自定义配置
custom_config = LLMConfig(
    base_url="https://api.deepseek.com/v1",
    api_key="your_api_key",
    model="deepseek-chat",
    request_interval=3.0  # 3 秒间隔
)

# 使用自定义配置创建客户端
client = LLMClient(custom_config)
```

### 多模态使用

```python
from utils.llm_client import MultiModalClient

client = MultiModalClient()

# 文本分析（受 LLM 频率限制）
text_result = client.analyze_text("分析这段文本")

# 图像分析（受视觉模型频率限制）
image_result = client.analyze_image("path/to/image.jpg")

# 混合内容分析（同时受两种频率限制）
mixed_result = client.analyze_mixed_content(
    text="文本内容",
    image_paths=["image1.jpg", "image2.jpg"],
    prompt="分析提示"
)
```

## 日志输出

启用 DEBUG 级别日志可以看到频率控制的详细信息：

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# 输出示例：
# 2025-07-13 01:23:45,346 - DEBUG - 频率限制：等待 2.00 秒
# 2025-07-13 01:23:45,346 - INFO - LLM 客户端请求间隔已更新为 2.0 秒
```

## 性能影响

- **首次请求**：无延迟
- **后续请求**：根据配置的间隔时间等待
- **内存开销**：每个客户端实例增加约 100 字节
- **CPU 开销**：几乎可忽略不计

## 最佳实践

1. **根据 API 限制调整**：根据你使用的 API 服务的限流策略调整间隔时间
2. **区分场景**：批量处理时可以设置较长间隔，交互式应用可以设置较短间隔
3. **监控日志**：通过日志监控频率控制的效果
4. **动态调整**：根据实际使用情况动态调整频率限制

## 故障排除

### 问题：请求仍然被限流
**解决方案**：增加 `request_interval` 的值

### 问题：响应太慢
**解决方案**：减少 `request_interval` 的值，但要确保不超过 API 限制

### 问题：频率控制不生效
**解决方案**：检查配置是否正确加载，查看日志输出

## 测试

运行测试验证功能：

```bash
# 激活虚拟环境
.\.venv\Scripts\Activate.ps1

# 运行测试
python tests/test_rate_limit.py
```

## 向后兼容性

- ✅ 现有代码无需修改
- ✅ 默认配置保持 1 秒间隔
- ✅ 所有现有 API 保持不变
