#!/usr/bin/env python3
"""
文档检查系统使用示例
演示如何使用 DocumentCheckWorkflow 进行文档检查
"""

import os
import sys
import logging
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from workflow import DocumentCheckWorkflow
from config.config import config


def setup_example_logging():
    """设置示例日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def example_basic_usage():
    """基本使用示例"""
    print("=" * 60)
    print("基本使用示例")
    print("=" * 60)
    
    # 示例 URL（请替换为实际的文档 URL）
    template_url = "https://example.com/template-document"
    target_url = "https://example.com/target-document"
    
    print(f"模板文档 URL: {template_url}")
    print(f"目标文档 URL: {target_url}")
    print()
    
    # 创建工作流实例
    workflow = DocumentCheckWorkflow()
    
    try:
        print("🚀 开始执行文档检查...")
        
        # 运行检查
        result = workflow.run(
            template_url=template_url,
            target_url=target_url
        )
        
        # 输出结果
        print("\n📊 检查结果:")
        print(f"成功: {result['success']}")
        
        if result['success']:
            print(f"报告文件: {result['report_path']}")
            
            # 结构检查结果
            structure_result = result.get('structure_result')
            if structure_result:
                print(f"结构检查: {'✅ 通过' if structure_result.passed else '❌ 失败'}")
                if not structure_result.passed:
                    print(f"  缺失章节: {len(structure_result.missing_chapters)} 个")
            
            # 内容检查结果
            content_result = result.get('content_result')
            if content_result:
                print(f"内容检查: {'✅ 通过' if content_result.passed else '❌ 失败'}")
                if not content_result.passed:
                    print(f"  违规项目: {content_result.total_violations} 个")
        else:
            print(f"错误信息: {result['error_message']}")
            
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        
    finally:
        # 清理资源
        workflow.cleanup()


def example_with_page_ids():
    """带页面 ID 的使用示例"""
    print("\n" + "=" * 60)
    print("带页面 ID 的使用示例")
    print("=" * 60)
    
    # 示例参数
    template_url = "https://example.com/wiki"
    template_page_id = "template-123"
    target_url = "https://example.com/wiki"
    target_page_id = "target-456"
    
    print(f"模板文档: {template_url} (页面 ID: {template_page_id})")
    print(f"目标文档: {target_url} (页面 ID: {target_page_id})")
    print()
    
    workflow = DocumentCheckWorkflow()
    
    try:
        print("🚀 开始执行文档检查...")
        
        result = workflow.run(
            template_url=template_url,
            target_url=target_url,
            template_page_id=template_page_id,
            target_page_id=target_page_id
        )
        
        print(f"\n📊 检查完成: {result['success']}")
        if result['success']:
            print(f"报告文件: {result['report_path']}")
        else:
            print(f"错误: {result['error_message']}")
            
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        
    finally:
        workflow.cleanup()


def example_status_monitoring():
    """状态监控示例"""
    print("\n" + "=" * 60)
    print("状态监控示例")
    print("=" * 60)
    
    workflow = DocumentCheckWorkflow()
    
    try:
        # 获取初始状态
        status = workflow.get_workflow_status()
        print(f"初始状态: {status}")
        
        # 这里可以启动异步检查，然后监控状态
        # 由于这是示例，我们只演示状态获取
        print("状态监控功能已就绪")
        
    except Exception as e:
        print(f"❌ 状态监控失败: {e}")
        
    finally:
        workflow.cleanup()


def example_configuration():
    """配置示例"""
    print("\n" + "=" * 60)
    print("配置示例")
    print("=" * 60)
    
    print("当前配置:")
    print(f"LLM 模型: {config.llm.model}")
    print(f"最大上下文长度: {config.llm.max_context_length}")
    print(f"输出目录: {config.report.output_dir}")
    print(f"日志级别: {config.logging.level}")
    
    print("\n配置文件位置:")
    print("- 主配置: config/config.py")
    print("- 规则配置: config/rules.yaml")
    print("- Cookies: config/cookies.txt")
    
    print("\n环境变量支持:")
    print("- LLM_API_KEY: LLM API 密钥")
    print("- LLM_BASE_URL: LLM API 端点")
    print("- LLM_MODEL: LLM 模型名称")


def example_error_handling():
    """错误处理示例"""
    print("\n" + "=" * 60)
    print("错误处理示例")
    print("=" * 60)
    
    # 使用无效的 URL 来演示错误处理
    invalid_url = "invalid-url"
    
    workflow = DocumentCheckWorkflow()
    
    try:
        print(f"尝试使用无效 URL: {invalid_url}")
        
        result = workflow.run(
            template_url=invalid_url,
            target_url=invalid_url
        )
        
        print(f"结果: {result}")
        print("错误处理机制正常工作")
        
    except Exception as e:
        print(f"捕获异常: {e}")
        print("异常处理机制正常工作")
        
    finally:
        workflow.cleanup()


def main():
    """主函数"""
    print("文档检查系统使用示例")
    print("=" * 60)
    
    # 设置日志
    setup_example_logging()
    
    # 检查配置
    print("📋 检查系统配置...")
    
    # 检查必要目录
    reports_dir = Path(config.report.output_dir)
    logs_dir = Path(config.logging.log_dir)
    
    reports_dir.mkdir(exist_ok=True)
    logs_dir.mkdir(exist_ok=True)
    
    print(f"✅ 报告目录: {reports_dir}")
    print(f"✅ 日志目录: {logs_dir}")
    
    # 运行示例
    try:
        # 配置示例
        example_configuration()
        
        # 状态监控示例
        example_status_monitoring()
        
        # 错误处理示例
        example_error_handling()
        
        # 注意：以下示例需要真实的 URL，请根据实际情况修改
        print("\n" + "=" * 60)
        print("注意事项")
        print("=" * 60)
        print("以下示例需要真实的文档 URL 才能正常运行:")
        print("- example_basic_usage()")
        print("- example_with_page_ids()")
        print()
        print("请在 example.py 中修改 URL 后再运行这些示例")
        
        # 如果您有真实的 URL，可以取消注释以下行
        # example_basic_usage()
        # example_with_page_ids()
        
    except KeyboardInterrupt:
        print("\n⚠️  用户中断执行")
    except Exception as e:
        print(f"\n❌ 示例执行失败: {e}")
        logging.exception("示例执行异常")
    
    print("\n✅ 示例演示完成")


if __name__ == "__main__":
    main()
