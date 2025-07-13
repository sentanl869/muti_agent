"""
HTML 解析工具
用于解析文档 HTML，提取章节结构和图像信息
"""

import re
import os
import logging
from typing import List, Dict, Tuple, Optional
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass
from bs4 import BeautifulSoup, Tag
import requests

logger = logging.getLogger(__name__)


@dataclass
class ImageInfo:
    """图像信息"""
    url: str
    local_path: str = ""
    alt_text: str = ""
    title: str = ""
    context: str = ""
    description: str = ""
    position: str = ""


@dataclass
class ChapterInfo:
    """章节信息"""
    title: str
    level: int
    content: str
    images: List[ImageInfo]
    position: int
    html_id: str = ""
    parent_path: str = ""


class HTMLParser:
    """HTML 解析器"""
    
    def __init__(self, base_url: str = ""):
        self.base_url = base_url
        self.session = requests.Session()
        
        # 设置请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def load_cookies(self, cookies_file: str):
        """加载 Cookie 文件"""
        try:
            if os.path.exists(cookies_file):
                with open(cookies_file, 'r', encoding='utf-8') as f:
                    cookie_content = f.read().strip()
                    
                # 解析 Cookie 字符串
                if cookie_content and not cookie_content.startswith('#'):
                    # 简单的 Cookie 解析
                    cookies = {}
                    for item in cookie_content.split(';'):
                        if '=' in item:
                            key, value = item.strip().split('=', 1)
                            cookies[key] = value
                    
                    # 设置 Cookie
                    for key, value in cookies.items():
                        self.session.cookies.set(key, value)
                        
                    logger.info(f"已加载 {len(cookies)} 个 Cookie")
                    
        except Exception as e:
            logger.warning(f"加载 Cookie 失败: {e}")
    
    def parse_html(self, html_content: str) -> Tuple[List[ChapterInfo], Dict[str, any]]:
        """解析 HTML 内容，提取章节结构和元信息"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 提取文档元信息
            meta_info = self._extract_meta_info(soup)
            
            # 提取章节结构
            chapters = self._extract_chapters(soup)
            
            # 为每个章节提取图像
            for chapter in chapters:
                chapter.images = self._extract_chapter_images(soup, chapter)
            
            return chapters, meta_info
            
        except Exception as e:
            logger.error(f"HTML 解析失败: {e}")
            raise
    
    def _extract_meta_info(self, soup: BeautifulSoup) -> Dict[str, any]:
        """提取文档元信息"""
        meta_info = {
            'title': '',
            'description': '',
            'author': '',
            'keywords': [],
            'language': 'zh-CN'
        }
        
        try:
            # 提取标题
            title_tag = soup.find('title')
            if title_tag:
                meta_info['title'] = title_tag.get_text().strip()
            
            # 提取 meta 信息
            meta_tags = soup.find_all('meta')
            for meta in meta_tags:
                name = meta.get('name', '').lower()
                content = meta.get('content', '')
                
                if name == 'description':
                    meta_info['description'] = content
                elif name == 'author':
                    meta_info['author'] = content
                elif name == 'keywords':
                    meta_info['keywords'] = [k.strip() for k in content.split(',')]
                elif name == 'language' or meta.get('http-equiv', '').lower() == 'content-language':
                    meta_info['language'] = content
            
        except Exception as e:
            logger.warning(f"提取元信息失败: {e}")
        
        return meta_info
    
    def _extract_chapters(self, soup: BeautifulSoup) -> List[ChapterInfo]:
        """提取章节结构"""
        chapters = []
        
        try:
            # 查找所有标题标签
            heading_tags = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            
            for i, heading in enumerate(heading_tags):
                # 获取标题级别
                level = int(heading.name[1])
                title = self._clean_text(heading.get_text())
                
                if not title:
                    continue
                
                # 获取章节内容
                content = self._extract_chapter_content(heading)
                
                # 创建章节信息
                chapter = ChapterInfo(
                    title=title,
                    level=level,
                    content=content,
                    images=[],
                    position=i,
                    html_id=heading.get('id', ''),
                    parent_path=self._get_parent_path(chapters, level)
                )
                
                chapters.append(chapter)
            
        except Exception as e:
            logger.error(f"提取章节结构失败: {e}")
        
        return chapters
    
    def _extract_chapter_content(self, heading_tag: Tag) -> str:
        """提取章节内容"""
        content_parts = []
        
        try:
            # 获取当前标题的级别
            current_level = int(heading_tag.name[1])
            
            # 遍历后续元素直到下一个同级或更高级标题
            current = heading_tag.next_sibling
            
            while current:
                if hasattr(current, 'name'):
                    # 如果遇到同级或更高级标题，停止
                    if current.name and current.name.startswith('h'):
                        next_level = int(current.name[1])
                        if next_level <= current_level:
                            break
                    
                    # 提取文本内容
                    if current.name in ['p', 'div', 'section', 'article', 'ul', 'ol', 'table', 'pre', 'blockquote']:
                        text = self._clean_text(current.get_text())
                        if text and self._is_valid_content(current, text):
                            content_parts.append(text)
                
                current = current.next_sibling
            
        except Exception as e:
            logger.warning(f"提取章节内容失败: {e}")
        
        return '\n\n'.join(content_parts)
    
    def _extract_chapter_images(self, soup: BeautifulSoup, chapter: ChapterInfo) -> List[ImageInfo]:
        """提取章节中的图像"""
        images = []
        
        try:
            # 查找章节对应的 HTML 区域
            chapter_section = self._find_chapter_section(soup, chapter)
            
            if chapter_section:
                img_tags = chapter_section.find_all('img')
                
                for i, img_tag in enumerate(img_tags):
                    img_url = img_tag.get('src', '')
                    if not img_url:
                        continue
                    
                    # 转换为绝对 URL
                    if self.base_url:
                        img_url = urljoin(self.base_url, img_url)
                    
                    # 创建图像信息
                    image_info = ImageInfo(
                        url=img_url,
                        alt_text=img_tag.get('alt', ''),
                        title=img_tag.get('title', ''),
                        context=self._get_image_context(img_tag),
                        position=f"{chapter.title} - 图片{i+1}"
                    )
                    
                    images.append(image_info)
            
        except Exception as e:
            logger.warning(f"提取章节图像失败: {e}")
        
        return images
    
    def _find_chapter_section(self, soup: BeautifulSoup, chapter: ChapterInfo) -> Optional[Tag]:
        """查找章节对应的 HTML 区域"""
        try:
            # 首先尝试通过 ID 查找
            if chapter.html_id:
                section = soup.find(id=chapter.html_id)
                if section:
                    return section
            
            # 通过标题文本查找
            heading_tags = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            for heading in heading_tags:
                if self._clean_text(heading.get_text()) == chapter.title:
                    # 返回包含该标题的父容器
                    parent = heading.parent
                    while parent and parent.name not in ['section', 'article', 'div', 'body']:
                        parent = parent.parent
                    return parent or heading
            
        except Exception as e:
            logger.warning(f"查找章节区域失败: {e}")
        
        return None
    
    def _get_image_context(self, img_tag: Tag) -> str:
        """获取图像周围的上下文"""
        context_parts = []
        
        try:
            # 获取前后的文本内容
            prev_sibling = img_tag.previous_sibling
            next_sibling = img_tag.next_sibling
            
            # 向前查找文本
            for _ in range(3):  # 最多查找3个兄弟元素
                if prev_sibling and hasattr(prev_sibling, 'get_text'):
                    text = self._clean_text(prev_sibling.get_text())
                    if text:
                        context_parts.insert(0, text[:100])  # 限制长度
                        break
                prev_sibling = prev_sibling.previous_sibling if prev_sibling else None
            
            # 向后查找文本
            for _ in range(3):
                if next_sibling and hasattr(next_sibling, 'get_text'):
                    text = self._clean_text(next_sibling.get_text())
                    if text:
                        context_parts.append(text[:100])
                        break
                next_sibling = next_sibling.next_sibling if next_sibling else None
            
            # 检查父元素的标题或说明
            parent = img_tag.parent
            while parent and parent.name != 'body':
                if parent.name in ['figure', 'div'] and parent.get('class'):
                    caption = parent.find(['figcaption', 'caption', 'p'])
                    if caption:
                        caption_text = self._clean_text(caption.get_text())
                        if caption_text:
                            context_parts.append(caption_text)
                            break
                parent = parent.parent
            
        except Exception as e:
            logger.warning(f"获取图像上下文失败: {e}")
        
        return ' | '.join(context_parts)
    
    def _get_parent_path(self, chapters: List[ChapterInfo], current_level: int) -> str:
        """获取父章节路径"""
        path_parts = []
        
        # 从后往前查找父章节
        for chapter in reversed(chapters):
            if chapter.level < current_level:
                path_parts.insert(0, chapter.title)
                current_level = chapter.level
                if current_level == 1:  # 到达顶级章节
                    break
        
        return ' > '.join(path_parts)
    
    def _clean_text(self, text: str) -> str:
        """清理文本内容"""
        if not text:
            return ""
        
        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text.strip())
        
        # 移除特殊字符
        text = re.sub(r'[\r\n\t]', ' ', text)
        
        return text.strip()
    
    def _is_valid_content(self, element: Tag, text: str) -> bool:
        """验证内容是否有效，过滤掉导航和无意义内容"""
        try:
            # 检查内容长度，过滤过短的内容
            if len(text.strip()) < 10:
                return False
            
            # 检查是否为纯链接内容（链接密度过高）
            links = element.find_all('a') if element else []
            if links:
                link_text_length = sum(len(self._clean_text(link.get_text())) for link in links)
                total_text_length = len(text)
                if total_text_length > 0 and link_text_length / total_text_length > 0.8:
                    logger.debug(f"过滤高链接密度内容: {text[:50]}...")
                    return False
            
            # 检查是否为导航模式文本
            navigation_patterns = [
                r'首页\s*[>›]\s*',
                r'主页\s*[>›]\s*',
                r'返回\s*[>›]\s*',
                r'上一页\s*[>›]\s*',
                r'下一页\s*[>›]\s*',
                r'目录\s*[>›]\s*',
                r'导航\s*[>›]\s*'
            ]
            
            for pattern in navigation_patterns:
                if re.search(pattern, text):
                    logger.debug(f"过滤导航模式内容: {text[:50]}...")
                    return False
            
            # 检查是否为常见的无意义内容
            meaningless_patterns = [
                r'^(编辑|修改|删除|分享|收藏|打印)$',
                r'^(上传时间|修改时间|创建时间|发布时间)',
                r'^(作者|创建者|修改者)：\s*$',
                r'^(标签|分类|关键词)：\s*$',
                r'^(点击|查看|下载|更多)$'
            ]
            
            for pattern in meaningless_patterns:
                if re.search(pattern, text.strip()):
                    logger.debug(f"过滤无意义内容: {text[:50]}...")
                    return False
            
            # 检查CSS类名，过滤明显的导航元素
            if element and element.get('class'):
                class_names = ' '.join(element.get('class', []))
                filter_classes = [
                    'nav', 'navigation', 'menu', 'breadcrumb', 'sidebar',
                    'footer', 'header', 'toolbar', 'pagination', 'toc',
                    'shortcuts', 'metadata', 'actions', 'controls'
                ]
                
                for filter_class in filter_classes:
                    if filter_class in class_names.lower():
                        logger.debug(f"过滤导航类元素: {class_names}")
                        return False
            
            return True
            
        except Exception as e:
            logger.warning(f"内容验证失败: {e}")
            return True  # 出错时默认保留内容
    
    def extract_number(self, text: str) -> str:
        """从文本中提取数字编号"""
        try:
            # 匹配常见的章节编号模式
            patterns = [
                r'^(\d+(?:\.\d+)*)',  # 1.1, 1.2.3 等
                r'^第(\d+)章',        # 第1章
                r'^第(\d+)节',        # 第1节
                r'^(\d+)',            # 纯数字
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text.strip())
                if match:
                    return match.group(1)
            
            # 如果没有找到数字，返回原文本的前10个字符作为标识
            return text.strip()[:10]
            
        except Exception as e:
            logger.warning(f"提取编号失败: {e}")
            return text.strip()[:10]
    
    def download_image(self, image_info: ImageInfo, save_dir: str = "temp") -> str:
        """下载图像到本地"""
        try:
            os.makedirs(save_dir, exist_ok=True)
            
            # 生成本地文件名
            parsed_url = urlparse(image_info.url)
            filename = os.path.basename(parsed_url.path)
            if not filename or '.' not in filename:
                filename = f"image_{hash(image_info.url) % 10000}.jpg"
            
            local_path = os.path.join(save_dir, filename)
            
            # 如果文件已存在，直接返回
            if os.path.exists(local_path):
                image_info.local_path = local_path
                return local_path
            
            # 下载图像
            response = self.session.get(image_info.url, timeout=30)
            response.raise_for_status()
            
            # 保存图像
            with open(local_path, 'wb') as f:
                f.write(response.content)
            
            image_info.local_path = local_path
            logger.info(f"图像下载成功: {local_path}")
            
            return local_path
            
        except Exception as e:
            logger.error(f"图像下载失败 {image_info.url}: {e}")
            return ""
