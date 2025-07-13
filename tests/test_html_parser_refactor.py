#!/usr/bin/env python3
"""
测试修改后的 HTML 解析器
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.html_parser import HTMLParser

# 测试 HTML 内容
test_html = """
<!DOCTYPE html>
<html>
<head>
    <title>测试文档</title>
</head>
<body>
    <h1>文档标题</h1>
    <p>这是文档的主标题，应该被跳过</p>
    
    <h1>第一章 概述</h1>
    <p>这是第一章的内容。介绍了项目的基本概念和目标。</p>
    <p>第一章包含了重要的背景信息。</p>
    
    <h2>1.1 项目背景</h2>
    <p>项目背景的详细描述。</p>
    <p>更多背景信息。</p>
    
    <h2>1.2 项目目标</h2>
    <p>项目目标的详细说明。</p>
    
    <h3>1.2.1 短期目标</h3>
    <p>短期目标的具体内容。</p>
    
    <h3>1.2.2 长期目标</h3>
    <p>长期目标的具体内容。</p>
    
    <h1>第二章 技术架构</h1>
    <p>这是第二章的内容。描述了系统的技术架构。</p>
    
    <h2>2.1 系统架构</h2>
    <p>系统架构的详细描述。</p>
    
    <h2>2.2 技术选型</h2>
    <p>技术选型的说明。</p>
    
    <h1>第三章 实施计划</h1>
    <p>这是第三章的内容。</p>
</body>
</html>
"""

def test_html_parser():
    """测试 HTML 解析器"""
    print("开始测试 HTML 解析器...")
    
    # 创建解析器实例
    parser = HTMLParser()
    
    try:
        # 解析 HTML
        chapters, meta_info = parser.parse_html(test_html)
        
        print(f"\n=== 文档元信息 ===")
        print(f"标题: {meta_info['title']}")
        print(f"语言: {meta_info['language']}")
        
        print(f"\n=== 章节结构 ===")
        print(f"共提取到 {len(chapters)} 个章节")
        
        for i, chapter in enumerate(chapters):
            indent = "  " * (chapter.level - 1)
            print(f"{i+1}. {indent}[H{chapter.level}] {chapter.title}")
            if chapter.parent_path:
                print(f"    {indent}父路径: {chapter.parent_path}")
            print(f"    {indent}内容长度: {len(chapter.content)} 字符")
            if chapter.content:
                preview = chapter.content[:100].replace('\n', ' ')
                print(f"    {indent}内容预览: {preview}...")
            print()
        
        # 验证层次结构
        print("=== 验证层次结构 ===")
        h1_count = sum(1 for c in chapters if c.level == 1)
        h2_count = sum(1 for c in chapters if c.level == 2)
        h3_count = sum(1 for c in chapters if c.level == 3)
        
        print(f"H1 章节数量: {h1_count}")
        print(f"H2 章节数量: {h2_count}")
        print(f"H3 章节数量: {h3_count}")
        
        # 验证父路径
        print("\n=== 验证父路径 ===")
        for chapter in chapters:
            if chapter.level > 1:
                print(f"{chapter.title} -> 父路径: {chapter.parent_path}")
        
        print("\n测试完成！")
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_html_parser()
