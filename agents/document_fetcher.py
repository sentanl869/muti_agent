"""
文档获取 Agent
负责通过 HTTP 请求获取文档模板和目标文档
"""

import logging
import requests
from typing import Dict, Any, Optional
from urllib.parse import urljoin

from utils.html_parser import HTMLParser
from config.config import config
from utils.retry_handler import BackoffRetry, HTTP_RETRY_CONFIG, RetryConfig

logger = logging.getLogger(__name__)


class DocumentFetcher:
    """文档获取 Agent"""
    
    def __init__(self, retry_config=None):
        self.session = requests.Session()
        self.parser = HTMLParser()
        
        # 设置请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        # 初始化重试处理器
        if retry_config is None:
            retry_config = RetryConfig(
                max_retries=config.retry.max_retries,
                initial_delay=config.retry.initial_delay,
                max_delay=config.retry.max_delay,
                backoff_factor=config.retry.backoff_factor,
                enable_jitter=config.retry.enable_jitter,
                retryable_exceptions=HTTP_RETRY_CONFIG.retryable_exceptions
            )
        self.retry_handler = BackoffRetry(retry_config)
        
        # 加载 Cookie
        self._load_cookies()
    
    def _load_cookies(self):
        """加载 Cookie 配置"""
        try:
            cookies_file = config.document.cookies_file
            self.parser.load_cookies(cookies_file)
            
            # 将 Cookie 设置到 session
            for cookie in self.parser.session.cookies:
                self.session.cookies.set(cookie.name, cookie.value)
                
            logger.info("Cookie 加载完成")
            
        except Exception as e:
            logger.warning(f"Cookie 加载失败: {e}")
    
    def fetch_document(self, url: str, page_id: str = None) -> Dict[str, Any]:
        """
        获取文档内容
        
        Args:
            url: 基础 URL
            page_id: 页面 ID（可选，会拼接到 URL 中）
            
        Returns:
            包含文档内容和元信息的字典
        """
        try:
            # 构建完整 URL
            full_url = self._build_url(url, page_id)
            
            logger.info(f"开始获取文档: {full_url}")
            
            # 发送请求
            response = self._make_request(full_url)
            
            # 解析 HTML 内容
            chapters, meta_info = self.parser.parse_html(response.text)
            
            # 设置解析器的基础 URL
            self.parser.base_url = self._get_base_url(full_url)
            
            result = {
                'url': full_url,
                'status_code': response.status_code,
                'content_length': len(response.text),
                'chapters': chapters,
                'meta_info': meta_info,
                'raw_html': response.text
            }
            
            logger.info(f"文档获取成功: {len(chapters)} 个章节, {len(response.text)} 字符")
            
            return result
            
        except Exception as e:
            logger.error(f"文档获取失败 {url}: {e}")
            raise
    
    def fetch_template_document(self, template_url: str, template_page_id: str = None) -> Dict[str, Any]:
        """
        获取模板文档
        
        Args:
            template_url: 模板文档 URL
            template_page_id: 模板页面 ID
            
        Returns:
            模板文档内容
        """
        logger.info("开始获取模板文档")
        
        template_doc = self.fetch_document(template_url, template_page_id)
        template_doc['document_type'] = 'template'
        
        logger.info(f"模板文档获取完成: {len(template_doc['chapters'])} 个章节")
        
        return template_doc
    
    def fetch_target_document(self, target_url: str, target_page_id: str = None) -> Dict[str, Any]:
        """
        获取目标文档
        
        Args:
            target_url: 目标文档 URL
            target_page_id: 目标页面 ID
            
        Returns:
            目标文档内容
        """
        logger.info("开始获取目标文档")
        
        target_doc = self.fetch_document(target_url, target_page_id)
        target_doc['document_type'] = 'target'
        
        logger.info(f"目标文档获取完成: {len(target_doc['chapters'])} 个章节")
        
        return target_doc
    
    def _build_url(self, base_url: str, page_id: str = None) -> str:
        """构建完整 URL"""
        if not page_id:
            return base_url
        
        # 如果 URL 已经包含查询参数，使用 & 连接
        if '?' in base_url:
            separator = '&'
        else:
            separator = '?'
        
        # 根据不同的 URL 模式拼接 page_id
        if 'page_id=' in base_url:
            # 替换现有的 page_id
            import re
            return re.sub(r'page_id=[^&]*', f'pageId={page_id}', base_url)
        else:
            # 添加新的 page_id 参数
            return f"{base_url}{separator}pageId={page_id}"
    
    def _get_base_url(self, full_url: str) -> str:
        """获取基础 URL（用于解析相对路径）"""
        from urllib.parse import urlparse
        parsed = urlparse(full_url)
        return f"{parsed.scheme}://{parsed.netloc}"
    
    def _make_request(self, url: str) -> requests.Response:
        """发送 HTTP 请求"""
        def _do_request():
            timeout = config.document.timeout
            
            response = self.session.get(
                url,
                timeout=timeout,
                allow_redirects=True
            )
            
            # 检查响应状态
            response.raise_for_status()
            
            # 检查内容类型
            content_type = response.headers.get('content-type', '').lower()
            if 'text/html' not in content_type:
                logger.warning(f"响应内容类型不是 HTML: {content_type}")
            
            # 检查内容长度
            if len(response.text) < 100:
                raise ValueError("响应内容过短，可能不是有效的文档")
            
            logger.debug(f"请求成功: {response.status_code}, {len(response.text)} 字符")
            
            return response
        
        # 使用重试机制执行请求
        return self.retry_handler.execute_with_retry(_do_request)
    
    def validate_document(self, document: Dict[str, Any]) -> bool:
        """验证文档内容是否有效"""
        try:
            # 检查基本字段
            required_fields = ['chapters', 'meta_info', 'url']
            for field in required_fields:
                if field not in document:
                    logger.error(f"文档缺少必需字段: {field}")
                    return False
            
            # 检查章节数量
            if not document['chapters']:
                logger.error("文档没有章节内容")
                return False
            
            # 检查章节结构
            for i, chapter in enumerate(document['chapters']):
                if not chapter.title:
                    logger.warning(f"章节 {i} 没有标题")
                
                if chapter.level < 1 or chapter.level > 6:
                    logger.warning(f"章节 {i} 层级异常: {chapter.level}")
            
            logger.info(f"文档验证通过: {len(document['chapters'])} 个章节")
            return True
            
        except Exception as e:
            logger.error(f"文档验证失败: {e}")
            return False
    
    def get_document_summary(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """获取文档摘要信息"""
        try:
            chapters = document['chapters']
            meta_info = document['meta_info']
            
            # 统计章节信息
            level_counts = {}
            total_content_length = 0
            total_images = 0
            
            for chapter in chapters:
                level = chapter.level
                level_counts[level] = level_counts.get(level, 0) + 1
                total_content_length += len(chapter.content)
                total_images += len(chapter.images)
            
            summary = {
                'title': meta_info.get('title', '未知文档'),
                'total_chapters': len(chapters),
                'level_distribution': level_counts,
                'total_content_length': total_content_length,
                'total_images': total_images,
                'url': document['url'],
                'document_type': document.get('document_type', 'unknown')
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"生成文档摘要失败: {e}")
            return {}
    
    def close(self):
        """关闭会话"""
        if self.session:
            self.session.close()
