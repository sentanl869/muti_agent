"""
测试内容过滤功能
验证 HTMLParser 是否能正确过滤掉导航和无意义内容
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.html_parser import HTMLParser

# 测试 HTML 内容，包含一些应该被过滤的内容
test_html = """
<!DOCTYPE html>
<html>
<head>
    <title>测试文档</title>
</head>
<body>
    <div class="breadcrumb">首页 > 文档 > 测试页面</div>
    
    <h1>文档标题</h1>
    
    <h2>第1章 介绍</h2>
    <p>这是一个有意义的段落，包含了实际的文档内容。这个段落应该被保留，因为它包含了有价值的信息。</p>
    
    <div class="navigation">
        <a href="/home">首页</a>
        <a href="/docs">文档</a>
        <a href="/help">帮助</a>
    </div>
    
    <p>这是另一个有意义的段落。</p>
    
    <div class="sidebar">
        <ul>
            <li><a href="/link1">链接1</a></li>
            <li><a href="/link2">链接2</a></li>
            <li><a href="/link3">链接3</a></li>
        </ul>
    </div>
    
    <h2>第2章 详细说明</h2>
    <p>这里是详细的说明内容，应该被保留。包含了技术细节和重要信息。</p>
    
    <div>编辑</div>
    <div>修改时间：2024-01-01</div>
    
    <p>最后一个有意义的段落。</p>
    
    <div class="page-actions">
        <button>编辑</button>
        <button>删除</button>
        <button>分享</button>
    </div>
</body>
</html>
"""

def test_content_filter():
    """测试内容过滤功能"""
    print("开始测试内容过滤功能...")
    
    parser = HTMLParser()
    
    try:
        # 解析 HTML
        chapters, meta_info = parser.parse_html(test_html)
        
        print(f"\n解析结果:")
        print(f"文档标题: {meta_info.get('title', '未知')}")
        print(f"章节数量: {len(chapters)}")
        
        # 显示每个章节的内容
        for i, chapter in enumerate(chapters):
            print(f"\n章节 {i+1}:")
            print(f"  标题: {chapter.title}")
            print(f"  级别: H{chapter.level}")
            print(f"  内容长度: {len(chapter.content)} 字符")
            print(f"  内容预览: {chapter.content[:100]}...")
            
            # 检查是否包含应该被过滤的内容
            filtered_keywords = ['首页', '编辑', '删除', '分享', '链接1', '链接2', '链接3']
            found_filtered = [kw for kw in filtered_keywords if kw in chapter.content]
            
            if found_filtered:
                print(f"  ⚠️  发现可能未被过滤的内容: {found_filtered}")
            else:
                print(f"  ✅ 内容过滤正常")
        
        # 测试 extract_number 方法
        print(f"\n测试编号提取:")
        test_titles = [
            "第1章 介绍",
            "1.1 概述", 
            "2.3.1 详细说明",
            "第5节 总结",
            "无编号标题"
        ]
        
        for title in test_titles:
            number = parser.extract_number(title)
            print(f"  '{title}' -> '{number}'")
            
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_content_filter()
