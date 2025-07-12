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

标题1: {title1}
标题2: {title2}

请只回答"是"或"否"。如果两个标题表达的是同一个主题或概念，即使用词不完全相同，也应该回答"是"。"""

    # 图像描述分析提示词（用于混合内容分析）
    IMAGE_DESCRIPTION_FOR_MIXED_CONTENT = """请描述图片{image_number}的内容，重点关注与文档规范相关的信息。"""


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
