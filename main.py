"""
文档检查系统主程序
"""

import argparse
import logging
import sys
import os
from pathlib import Path

from workflow import DocumentCheckWorkflow
from config.config import config


def setup_logging():
    """设置日志配置"""
    log_level = getattr(logging, config.logging.level.upper())
    
    # 创建日志目录
    log_dir = Path(config.logging.log_dir)
    log_dir.mkdir(exist_ok=True)
    
    # 配置日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    
    # 文件处理器
    file_handler = logging.FileHandler(
        log_dir / 'document_checker.log',
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    
    # 配置根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # 设置第三方库日志级别
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='文档检查系统 - 基于 LangGraph 的多 Agent 文档检查工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python main.py --template-url "https://example.com/template" --target-url "https://example.com/target"
  python main.py --template-url "https://example.com/template" --template-page-id "123" --target-url "https://example.com/target" --target-page-id "456"
        """
    )
    
    # 必需参数
    parser.add_argument(
        '--template-url',
        required=True,
        help='模板文档的 URL'
    )
    
    parser.add_argument(
        '--target-url',
        required=True,
        help='目标文档的 URL'
    )
    
    # 可选参数
    parser.add_argument(
        '--template-page-id',
        help='模板文档的页面 ID（可选）'
    )
    
    parser.add_argument(
        '--target-page-id',
        help='目标文档的页面 ID（可选）'
    )
    
    parser.add_argument(
        '--output-dir',
        help='报告输出目录（默认使用配置文件中的设置）'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='日志级别（默认使用配置文件中的设置）'
    )
    
    parser.add_argument(
        '--config-file',
        help='配置文件路径（默认使用 config/config.py）'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='试运行模式，只验证参数不执行检查'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='详细输出模式'
    )
    
    return parser.parse_args()


def validate_arguments(args):
    """验证命令行参数"""
    errors = []
    
    # 验证 URL 格式
    if not args.template_url.startswith(('http://', 'https://')):
        errors.append("模板文档 URL 必须以 http:// 或 https:// 开头")
    
    if not args.target_url.startswith(('http://', 'https://')):
        errors.append("目标文档 URL 必须以 http:// 或 https:// 开头")
    
    # 验证输出目录
    if args.output_dir:
        output_path = Path(args.output_dir)
        if output_path.exists() and not output_path.is_dir():
            errors.append(f"输出路径不是目录: {args.output_dir}")
    
    # 验证配置文件
    if args.config_file:
        config_path = Path(args.config_file)
        if not config_path.exists():
            errors.append(f"配置文件不存在: {args.config_file}")
    
    if errors:
        print("参数验证失败:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    return True


def print_banner():
    """打印程序横幅"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                    文档检查系统 v1.0                          ║
║              基于 LangGraph 的多 Agent 文档检查工具            ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_summary(result):
    """打印检查结果摘要"""
    print("\n" + "="*60)
    print("检查结果摘要")
    print("="*60)
    
    if result["success"]:
        print("✅ 检查完成")
        print(f"📄 报告文件: {result['report_path']}")
        
        # 结构检查结果
        structure_result = result.get("structure_result")
        if structure_result:
            print(f"📋 结构检查: {'✅ 通过' if structure_result.passed else '❌ 失败'}")
            if not structure_result.passed:
                print(f"   - 缺失章节: {len(structure_result.missing_chapters)} 个")
                print(f"   - 结构相似度: {structure_result.similarity_score:.1%}")
        
        # 内容检查结果
        content_result = result.get("content_result")
        if content_result:
            print(f"📝 内容检查: {'✅ 通过' if content_result.passed else '❌ 失败'}")
            if not content_result.passed:
                print(f"   - 违规项目: {content_result.total_violations} 个")
                severity_summary = content_result.severity_summary
                if severity_summary.get('critical', 0) > 0:
                    print(f"   - 严重问题: {severity_summary['critical']} 个")
                if severity_summary.get('warning', 0) > 0:
                    print(f"   - 警告问题: {severity_summary['warning']} 个")
        
    else:
        print("❌ 检查失败")
        print(f"错误信息: {result['error_message']}")
        print(f"当前步骤: {result['current_step']}")
    
    print("="*60)


def main():
    """主函数"""
    try:
        # 打印横幅
        print_banner()
        
        # 解析命令行参数
        args = parse_arguments()
        
        # 验证参数
        if not validate_arguments(args):
            sys.exit(1)
        
        # 应用命令行参数覆盖配置
        if args.output_dir:
            config.report.output_dir = args.output_dir
        
        if args.log_level:
            config.logging.level = args.log_level.lower()
        
        # 设置日志
        setup_logging()
        logger = logging.getLogger(__name__)
        
        logger.info("文档检查系统启动")
        logger.info(f"模板文档 URL: {args.template_url}")
        logger.info(f"目标文档 URL: {args.target_url}")
        
        if args.verbose:
            print(f"模板文档 URL: {args.template_url}")
            if args.template_page_id:
                print(f"模板页面 ID: {args.template_page_id}")
            print(f"目标文档 URL: {args.target_url}")
            if args.target_page_id:
                print(f"目标页面 ID: {args.target_page_id}")
            print(f"输出目录: {config.report.output_dir}")
            print(f"日志级别: {config.logging.level}")
        
        # 试运行模式
        if args.dry_run:
            print("✅ 试运行模式 - 参数验证通过")
            logger.info("试运行模式完成")
            return
        
        # 创建并运行工作流
        print("🚀 开始执行文档检查...")
        workflow = DocumentCheckWorkflow()
        
        try:
            result = workflow.run(
                template_url=args.template_url,
                target_url=args.target_url,
                template_page_id=args.template_page_id,
                target_page_id=args.target_page_id
            )
            
            # 打印结果摘要
            print_summary(result)
            
            # 根据结果设置退出码
            if result["success"]:
                logger.info("文档检查系统执行成功")
                sys.exit(0)
            else:
                logger.error("文档检查系统执行失败")
                sys.exit(1)
                
        finally:
            # 清理资源
            workflow.cleanup()
    
    except KeyboardInterrupt:
        print("\n⚠️  用户中断执行")
        logging.getLogger(__name__).info("用户中断执行")
        sys.exit(130)
    
    except Exception as e:
        print(f"\n❌ 系统异常: {e}")
        logging.getLogger(__name__).error(f"系统异常: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
