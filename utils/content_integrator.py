"""
内容整合器
将文本和图像内容整合成完整的章节内容
"""

import logging
from typing import List, Dict, Any
from dataclasses import dataclass

from utils.html_parser import ChapterInfo, ImageInfo
from utils.llm_client import MultiModalClient
from config.config import config
from prompts import PromptBuilder

logger = logging.getLogger(__name__)


@dataclass
class IntegratedChapter:
    """整合后的章节内容"""
    title: str
    level: int
    text_content: str
    images: List[ImageInfo]
    combined_content: str
    position: int
    parent_path: str
    word_count: int = 0


class ContentIntegrator:
    """内容整合器"""
    
    def __init__(self):
        self.multimodal_client = MultiModalClient()
        self.max_chunk_size = config.document.chunk_size
    
    def integrate_chapters(self, chapters: List[ChapterInfo]) -> List[IntegratedChapter]:
        """整合所有章节的内容"""
        integrated_chapters = []
        
        for chapter in chapters:
            try:
                integrated_chapter = self._integrate_single_chapter(chapter)
                integrated_chapters.append(integrated_chapter)
                
                logger.info(f"章节整合完成: {chapter.title} ({integrated_chapter.word_count} 字)")
                
            except Exception as e:
                logger.error(f"章节整合失败 {chapter.title}: {e}")
                # 创建一个基础的整合章节
                integrated_chapter = IntegratedChapter(
                    title=chapter.title,
                    level=chapter.level,
                    text_content=chapter.content,
                    images=chapter.images,
                    combined_content=chapter.content,
                    position=chapter.position,
                    parent_path=chapter.parent_path,
                    word_count=len(chapter.content)
                )
                integrated_chapters.append(integrated_chapter)
        
        return integrated_chapters
    
    def _integrate_single_chapter(self, chapter: ChapterInfo) -> IntegratedChapter:
        """整合单个章节的内容"""
        # 处理章节中的图像
        processed_images = self._process_chapter_images(chapter.images)
        
        # 组合文本和图像描述
        combined_content = self._combine_content(chapter, processed_images)
        
        # 创建整合后的章节
        integrated_chapter = IntegratedChapter(
            title=chapter.title,
            level=chapter.level,
            text_content=chapter.content,
            images=processed_images,
            combined_content=combined_content,
            position=chapter.position,
            parent_path=chapter.parent_path,
            word_count=len(combined_content)
        )
        
        return integrated_chapter
    
    def _process_chapter_images(self, images: List[ImageInfo]) -> List[ImageInfo]:
        """处理章节中的图像，生成描述"""
        processed_images = []
        
        for image in images:
            try:
                # 下载图像（如果还没有下载）
                if not image.local_path:
                    from utils.html_parser import HTMLParser
                    parser = HTMLParser()
                    local_path = parser.download_image(image)
                    if not local_path:
                        logger.warning(f"图像下载失败，跳过: {image.url}")
                        continue
                
                # 生成图像描述
                if not image.description:
                    description_prompt = self._create_image_description_prompt(image)
                    image.description = self.multimodal_client.analyze_image(
                        image.local_path, 
                        description_prompt
                    )
                
                processed_images.append(image)
                
            except Exception as e:
                logger.error(f"图像处理失败 {image.url}: {e}")
                # 即使处理失败，也保留图像信息
                if not image.description:
                    image.description = f"图像处理失败: {str(e)}"
                processed_images.append(image)
        
        return processed_images
    
    def _create_image_description_prompt(self, image: ImageInfo) -> str:
        """创建图像描述提示词"""
        return PromptBuilder.build_image_description_prompt(
            image_context=image.context,
            alt_text=image.alt_text,
            title=image.title
        )
    
    def _combine_content(self, chapter: ChapterInfo, images: List[ImageInfo]) -> str:
        """组合文本和图像内容"""
        content_parts = []
        
        # 添加章节标题和层级信息
        content_parts.append(f"# 章节: {chapter.title}")
        content_parts.append(f"层级: H{chapter.level}")
        if chapter.parent_path:
            content_parts.append(f"路径: {chapter.parent_path} > {chapter.title}")
        content_parts.append("")
        
        # 添加文本内容
        if chapter.content:
            content_parts.append("## 文本内容")
            content_parts.append(chapter.content)
            content_parts.append("")
        
        # 添加图像内容
        if images:
            content_parts.append("## 图像内容")
            for i, image in enumerate(images, 1):
                content_parts.append(f"### 图片 {i}")
                content_parts.append(f"**位置**: {image.position}")
                
                if image.alt_text:
                    content_parts.append(f"**Alt文本**: {image.alt_text}")
                
                if image.title:
                    content_parts.append(f"**标题**: {image.title}")
                
                if image.context:
                    content_parts.append(f"**上下文**: {image.context}")
                
                if image.description:
                    content_parts.append(f"**图像描述**: {image.description}")
                
                content_parts.append("")
        
        combined_content = "\n".join(content_parts)
        
        # 检查内容长度，如果超过限制则进行分块
        if len(combined_content) > self.max_chunk_size:
            combined_content = self._truncate_content(combined_content)
        
        return combined_content
    
    def _truncate_content(self, content: str) -> str:
        """截断过长的内容"""
        if len(content) <= self.max_chunk_size:
            return content
        
        # 尝试在段落边界截断
        lines = content.split('\n')
        truncated_lines = []
        current_length = 0
        
        for line in lines:
            if current_length + len(line) + 1 > self.max_chunk_size:
                break
            truncated_lines.append(line)
            current_length += len(line) + 1
        
        truncated_content = '\n'.join(truncated_lines)
        
        # 添加截断提示
        truncated_content += f"\n\n[注意: 内容因长度限制被截断，原长度: {len(content)} 字符，截断后: {len(truncated_content)} 字符]"
        
        logger.warning(f"内容被截断: {len(content)} -> {len(truncated_content)} 字符")
        
        return truncated_content
    
    def split_large_chapters(self, chapters: List[IntegratedChapter]) -> List[IntegratedChapter]:
        """分割过大的章节"""
        split_chapters = []
        
        for chapter in chapters:
            if chapter.word_count <= self.max_chunk_size:
                split_chapters.append(chapter)
            else:
                # 分割大章节
                sub_chapters = self._split_chapter(chapter)
                split_chapters.extend(sub_chapters)
        
        return split_chapters
    
    def _split_chapter(self, chapter: IntegratedChapter) -> List[IntegratedChapter]:
        """分割单个大章节"""
        sub_chapters = []
        
        try:
            # 按段落分割内容
            paragraphs = chapter.combined_content.split('\n\n')
            
            current_content = []
            current_length = 0
            part_number = 1
            
            for paragraph in paragraphs:
                paragraph_length = len(paragraph)
                
                # 如果添加这个段落会超过限制，则创建一个子章节
                if current_length + paragraph_length > self.max_chunk_size and current_content:
                    sub_chapter = self._create_sub_chapter(
                        chapter, current_content, part_number
                    )
                    sub_chapters.append(sub_chapter)
                    
                    current_content = [paragraph]
                    current_length = paragraph_length
                    part_number += 1
                else:
                    current_content.append(paragraph)
                    current_length += paragraph_length
            
            # 处理最后一部分
            if current_content:
                sub_chapter = self._create_sub_chapter(
                    chapter, current_content, part_number
                )
                sub_chapters.append(sub_chapter)
            
        except Exception as e:
            logger.error(f"章节分割失败: {e}")
            # 如果分割失败，返回原章节（截断）
            chapter.combined_content = self._truncate_content(chapter.combined_content)
            chapter.word_count = len(chapter.combined_content)
            sub_chapters.append(chapter)
        
        return sub_chapters
    
    def _create_sub_chapter(self, original_chapter: IntegratedChapter, 
                           content_parts: List[str], part_number: int) -> IntegratedChapter:
        """创建子章节"""
        combined_content = '\n\n'.join(content_parts)
        
        sub_chapter = IntegratedChapter(
            title=f"{original_chapter.title} (第{part_number}部分)",
            level=original_chapter.level,
            text_content=original_chapter.text_content,
            images=original_chapter.images if part_number == 1 else [],  # 只在第一部分包含图像
            combined_content=combined_content,
            position=original_chapter.position,
            parent_path=original_chapter.parent_path,
            word_count=len(combined_content)
        )
        
        return sub_chapter
