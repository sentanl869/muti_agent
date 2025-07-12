# 文档检查系统

基于 LangGraph 的多 Agent 文档检查工具，用于检查文档的章节完整性和内容规范性。

## 功能特性

### 🔍 双重检查机制
- **章节完整性检查**：根据模板文档检查目标文档的章节结构是否完整
- **内容规范检查**：基于预定义规则检查文档内容是否符合规范

### 🤖 多 Agent 架构
- **文档获取 Agent**：负责从 HTTP 接口获取文档内容
- **结构检查 Agent**：负责章节结构完整性分析
- **内容检查 Agent**：负责内容规范性检查
- **报告生成 Agent**：负责生成 HTML 格式的检查报告

### 📊 智能报告
- 生成美观的 HTML 格式报告
- 包含详细的统计信息和可视化图表
- 支持交互式章节折叠/展开
- 提供改进建议和违规详情

### ⚙️ 灵活配置
- 支持自定义 LLM 模型和 API 配置
- 可配置的内容规范规则（YAML 格式）
- 支持大文档的分块处理（避免超出上下文长度）

## 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  文档获取 Agent  │    │  结构检查 Agent  │    │  内容检查 Agent  │
│                │    │                │    │                │
│ • HTTP 请求     │    │ • 章节对比      │    │ • 规则匹配      │
│ • 内容解析      │    │ • 结构分析      │    │ • 违规检测      │
│ • 数据验证      │    │ • 相似度计算    │    │ • 严重度评估    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │  报告生成 Agent  │
                    │                │
                    │ • 数据整合      │
                    │ • HTML 渲染     │
                    │ • 图表生成      │
                    │ • 文件输出      │
                    └─────────────────┘
```

## 安装部署

### 环境要求
- Python 3.8+
- 支持的 LLM API（OpenAI、Azure OpenAI、或其他兼容接口）

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd document_checker
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **配置系统**
```bash
# 编辑配置文件
vim config/config.py

# 配置 LLM API
# 设置 base_url 和 api_key

# 编辑规范规则（可选）
vim config/rules.yaml
```

4. **创建必要目录**
```bash
mkdir -p logs reports
```

## 配置说明

### LLM 配置
在 `config/config.py` 中配置您的 LLM 服务：

```python
class LLMConfig:
    base_url = "https://your-api-endpoint.com/v1"  # 您的 API 端点
    api_key = "your-api-key"                       # 您的 API 密钥
    model = "gpt-3.5-turbo"                        # 使用的模型
    max_context_length = 64000                     # 最大上下文长度
```

### 规范规则配置
在 `config/rules.yaml` 中定义内容检查规则：

```yaml
text_rules:
  - name: "标题规范"
    pattern: "^[一二三四五六七八九十]+、"
    severity: "warning"
    description: "章节标题应使用中文数字编号"

image_rules:
  - name: "图片标题"
    pattern: "图\\s*\\d+"
    severity: "critical"
    description: "图片必须有标题"
```

## 使用方法

### 基本用法
```bash
python main.py \
  --template-url "https://example.com/template-doc" \
  --target-url "https://example.com/target-doc"
```

### 完整参数示例
```bash
python main.py \
  --template-url "https://example.com/template-doc" \
  --template-page-id "123" \
  --target-url "https://example.com/target-doc" \
  --target-page-id "456" \
  --output-dir "./custom-reports" \
  --log-level "DEBUG" \
  --verbose
```

### 试运行模式
```bash
python main.py \
  --template-url "https://example.com/template" \
  --target-url "https://example.com/target" \
  --dry-run
```

## 命令行参数

| 参数 | 必需 | 说明 |
|------|------|------|
| `--template-url` | ✅ | 模板文档的 URL |
| `--target-url` | ✅ | 目标文档的 URL |
| `--template-page-id` | ❌ | 模板文档的页面 ID |
| `--target-page-id` | ❌ | 目标文档的页面 ID |
| `--output-dir` | ❌ | 报告输出目录 |
| `--log-level` | ❌ | 日志级别 (DEBUG/INFO/WARNING/ERROR) |
| `--config-file` | ❌ | 自定义配置文件路径 |
| `--dry-run` | ❌ | 试运行模式，只验证参数 |
| `--verbose` | ❌ | 详细输出模式 |

## 输出说明

### 检查报告
系统会生成一个 HTML 格式的检查报告，包含：

- **总体概览**：检查状态、通过率、问题统计
- **章节完整性**：缺失章节、额外章节、结构相似度
- **内容规范性**：违规项目、严重程度分布、改进建议
- **详细统计**：章节分布、内容统计、图表可视化

### 日志文件
系统运行日志保存在 `logs/document_checker.log`，包含：
- 详细的执行步骤
- 错误信息和调试信息
- 性能统计

## Docker 部署

### 构建镜像
```bash
docker build -t document-checker .
```

### 运行容器
```bash
docker run -it --rm \
  -v $(pwd)/reports:/app/reports \
  -v $(pwd)/logs:/app/logs \
  -e LLM_API_KEY="your-api-key" \
  -e LLM_BASE_URL="https://your-api-endpoint.com/v1" \
  document-checker \
  --template-url "https://example.com/template" \
  --target-url "https://example.com/target"
```

## 开发指南

### 项目结构
```
document_checker/
├── agents/                 # Agent 模块
│   ├── document_fetcher.py # 文档获取 Agent
│   ├── structure_checker.py # 结构检查 Agent
│   ├── content_checker.py  # 内容检查 Agent
│   └── report_generator.py # 报告生成 Agent
├── config/                 # 配置文件
│   ├── config.py          # 主配置文件
│   ├── rules.yaml         # 规范规则
│   └── cookies.txt        # HTTP 请求 cookies
├── utils/                  # 工具模块
│   ├── llm_client.py      # LLM 客户端
│   ├── html_parser.py     # HTML 解析器
│   └── content_integrator.py # 内容整合器
├── templates/              # 报告模板
│   └── report.html        # HTML 报告模板
├── workflow.py            # LangGraph 工作流
├── main.py               # 主程序入口
└── requirements.txt      # 依赖列表
```

### 扩展开发

#### 添加新的检查规则
1. 在 `config/rules.yaml` 中定义新规则
2. 在 `agents/content_checker.py` 中实现检查逻辑

#### 自定义报告模板
1. 修改 `templates/report.html`
2. 在 `agents/report_generator.py` 中调整数据准备逻辑

#### 添加新的 Agent
1. 在 `agents/` 目录下创建新的 Agent 类
2. 在 `workflow.py` 中集成到工作流

## 故障排除

### 常见问题

**Q: 文档获取失败**
A: 检查网络连接和 URL 有效性，确认 cookies.txt 配置正确

**Q: LLM API 调用失败**
A: 验证 API 密钥和端点配置，检查网络连接和 API 配额

**Q: 内存不足**
A: 调整 `max_context_length` 配置，启用文档分块处理

**Q: 报告生成失败**
A: 检查输出目录权限，确认模板文件完整性

### 调试模式
```bash
python main.py \
  --template-url "..." \
  --target-url "..." \
  --log-level "DEBUG" \
  --verbose
```

## 许可证

本项目采用 MIT 许可证，详见 LICENSE 文件。

## 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 联系方式

如有问题或建议，请通过以下方式联系：
- 提交 GitHub Issue
- 发送邮件至 [your-email@example.com]
