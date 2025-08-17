"""
统一的 Prompt 管理模块
包含所有 LLM 相关的提示词
"""


class DocumentCheckerPrompts:
    """文档检查器相关的提示词"""
    
    # 内容规范检查提示词
    CONTENT_COMPLIANCE_CHECK = """请根据以下文档规范检查章节内容，找出所有违反规范的地方：

## 文档规范要求：
{rules_text}

## 待检查的章节内容：
{chapter_content}

## 检查要求：
1. 仔细检查章节内容是否违反了上述任何规范
2. 对于每个违规项，请提供：
   - 违反的具体规范
   - 违规的具体内容（引用原文）
   - 违规内容的位置描述
   - 改进建议

## 输出格式：
请按以下格式输出检查结果：

违规项1:
规范: [违反的具体规范]
内容: [违规的具体内容]
位置: [违规内容在章节中的位置]
建议: [具体的改进建议]

违规项2:
...

如果没有发现违规项，请回答"未发现违规项"。

请开始检查："""

    # 图像描述提示词
    IMAGE_DESCRIPTION = """请详细描述这张图片的内容，特别关注以下方面：

1. **图片类型**: 确定这是什么类型的图片（截图、流程图、架构图、数据图表、界面图等）

2. **主要内容**: 描述图片的主要内容和信息

3. **文字信息**: 如果图片中包含文字，请准确识别并记录

4. **图表元素**: 如果是图表，请描述：
   - 标题和标签
   - 坐标轴信息
   - 图例说明
   - 数据内容

5. **技术细节**: 如果是技术图表，请描述：
   - 组件和模块
   - 连接关系
   - 流程步骤
   - 关键信息

6. **规范相关**: 特别注意可能与文档规范相关的内容：
   - 是否有清晰的标题
   - 是否有必要的说明
   - 图片质量是否清晰
   - 信息是否完整

请用中文回答，描述要详细且准确。"""

    # 图像分析默认提示词
    IMAGE_ANALYSIS_DEFAULT = """请详细描述这张图片的内容，特别关注以下方面：
1. 图片类型（截图、图表、流程图、架构图等）
2. 主要内容和信息
3. 文字内容（如果有）
4. 图表元素（标题、标签、图例等）
5. 技术细节和关键信息
请用中文回答，描述要详细且准确。"""

    # 章节标题相似度判断提示词
    CHAPTER_TITLE_SIMILARITY = """请判断以下两个章节标题是否表达相同或相似的含义：

模板标题: {title1}
目标标题: {title2}

## 判断规则：

### 1. 精确匹配
如果两个标题完全相同或仅有微小的格式差异（如空格、标点符号），则判断为"是"。

### 2. 语义匹配
如果两个标题表达相同的概念或主题，即使用词不完全相同，也判断为"是"。

### 3. 样本章节匹配（重要）
**特别注意**：如果模板标题是样本性质的泛化表达，需要采用更灵活的匹配标准：

#### 3.1 模块/组件样本匹配
- 模板标题包含"模块1"、"模块2"、"模块X"等泛化表达时，目标标题如果是具体的模块实现，则判断为"是"
- 示例：
  - "4.6.1.3.1.模块1安全设计" ↔ "4.6.1.3.1.用户认证模块安全设计" → "是"
  - "4.6.1.3.2.模块2安全设计" ↔ "4.6.1.3.2.数据处理模块安全设计" → "是"
  - "组件A功能说明" ↔ "Redis缓存组件功能说明" → "是"

#### 3.2 泛化词汇样本匹配
- 模板标题包含"组件"、"模块"、"部分"、"系统"等泛化词汇，且带有数字编号或字母标识时，目标标题如果是该类别的具体实现，则判断为"是"
- 示例：
  - "预使用组件版本合规性及版本漏洞情况" ↔ "第三方组件版本合规性检查" → "是"
  - "系统A架构设计" ↔ "用户管理系统架构设计" → "是"

#### 3.3 示例性章节匹配
- 模板标题明显是示例性质（包含"示例"、"样例"、"例如"等词汇，或使用占位符表达）时，目标标题如果是相应的具体实现，则判断为"是"
- 示例：
  - "XX模块设计说明" ↔ "支付模块设计说明" → "是"
  - "某某功能实现" ↔ "登录功能实现" → "是"

#### 3.4 编号序列样本匹配
- 模板标题包含连续编号（如1、2、3或A、B、C）且内容结构相似时，目标标题如果遵循相同的结构模式但使用具体名称，则判断为"是"
- 示例：
  - "接口1设计" ↔ "用户登录接口设计" → "是"
  - "流程步骤A" ↔ "数据验证流程步骤" → "是"

### 4. 结构层级匹配
如果两个标题在文档结构中处于相同层级，且核心概念相同，即使表达方式不同，也应判断为"是"。

### 5. 必做/可选标记处理
标题中的"（必做）"、"（可选）"、"（推荐）"等标记不影响核心内容的匹配判断。

## 判断流程：
1. 首先检查是否为精确匹配
2. 然后检查模板标题是否为样本性质
3. 如果是样本章节，采用灵活的匹配标准
4. 如果不是样本章节，采用严格的语义匹配
5. 最后考虑结构层级和标记处理

## 输出要求：
请只回答"是"或"否"。

## 特别提醒：
对于明显的样本章节（如包含"模块1"、"模块2"、"组件X"等泛化表达的标题），应该优先考虑其样本性质，采用更宽松的匹配标准，避免将样本章节误判为缺失章节。"""

    # 图像描述分析提示词（用于混合内容分析）
    IMAGE_DESCRIPTION_FOR_MIXED_CONTENT = """请描述图片{image_number}的内容，重点关注与文档规范相关的信息。"""

    # 关键章节检查提示词
    CRITICAL_CHAPTER_CHECK = """请判断以下一到三级章节列表中是否包含与"{required_chapter}"相关的章节：

一到三级章节列表：
{chapter_list}

判断标准：
- 章节标题中包含"{required_chapter}"关键词
- 章节标题表达的概念属于{required_chapter}范畴

请只回答"是"或"否"。"""

    # 批量语义匹配提示词
    BATCH_SEMANTIC_MATCHING = """请分析以下模板章节标题和目标章节标题之间的语义相似度。

## 模板章节标题：
{template_titles}

## 目标章节标题：
{target_titles}

{context_info}

## 匹配规则：

### 1. 精确匹配 (1.0)
- 标题完全相同或仅有微小格式差异

### 2. 高相似度匹配 (0.8-0.9)
- 表达相同概念，用词略有不同
- 样本章节匹配（如"模块1" ↔ "用户认证模块"）

### 3. 中等相似度匹配 (0.5-0.7)
- 相关概念，但有一定差异
- 同类型章节，具体内容不同

### 4. 低相似度匹配 (0.1-0.4)
- 有一定关联，但差异较大

### 5. 无关匹配 (0.0)
- 完全不相关的章节

## 输出格式：
请按以下格式输出相似度矩阵：

```
SIMILARITY_MATRIX:
T1-G1: 0.9 | 原因：标题语义相同
T1-G2: 0.2 | 原因：概念不相关
...
T2-G1: 0.1 | 原因：主题不同
T2-G2: 0.8 | 原因：表达相同功能
...
```

请开始分析："""

    # 上下文感知章节匹配提示词
    CONTEXT_AWARE_MATCHING = """请根据上下文信息分析模板章节与候选目标章节的匹配关系。

## 模板章节：
标题: {template_title}
层级: H{template_level}
位置: 第{template_position}个

## 候选目标章节：
{candidate_chapters}

## 上下文信息：
{context_info}

## 匹配要求：
1. 考虑章节的层级结构关系
2. 参考已知的重编号模式
3. 结合同级章节的映射情况
4. 优先匹配语义相同的章节

## 输出格式：
请为每个候选章节给出匹配分数和原因：

候选1: [分数] | 原因：[详细说明]
候选2: [分数] | 原因：[详细说明]
...

分数范围：0.0-1.0，1.0表示完全匹配。"""


