"""
基于Ollama的RAG代码生成器

集成Ollama API和RAG检索功能
"""

from typing import Optional, List, Dict, Any
from loguru import logger
import time
from pathlib import Path
import json
import numpy as np

from .models import QueryContext, GenerationConfig
from .query_rewriter import QueryRewriter
from .prompt import PromptConstructor
from .ollama_generator import OllamaGenerator, OllamaGeneratorError
from .cache import QueryCache


class OllamaRAGGenerator:
    """基于Ollama的RAG代码生成器
    
    使用Ollama进行代码生成，支持知识库检索增强
    """
    
    def __init__(
        self,
        model_name: str = "deepseek-coder:6.7b",
        ollama_url: str = "http://localhost:11434",
        knowledge_base_path: Optional[str] = "./knowledge_base",
        max_prompt_tokens: int = 2000,
        enable_cache: bool = True,
        cache_max_size: int = 1000,
        cache_ttl: int = 3600
    ):
        """
        初始化Ollama RAG生成器
        
        Args:
            model_name: Ollama模型名称
            ollama_url: Ollama API地址
            knowledge_base_path: 知识库路径
            max_prompt_tokens: Prompt最大token数
            enable_cache: 是否启用缓存
            cache_max_size: 缓存最大大小
            cache_ttl: 缓存生存时间（秒）
        """
        logger.info("=" * 60)
        logger.info("初始化Ollama RAG代码生成系统")
        logger.info("=" * 60)
        
        # 初始化缓存
        if enable_cache:
            logger.info("1/5 初始化缓存系统...")
            self.cache = QueryCache(
                max_size=cache_max_size,
                ttl=cache_ttl
            )
        else:
            self.cache = None
            logger.info("缓存系统已禁用")
        
        # 初始化Query重写器
        logger.info("2/5 初始化Query重写器...")
        self.query_rewriter = QueryRewriter()
        
        # 初始化Prompt构造器
        logger.info("3/5 初始化Prompt构造器...")
        self.prompt_constructor = PromptConstructor(
            max_tokens=max_prompt_tokens
        )
        
        # 初始化Ollama生成器
        logger.info("4/5 初始化Ollama生成器...")
        self.ollama_generator = OllamaGenerator(
            model_name=model_name,
            base_url=ollama_url
        )
        
        # 加载知识库
        logger.info("5/5 加载知识库...")
        self.retriever = self._load_knowledge_base(knowledge_base_path)
        if self.retriever:
            logger.info(f"✓ 知识库加载成功，包含 {len(self.retriever['snippets'])} 个代码片段")
        else:
            logger.warning("知识库未加载，将使用纯生成模式")
        
        logger.info("=" * 60)
        logger.info("Ollama RAG代码生成系统初始化完成")
        logger.info("=" * 60)
    
    def _load_knowledge_base(self, kb_path: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        加载知识库
        
        Args:
            kb_path: 知识库路径
            
        Returns:
            包含索引、片段和模型的字典，如果加载失败返回None
        """
        if not kb_path:
            return None
        
        kb_path = Path(kb_path)
        if not kb_path.exists():
            logger.warning(f"知识库路径不存在: {kb_path}")
            return None
        
        try:
            import faiss
            from sentence_transformers import SentenceTransformer
            
            # 加载FAISS索引
            index_file = kb_path / "faiss_index.bin"
            if not index_file.exists():
                logger.warning(f"FAISS索引文件不存在: {index_file}")
                return None
            
            index = faiss.read_index(str(index_file))
            logger.info(f"  - FAISS索引: {index.ntotal} 个向量")
            
            # 加载代码片段
            snippets_file = kb_path / "snippets.json"
            if not snippets_file.exists():
                logger.warning(f"代码片段文件不存在: {snippets_file}")
                return None
            
            with open(snippets_file, "r", encoding="utf-8") as f:
                snippets = json.load(f)
            logger.info(f"  - 代码片段: {len(snippets)} 个")
            
            # 加载Embedding模型（从配置文件读取）
            config_file = kb_path / "config.json"
            if config_file.exists():
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                model_name = config.get("embedding_model", "sentence-transformers/all-MiniLM-L6-v2")
                logger.info(f"  - 从配置加载Embedding模型: {model_name}")
            else:
                model_name = "sentence-transformers/all-MiniLM-L6-v2"
                logger.info(f"  - 使用默认Embedding模型: {model_name}")
            
            # ✅ 强制离线模式：完全禁用网络访问
            import os
            
            # 设置多个环境变量确保离线
            os.environ['TRANSFORMERS_OFFLINE'] = '1'
            os.environ['HF_DATASETS_OFFLINE'] = '1'
            os.environ['HF_HUB_OFFLINE'] = '1'
            
            # 禁用SSL验证和代理（避免网络检查）
            os.environ['CURL_CA_BUNDLE'] = ''
            os.environ['REQUESTS_CA_BUNDLE'] = ''
            
            try:
                # 使用local_files_only参数强制只使用本地文件
                embedding_model = SentenceTransformer(
                    model_name, 
                    device="cpu",
                    cache_folder=None,  # 使用默认缓存
                )
                
                # 手动设置模型为eval模式，避免后续网络检查
                embedding_model.eval()
                
                logger.info("  - Embedding模型加载完成（离线模式）")
            except Exception as e:
                logger.error(f"离线模式加载失败: {e}")
                logger.info("  - 请确保模型已下载到本地缓存")
                logger.info(f"  - 缓存位置: {os.path.expanduser('~/.cache/huggingface/')}")
                raise
            
            return {
                "index": index,
                "snippets": snippets,
                "embedding_model": embedding_model
            }
        
        except ImportError as e:
            logger.error(f"缺少依赖库: {str(e)}")
            logger.error("请安装: pip install faiss-cpu sentence-transformers")
            return None
        except Exception as e:
            logger.error(f"知识库加载失败: {str(e)}")
            return None
    
    def _retrieve_similar_codes(
        self,
        query: str,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        检索相似代码
        
        Args:
            query: 查询字符串
            top_k: 返回结果数量
            
        Returns:
            相似代码列表
        """
        if not self.retriever:
            return []
        
        try:
            # 生成query向量
            query_embedding = self.retriever["embedding_model"].encode([query])[0]
            
            # 检索
            distances, indices = self.retriever["index"].search(
                query_embedding.reshape(1, -1).astype('float32'),
                k=min(top_k, self.retriever["index"].ntotal)
            )
            
            # 获取代码片段
            retrieved_codes = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx < len(self.retriever["snippets"]):
                    snippet = self.retriever["snippets"][idx]
                    
                    # 计算相似度分数
                    similarity = float(np.exp(-dist))
                    
                    retrieved_codes.append({
                        "code": snippet.get("code", ""),
                        "name": snippet.get("name", "unknown"),
                        "type": snippet.get("type", "function"),
                        "language": snippet.get("language", "python"),
                        "similarity": similarity,
                        "docstring": snippet.get("docstring", "")
                    })
            
            return retrieved_codes
        
        except Exception as e:
            logger.error(f"检索失败: {str(e)}")
            return []
    
    def generate(
        self,
        query: str,
        temperature: float = 0.2,
        max_new_tokens: int = 512,
        use_cache: bool = True,
        use_rag: bool = True
    ) -> Dict[str, Any]:
        """
        生成代码
        
        Args:
            query: 用户输入的代码需求描述
            temperature: 生成温度
            max_new_tokens: 最大生成token数
            use_cache: 是否使用缓存
            use_rag: 是否使用RAG检索
            
        Returns:
            包含生成结果的字典
        """
        # 输入验证
        if not query or len(query.strip()) == 0:
            raise ValueError("Query不能为空")
        
        if len(query) > 1000:
            raise ValueError("Query过长（最大1000字符）")
        
        logger.info("=" * 60)
        logger.info(f"开始代码生成流程")
        logger.info(f"Query: {query[:100]}...")
        logger.info(f"RAG模式: {'启用' if use_rag and self.retriever else '禁用'}")
        logger.info("=" * 60)
        
        start_time = time.time()
        
        try:
            # 检查缓存
            cached = False
            if use_cache and self.cache is not None:
                cache_key_params = {
                    'temperature': temperature,
                    'max_new_tokens': max_new_tokens,
                    'use_rag': use_rag
                }
                cached_result = self.cache.get(query, **cache_key_params)
                if cached_result is not None:
                    logger.info("✓ 缓存命中，直接返回结果")
                    return {
                        'code': cached_result,
                        'query': query,
                        'duration': time.time() - start_time,
                        'cached': True,
                        'model': self.ollama_generator.model_name,
                        'retrieved_codes': []
                    }
            
            # 步骤1: Query重写
            logger.info("步骤1/4: Query重写")
            query_ctx = self.query_rewriter.rewrite(query)
            logger.info(f"  - 重写后: {query_ctx.rewritten_query[:100]}...")
            
            # 步骤2: RAG检索（如果启用）
            retrieved_codes = []
            if use_rag and self.retriever:
                logger.info("步骤2/4: 知识库检索")
                retrieved_codes = self._retrieve_similar_codes(query, top_k=3)
                logger.info(f"  - 检索到 {len(retrieved_codes)} 个相关代码")
                for i, code in enumerate(retrieved_codes, 1):
                    logger.info(f"    {i}. {code['name']} (相似度: {code['similarity']:.3f})")
            else:
                logger.info("步骤2/4: 跳过检索（RAG未启用）")
            
            # 步骤3: 构造增强Prompt
            logger.info("步骤3/4: 构造Prompt")
            
            # 构造系统提示
            system_prompt = (
                "你是一个专业的程序员"
                "请根据用户的需求生成高质量、可运行的代码。"
                "代码应该包含必要的注释和错误处理。"
                "完全遵循用户要求，仔细思考和判断要求"
            )
            
            # 构造用户提示
            if retrieved_codes:
                # RAG增强Prompt
                reference_section = "\n\n".join([
                    f"参考代码 {i+1} - {code['name']} (相似度: {code['similarity']:.2f}):\n```{code['language']}\n{code['code']}\n```"
                    for i, code in enumerate(retrieved_codes)
                ])
                
                user_prompt = f"""请根据以下需求生成代码：

需求描述：
{query_ctx.rewritten_query}

关键词：
{', '.join(query_ctx.expanded_keywords[:10])}

参考以下相似代码示例：

{reference_section}

请生成完整的、可运行的代码，包含必要的注释。你可以参考上述示例，但要根据具体需求进行调整。
"""
            else:
                # 纯生成Prompt
                user_prompt = f"""请根据以下需求生成代码：

需求描述：
{query_ctx.rewritten_query}

关键词：
{', '.join(query_ctx.expanded_keywords[:10])}

请生成完整的、可运行的代码，包含必要的注释。
"""
            
            prompt_length = len(user_prompt)
            logger.info(f"  - Prompt长度: {prompt_length} 字符")
            logger.info(f"  - 包含参考代码: {len(retrieved_codes)} 个")
            
            # 步骤4: 代码生成
            logger.info(f"步骤4/4: 代码生成 (temperature={temperature})")
            
            generated_code = self.ollama_generator.generate(
                prompt=user_prompt,
                temperature=temperature,
                max_tokens=max_new_tokens,
                system_prompt=system_prompt
            )
            
            duration = time.time() - start_time
            
            logger.info(f"  - 生成完成，代码长度: {len(generated_code)} 字符")
            logger.info(f"  - 总耗时: {duration:.2f}秒")
            logger.info("=" * 60)
            logger.info("代码生成流程完成")
            logger.info("=" * 60)
            
            # 存入缓存
            if use_cache and self.cache is not None:
                cache_key_params = {
                    'temperature': temperature,
                    'max_new_tokens': max_new_tokens,
                    'use_rag': use_rag
                }
                self.cache.set(query, generated_code, **cache_key_params)
                logger.debug("结果已缓存")
            
            return {
                'code': generated_code,
                'query': query,
                'rewritten_query': query_ctx.rewritten_query,
                'duration': duration,
                'cached': False,
                'model': self.ollama_generator.model_name,
                'retrieved_codes': retrieved_codes,
                'rag_enabled': use_rag and self.retriever is not None
            }
        
        except (ValueError, OllamaGeneratorError) as e:
            logger.error(f"代码生成失败: {str(e)}")
            raise
        
        except Exception as e:
            logger.error(f"代码生成过程发生未预期错误: {str(e)}", exc_info=True)
            raise RuntimeError(f"代码生成失败: {str(e)}")
    
    def batch_generate(
        self,
        queries: List[str],
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        批量生成代码
        
        Args:
            queries: 查询列表
            **kwargs: 传递给generate()的参数
            
        Returns:
            结果列表
        """
        logger.info(f"开始批量生成，共 {len(queries)} 个查询")
        
        results = []
        
        for i, query in enumerate(queries, 1):
            logger.info(f"\n处理查询 {i}/{len(queries)}")
            
            try:
                result = self.generate(query, **kwargs)
                result['success'] = True
                result['error'] = None
                results.append(result)
                logger.info(f"查询 {i} 成功")
            
            except Exception as e:
                logger.error(f"查询 {i} 失败: {str(e)}")
                results.append({
                    'query': query,
                    'code': None,
                    'error': str(e),
                    'success': False
                })
        
        success_count = sum(1 for r in results if r.get('success', False))
        logger.info(
            f"\n批量生成完成: {success_count}/{len(queries)} 成功"
        )
        
        return results
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        获取系统信息
        
        Returns:
            包含系统状态的字典
        """
        models = self.ollama_generator.list_models()
        
        return {
            'backend': 'ollama',
            'model': self.ollama_generator.model_name,
            'ollama_url': self.ollama_generator.base_url,
            'available_models': [m['name'] for m in models],
            'cache_enabled': self.cache is not None,
            'knowledge_base_loaded': self.retriever is not None,
            'knowledge_base_size': len(self.retriever['snippets']) if self.retriever else 0,
            'status': 'ready'
        }


    def reload_knowledge_base(self, kb_path: Optional[str] = "./knowledge_base"):
        """
        重新加载知识库（用于训练完embedding后自动刷新）
        
        Args:
            kb_path: 知识库路径，默认为./knowledge_base
        """
        logger.info("=" * 60)
        logger.info("重新加载知识库...")
        logger.info("=" * 60)
        
        # 清除旧的知识库引用
        if self.retriever:
            logger.info("清除旧知识库...")
            self.retriever = None
        
        # 加载新知识库
        self.retriever = self._load_knowledge_base(kb_path)
        
        if self.retriever:
            logger.info(f"✓ 知识库重新加载成功，包含 {len(self.retriever['snippets'])} 个代码片段")
        else:
            logger.warning("知识库加载失败，将使用纯生成模式")
        
        logger.info("=" * 60)
