"""命令行接口

提供交互式代码生成功能。

支持需求15.1：提供命令行接口用于代码生成
"""

import sys
import argparse
from pathlib import Path
from loguru import logger

from .rag_generator import RAGCodeGenerator
from .config import Config, ConfigError


def setup_logger(verbose: bool = False):
    """配置日志"""
    logger.remove()
    
    if verbose:
        logger.add(
            sys.stderr,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
            level="DEBUG"
        )
    else:
        logger.add(
            sys.stderr,
            format="<level>{level: <8}</level> | <level>{message}</level>",
            level="INFO"
        )


def interactive_mode(generator: RAGCodeGenerator):
    """交互式模式"""
    print("\n" + "=" * 60)
    print("RAG代码生成系统 - 交互模式")
    print("=" * 60)
    print("输入代码需求描述，系统将生成相应代码")
    print("输入 'quit' 或 'exit' 退出")
    print("输入 'help' 查看帮助")
    print("=" * 60 + "\n")
    
    while True:
        try:
            # 读取用户输入
            query = input("\n请输入代码需求: ").strip()
            
            if not query:
                continue
            
            # 处理命令
            if query.lower() in ['quit', 'exit', 'q']:
                print("\n再见！")
                break
            
            if query.lower() == 'help':
                print_help()
                continue
            
            if query.lower() == 'info':
                print_system_info(generator)
                continue
            
            # 生成代码
            print("\n生成中...")
            code = generator.generate(query)
            
            # 显示结果
            print("\n" + "=" * 60)
            print("生成的代码:")
            print("=" * 60)
            print(code)
            print("=" * 60)
            
            # 询问是否保存
            save = input("\n是否保存到文件? (y/n): ").strip().lower()
            if save == 'y':
                filename = input("文件名: ").strip()
                if filename:
                    save_code(code, filename)
        
        except KeyboardInterrupt:
            print("\n\n操作已取消")
            continue
        
        except Exception as e:
            print(f"\n错误: {str(e)}")
            logger.error(f"生成失败: {str(e)}", exc_info=True)


def print_help():
    """打印帮助信息"""
    help_text = """
可用命令:
  help  - 显示此帮助信息
  info  - 显示系统信息
  quit  - 退出程序
  exit  - 退出程序
  q     - 退出程序

使用方法:
  直接输入代码需求描述，例如:
  - 实现一个线程安全的数据库连接池
  - 创建一个Redis缓存装饰器
  - 实现JWT认证中间件
"""
    print(help_text)


def print_system_info(generator: RAGCodeGenerator):
    """打印系统信息"""
    info = generator.get_system_info()
    
    print("\n" + "=" * 60)
    print("系统信息")
    print("=" * 60)
    print(f"模型已加载: {info['model_loaded']}")
    print(f"检索器可用: {info['retriever_available']}")
    print(f"运行设备: {info['device']}")
    print(f"量化方式: {info['quantization']}")
    
    if info.get('gpu_available'):
        print(f"\nGPU信息:")
        print(f"  名称: {info['gpu_name']}")
        print(f"  总显存: {info['gpu_memory_total_gb']:.2f} GB")
        print(f"  已分配: {info['gpu_memory_allocated_gb']:.2f} GB")
        print(f"  已保留: {info['gpu_memory_reserved_gb']:.2f} GB")
    else:
        print("\nGPU: 不可用")
    
    print("=" * 60)


def save_code(code: str, filename: str):
    """保存代码到文件"""
    try:
        filepath = Path(filename)
        filepath.write_text(code, encoding='utf-8')
        print(f"代码已保存到: {filepath.absolute()}")
    except Exception as e:
        print(f"保存失败: {str(e)}")


def single_query_mode(generator: RAGCodeGenerator, query: str, output: str = None):
    """单次查询模式"""
    try:
        print(f"\n查询: {query}")
        print("生成中...\n")
        
        code = generator.generate(query)
        
        # 输出结果
        if output:
            save_code(code, output)
        else:
            print("=" * 60)
            print("生成的代码:")
            print("=" * 60)
            print(code)
            print("=" * 60)
    
    except Exception as e:
        print(f"错误: {str(e)}")
        logger.error(f"生成失败: {str(e)}", exc_info=True)
        sys.exit(1)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="RAG代码生成系统命令行工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 交互模式
  python -m rag_code_generator.cli
  
  # 单次查询
  python -m rag_code_generator.cli -q "实现数据库连接池"
  
  # 保存到文件
  python -m rag_code_generator.cli -q "实现Redis缓存" -o cache.py
  
  # 使用自定义配置
  python -m rag_code_generator.cli -c custom_config.yaml
"""
    )
    
    parser.add_argument(
        '-c', '--config',
        type=str,
        default='config.yaml',
        help='配置文件路径 (默认: config.yaml)'
    )
    
    parser.add_argument(
        '-q', '--query',
        type=str,
        help='代码需求描述（单次查询模式）'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=str,
        help='输出文件路径'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='详细输出模式'
    )
    
    parser.add_argument(
        '--no-retrieval',
        action='store_true',
        help='禁用检索，仅使用模型生成'
    )
    
    args = parser.parse_args()
    
    # 配置日志
    setup_logger(args.verbose)
    
    try:
        # 加载配置
        logger.info(f"加载配置文件: {args.config}")
        config = Config(args.config)
        
        # 初始化生成器
        logger.info("初始化RAG代码生成器...")
        
        generator = RAGCodeGenerator(
            model_path=config.get('models.main_model.path'),
            embedding_index_path=config.get('retrieval.embedding_index_path'),
            bm25_index_path=config.get('retrieval.bm25_index_path'),
            device=config.get('system.device', 'cuda:0'),
            quantization=config.get('models.main_model.quantization', '4bit'),
            max_prompt_tokens=config.get('prompt.max_tokens', 2000),
            config=config.config
        )
        
        # 选择模式
        if args.query:
            # 单次查询模式
            single_query_mode(generator, args.query, args.output)
        else:
            # 交互模式
            interactive_mode(generator)
    
    except ConfigError as e:
        print(f"配置错误: {str(e)}")
        sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\n程序已中断")
        sys.exit(0)
    
    except Exception as e:
        print(f"错误: {str(e)}")
        logger.error(f"程序异常: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
