"""RAG代码生成器主控制器

协调所有模块完成代码生成任务。

支持需求：
- 1.1: 协调Query重写、检索、Prompt构造、代码生成
- 5.1: 完整的端到端生成流程
- 9.5: 单次请求失败不影响后续请求
"""

import numpy as np
from typing import Optional, List, Dict, Any
from pathlib import Path
from loguru import logger

from .models import QueryContext, GenerationConfig
from .query_rewriter import QueryRewriter
from .retrieval import MultiStageRetriever
from .prompt import PromptConstructor
from .generator import CodeGenerator, ModelLoadError, GenerationTimeoutError
from .cache import QueryCache


class RAGCodeGenerator:
    """RAG代码生成器主控制器
    
    整合所有模块，提供统一的代码生成接口。
    """
    
    def __init__(
        self,
        model_path: str,
        embedding_index_path: Optional[str] = None,
        bm25_index_path: Optional[str] = None,
        device: str = "cuda:0",
        quantization: str = "4bit",
        max_prompt_tokens: int = 2000,
        enable_cache: bool = True,
        cache_max_size: int = 1000,
        cache_ttl: int = 3600,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化RAG代码生成器
        
        Args:
            model_path: DeepSeekCoder模型路径
            embedding_index_path: FAISS索引路径
            bm25_index_path: BM25索引路径
            device: 运行设备
            quantization: 量化方式
            max_prompt_tokens: Prompt最大token数
            enable_cache: 是否启用缓存
            cache_max_size: 缓存最大大小
            cache_ttl: 缓存生存时间（秒）
            config: 额外配置字典
            
        Raises:
            ModelLoadError: 模型加载失败
        """
        self.config = config or {}
        
        logger.info("=" * 60)
        logger.info("初始化RAG代码生成系统")
        logger.info("=" * 60)
        
        # 初始化缓存系统
        if enable_cache:
            logger.info("0/5 初始化缓存系统...")
            self.cache = QueryCache(
                max_size=cache_max_size,
                ttl=cache_ttl
            )
        else:
            self.cache = None
            logger.info("缓存系统已禁用")
        
        # 初始化Query重写器
        logger.info("1/5 初始化Query重写器...")
        self.query_rewriter = QueryRewriter()
        
        # 初始化检索器
        logger.info("2/5 初始化多阶段检索器...")
        if embedding_index_path and bm25_index_path:
            self.retriever = MultiStageRetriever(
                embedding_index_path=embedding_index_path,
                bm25_index_path=bm25_index_path,
                device=device
            )
        else:
            logger.warning("未提供索引路径，检索功能将不可用")
            self.retriever = None
        
        # 初始化Prompt构造器
        logger.info("3/5 初始化Prompt构造器...")
        self.prompt_constructor = PromptConstructor(
            max_tokens=max_prompt_tokens
        )
        
        # 初始化代码生成器
        logger.info("4/5 初始化代码生成器...")
        self.code_generator = CodeGenerator(
            model_path=model_path,
            device=device,
            quantization=quantization,
            load_in_4bit=(quantization == "4bit")
        )
        
        logger.info("=" * 60)
        logger.info("RAG代码生成系统初始化完成")
        logger.info("=" * 60)
    
    def generate(
        self,
        query: str,
        top_k: int = 3,
        temperature: float = 0.2,
        max_new_tokens: int = 512,
        use_retrieval: bool = True,
        generation_config: Optional[GenerationConfig] = None
    ) -> str:
        """
        生成代码
        
        支持需求：
        - 1.1: 协调完整的生成流程
        - 5.1: 端到端代码生成
        - 9.5: 错误隔离，单次失败不影响系统
        
        Args:
            query: 用户输入的代码需求描述
            top_k: 检索代码片段数量
            temperature: 生成温度
            max_new_tokens: 最大生成token数
            use_retrieval: 是否使用检索（False时仅用模型生成）
            generation_config: 生成配置对象（可选）
            
        Returns:
            生成的代码字符串
            
        Raises:
            ValueError: 输入无效
            GenerationTimeoutError: 生成超时
            RuntimeError: 生成失败
        """
        # 输入验证
        if not query or len(query.strip()) == 0:
            raise ValueError("Query不能为空")
        
        if len(query) > 1000:
            raise ValueError("Query过长（最大1000字符）")
        
        logger.info("=" * 60)
        logger.info(f"开始代码生成流程")
        logger.info(f"Query: {query[:100]}...")
        logger.info("=" * 60)
        
        try:
            # 检查缓存
            if self.cache is not None:
                cache_key_params = {
                    'top_k': top_k,
                    'temperature': temperature,
                    'max_new_tokens': max_new_tokens,
                    'use_retrieval': use_retrieval
                }
                cached_result = self.cache.get(query, **cache_key_params)
                if cached_result is not None:
                    logger.info("✓ 缓存命中，直接返回结果")
                    return cached_result
            
            # 步骤1: Query重写
            logger.info("步骤1/4: Query重写")
            query_ctx = self.query_rewriter.rewrite(query)
            logger.info(f"  - 重写后: {query_ctx.rewritten_query[:100]}...")
            logger.info(f"  - 扩展关键词: {len(query_ctx.expanded_keywords)} 个")
            
            # 步骤2: 多阶段检索
            retrieved_results = []
            if use_retrieval and self.retriever is not None:
                logger.info(f"步骤2/4: 多阶段检索 (top_k={top_k})")
                try:
                    # 这里简化处理，实际应该生成query_embedding
                    # TODO: 集成embedding模型生成query向量
                    query_embedding = None
                    
                    retrieved_results = self.retriever.retrieve(
                        query_ctx=query_ctx,
                        query_embedding=query_embedding,
                        top_k=top_k
                    )
                    logger.info(f"  - 检索到 {len(retrieved_results)} 个代码片段")
                    
                    for i, result in enumerate(retrieved_results, 1):
                        logger.info(
                            f"    {i}. {result.snippet.path} "
                            f"(分数: {result.score:.3f}, "
                            f"质量: {result.snippet.quality_score}/10)"
                        )
                
                except Exception as e:
                    logger.error(f"检索失败: {str(e)}")
                    logger.warning("将继续使用空检索结果生成代码")
                    retrieved_results = []
            else:
                logger.info("步骤2/4: 跳过检索（use_retrieval=False 或检索器未初始化）")
            
            # 步骤3: 构造Prompt
            logger.info("步骤3/4: 构造Prompt")
            prompt = self.prompt_constructor.construct(
                query=query,
                retrieved_snippets=retrieved_results
            )
            
            prompt_length = len(prompt)
            prompt_tokens = self.prompt_constructor.count_tokens(prompt)
            logger.info(f"  - Prompt长度: {prompt_length} 字符")
            logger.info(f"  - 估算token数: {prompt_tokens}")
            
            # 步骤4: 代码生成
            logger.info(f"步骤4/4: 代码生成 (temperature={temperature}, max_tokens={max_new_tokens})")
            
            # 使用generation_config或默认参数
            if generation_config:
                generated_code = self.code_generator.generate(
                    prompt=prompt,
                    temperature=generation_config.temperature,
                    max_new_tokens=generation_config.max_new_tokens,
                    top_p=generation_config.top_p,
                    top_k=generation_config.top_k,
                    do_sample=generation_config.do_sample,
                    repetition_penalty=generation_config.repetition_penalty
                )
            else:
                generated_code = self.code_generator.generate(
                    prompt=prompt,
                    temperature=temperature,
                    max_new_tokens=max_new_tokens
                )
            
            logger.info(f"  - 生成完成，代码长度: {len(generated_code)} 字符")
            logger.info("=" * 60)
            logger.info("代码生成流程完成")
            logger.info("=" * 60)
            
            # 存入缓存
            if self.cache is not None:
                cache_key_params = {
                    'top_k': top_k,
                    'temperature': temperature,
                    'max_new_tokens': max_new_tokens,
                    'use_retrieval': use_retrieval
                }
                self.cache.set(query, generated_code, **cache_key_params)
                logger.debug("结果已缓存")
            
            return generated_code
        
        except (ValueError, GenerationTimeoutError) as e:
            # 这些是预期的错误，直接抛出
            logger.error(f"代码生成失败: {str(e)}")
            raise
        
        except Exception as e:
            # 其他未预期的错误，包装后抛出
            logger.error(f"代码生成过程发生未预期错误: {str(e)}", exc_info=True)
            raise RuntimeError(f"代码生成失败: {str(e)}")
    
    def batch_generate(
        self,
        queries: List[str],
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        批量生成代码
        
        支持需求：
        - 12.1: 依次处理每个查询
        - 12.2: 复用已加载的模型和索引
        - 12.3: 单个查询失败不影响其他查询
        
        Args:
            queries: 查询列表
            **kwargs: 传递给generate()的参数
            
        Returns:
            结果列表，每个元素包含query、code和error字段
        """
        logger.info(f"开始批量生成，共 {len(queries)} 个查询")
        
        results = []
        
        for i, query in enumerate(queries, 1):
            logger.info(f"\n处理查询 {i}/{len(queries)}")
            
            try:
                code = self.generate(query, **kwargs)
                results.append({
                    'query': query,
                    'code': code,
                    'error': None,
                    'success': True
                })
                logger.info(f"查询 {i} 成功")
            
            except Exception as e:
                # 单个失败不影响其他查询（支持需求12.3）
                logger.error(f"查询 {i} 失败: {str(e)}")
                results.append({
                    'query': query,
                    'code': None,
                    'error': str(e),
                    'success': False
                })
        
        success_count = sum(1 for r in results if r['success'])
        logger.info(
            f"\n批量生成完成: {success_count}/{len(queries)} 成功, "
            f"{len(queries) - success_count} 失败"
        )
        
        return results
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        获取系统信息
        
        Returns:
            包含系统状态的字典
        """
        import torch
        
        info = {
            'retriever_available': self.retriever is not None,
            'model_loaded': self.code_generator.model is not None,
            'device': self.code_generator.device,
            'quantization': self.code_generator.quantization,
        }
        
        # GPU信息
        if torch.cuda.is_available():
            device_id = 0
            if ":" in self.code_generator.device:
                device_id = int(self.code_generator.device.split(":")[-1])
            
            info['gpu_available'] = True
            info['gpu_name'] = torch.cuda.get_device_name(device_id)
            info['gpu_memory_allocated_gb'] = torch.cuda.memory_allocated(device_id) / (1024**3)
            info['gpu_memory_reserved_gb'] = torch.cuda.memory_reserved(device_id) / (1024**3)
            info['gpu_memory_total_gb'] = torch.cuda.get_device_properties(device_id).total_memory / (1024**3)
        else:
            info['gpu_available'] = False
        
        return info
    
    def __del__(self):
        """析构函数，确保资源释放"""
        logger.debug("RAGCodeGenerator析构")