class PromptBuilder:
    """提示词构建器，用于动态构建提示词"""
    
    @staticmethod
    def build_content_check_prompt(rules_text: str, chapter_content: str) -> str:
        """构建内容检查提示词"""
        return DocumentCheckerPrompts.CONTENT_COMPLIANCE_CHECK.format(
            rules_text=rules_text,
            chapter_content=chapter_content
        )
    
    @staticmethod
    def build_image_description_prompt(image_context: str = None, 
                                     alt_text: str = None, 
                                     title: str = None) -> str:
        """构建图像描述提示词"""
        prompt = DocumentCheckerPrompts.IMAGE_DESCRIPTION
        
        # 添加上下文信息
        if image_context:
            prompt += f"\n\n**图片上下文**: {image_context}"
        
        if alt_text:
            prompt += f"\n\n**图片Alt文本**: {alt_text}"
        
        if title:
            prompt += f"\n\n**图片标题**: {title}"
        
        return prompt
    
    @staticmethod
    def build_title_similarity_prompt(title1: str, title2: str) -> str:
        """构建标题相似度判断提示词"""
        return DocumentCheckerPrompts.CHAPTER_TITLE_SIMILARITY.format(
            title1=title1,
            title2=title2
        )
    
    @staticmethod
    def build_mixed_content_analysis_prompt(base_prompt: str, 
                                          text_content: str, 
                                          image_descriptions: list) -> str:
        """构建混合内容分析提示词"""
        combined_content = f"文本内容:\n{text_content}\n\n"
        
        if image_descriptions:
            combined_content += "图像内容:\n" + "\n\n".join(image_descriptions)
        
        return f"{base_prompt}\n\n内容:\n{combined_content}"
    
    @staticmethod
    def build_critical_chapter_check_prompt(required_chapter: str, chapter_titles: list) -> str:
        """构建关键章节检查提示词"""
        chapter_list = "\n".join([f"- {title}" for title in chapter_titles])
        
        return DocumentCheckerPrompts.CRITICAL_CHAPTER_CHECK.format(
            required_chapter=required_chapter,
            chapter_list=chapter_list
        )
    
    @staticmethod
    def build_batch_semantic_matching_prompt(template_titles: list, target_titles: list, 
                                           context_info: str = "") -> str:
        """构建批量语义匹配提示词"""
        # 格式化模板标题
        template_section = ""
        for i, title in enumerate(template_titles):
            template_section += f"T{i+1}: {title}\n"
        
        # 格式化目标标题
        target_section = ""
        for i, title in enumerate(target_titles):
            target_section += f"G{i+1}: {title}\n"
        
        # 格式化上下文信息
        context_section = ""
        if context_info:
            context_section = f"\n## 上下文信息：\n{context_info}\n"
        
        return DocumentCheckerPrompts.BATCH_SEMANTIC_MATCHING.format(
            template_titles=template_section,
            target_titles=target_section,
            context_info=context_section
        )
    
    @staticmethod
    def build_context_aware_matching_prompt(template_title: str, template_level: int, 
                                          template_position: int, candidate_chapters: list,
                                          context_info: str = "") -> str:
        """构建上下文感知匹配提示词"""
        # 格式化候选章节
        candidates_section = ""
        for i, chapter in enumerate(candidate_chapters):
            candidates_section += f"候选{i+1}: {chapter.title} (H{chapter.level}, 位置{chapter.position})\n"
        
        return DocumentCheckerPrompts.CONTEXT_AWARE_MATCHING.format(
            template_title=template_title,
            template_level=template_level,
            template_position=template_position + 1,  # 转换为1基索引
            candidate_chapters=candidates_section,
            context_info=context_info
        )
