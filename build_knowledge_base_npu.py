"""
构建知识库 - 使用Intel NPU加速

支持Intel Core Ultra处理器的NPU加速Embedding生成
"""

# ✅ 在导入任何库之前设置离线模式环境变量
import os
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_DATASETS_OFFLINE'] = '1'
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np
from tqdm import tqdm
from loguru import logger
import pickle

try:
    from rank_bm25 import BM25Okapi
    HAS_BM25 = True
except ImportError:
    HAS_BM25 = False
    logger.warning("rank_bm25未安装，BM25索引功能将不可用")


class CodeSnippet:
    """代码片段"""
    def __init__(
        self,
        code: str,
        path: str,
        language: str,
        description: str = "",
        metadata: Optional[Dict] = None
    ):
        self.code = code
        self.path = path
        self.language = language
        self.description = description
        self.metadata = metadata or {}


class NPUKnowledgeBaseBuilder:
    """使用Intel NPU的知识库构建器"""
    
    def __init__(
        self,
        embedding_model: str = "sentence-transformers/all-mpnet-base-v2",
        output_dir: str = "./knowledge_base",
        use_npu: bool = False,
        append_mode: bool = True
    ):
        """
        初始化知识库构建器
        
        Args:
            embedding_model: Embedding模型名称
            output_dir: 输出目录
            use_npu: 是否使用Intel NPU
            append_mode: 是否追加模式（True=叠加，False=覆盖）
        """
        self.embedding_model_name = embedding_model
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.use_npu = use_npu
        self.append_mode = append_mode
        
        self.snippets: List[CodeSnippet] = []
        self.embeddings: Optional[np.ndarray] = None
        
        logger.info(f"初始化NPU知识库构建器")
        logger.info(f"  Embedding模型: {embedding_model}")
        logger.info(f"  输出目录: {output_dir}")
        logger.info(f"  使用NPU: {use_npu}")
        logger.info(f"  模式: {'叠加' if append_mode else '覆盖'}")
    
    def _check_npu_available(self) -> bool:
        """检查Intel NPU是否可用"""
        try:
            import openvino as ov
            core = ov.Core()
            devices = core.available_devices
            
            # 检查是否有NPU设备
            npu_available = 'NPU' in devices
            
            if npu_available:
                logger.info("✓ Intel NPU可用")
                logger.info(f"  可用设备: {devices}")
            else:
                logger.warning("⚠️  Intel NPU不可用")
                logger.info(f"  可用设备: {devices}")
            
            return npu_available
        
        except ImportError:
            logger.warning("⚠️  OpenVINO未安装，无法使用NPU")
            logger.info("  安装: pip install openvino openvino-dev")
            return False
        except Exception as e:
            logger.warning(f"⚠️  检查NPU失败: {str(e)}")
            return False
    
    def collect_from_directory(
        self,
        directory: str,
        extensions: List[str] = [".py", ".js", ".java", ".cpp", ".go"],
        max_files: int = 1000
    ):
        """从目录收集代码文件"""
        logger.info(f"从目录收集代码: {directory}")
        
        directory = Path(directory)
        collected = 0
        
        for ext in extensions:
            for file_path in directory.rglob(f"*{ext}"):
                if collected >= max_files:
                    break
                
                if any(skip in str(file_path) for skip in [
                    'node_modules', '__pycache__', '.git', 'venv', 'env'
                ]):
                    continue
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        code = f.read()
                    
                    if len(code) < 50 or len(code) > 10000:
                        continue
                    
                    snippet = CodeSnippet(
                        code=code,
                        path=str(file_path.relative_to(directory)),
                        language=ext[1:],
                        description=f"Code from {file_path.name}"
                    )
                    
                    self.snippets.append(snippet)
                    collected += 1
                
                except Exception as e:
                    logger.warning(f"读取文件失败 {file_path}: {str(e)}")
        
        logger.info(f"✓ 收集了 {len(self.snippets)} 个代码片段")
    
    def collect_from_json(self, json_file: str):
        """从JSON文件加载代码片段（兼容V3.5格式）"""
        logger.info(f"从JSON加载代码片段: {json_file}")
        
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for item in data:
            # ✅ 兼容V3.5格式：content/code, file_path/path
            code = item.get('content', item.get('code', ''))
            path = item.get('file_path', item.get('path', 'unknown'))
            
            # 生成描述（优先使用summary，否则使用description或name）
            description = item.get('summary', item.get('description', ''))
            if not description and item.get('name'):
                chunk_type = item.get('chunk_type', 'code')
                description = f"{chunk_type}: {item['name']}"
            
            # 合并元数据（保留V3.5的额外字段）
            metadata = item.get('metadata', {})
            
            # ✅ 添加V3.5特有字段到metadata
            if 'tokens' in item:
                metadata['tokens'] = item['tokens']
            if 'quality_score' in item:
                metadata['quality_score'] = item['quality_score']
            if 'semantic_completeness' in item:
                metadata['semantic_completeness'] = item['semantic_completeness']
            if 'start_line' in item:
                metadata['start_line'] = item['start_line']
            if 'end_line' in item:
                metadata['end_line'] = item['end_line']
            if 'chunk_type' in item:
                metadata['chunk_type'] = item['chunk_type']
            if 'context' in item:
                metadata['context'] = item['context']
            
            snippet = CodeSnippet(
                code=code,
                path=path,
                language=item.get('language', 'unknown'),
                description=description,
                metadata=metadata
            )
            self.snippets.append(snippet)
        
        logger.info(f"✓ 加载了 {len(self.snippets)} 个代码片段")
    
    def load_existing_knowledge_base(self):
        """加载现有知识库（用于叠加模式）"""
        snippets_path = self.output_dir / "snippets.json"
        embeddings_path = self.output_dir / "embeddings.npy"
        
        if not snippets_path.exists():
            logger.info("没有现有知识库，将创建新的")
            return
        
        logger.info("加载现有知识库...")
        
        # 加载现有片段（兼容V3.5格式）
        with open(snippets_path, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
        
        existing_snippets = []
        for item in existing_data:
            # ✅ 兼容V3.5格式
            code = item.get('content', item.get('code', ''))
            path = item.get('file_path', item.get('path', 'unknown'))
            
            snippet = CodeSnippet(
                code=code,
                path=path,
                language=item.get('language', 'unknown'),
                description=item.get('description', item.get('summary', '')),
                metadata=item.get('metadata', {})
            )
            existing_snippets.append(snippet)
        
        # 加载现有embeddings
        existing_embeddings = None
        if embeddings_path.exists():
            existing_embeddings = np.load(embeddings_path)
        
        logger.info(f"✓ 加载了 {len(existing_snippets)} 个现有片段")
        
        return existing_snippets, existing_embeddings
    
    def merge_with_existing(self, existing_snippets: List[CodeSnippet], existing_embeddings: Optional[np.ndarray]):
        """合并现有知识库和新片段"""
        if not existing_snippets:
            return
        
        logger.info("合并现有知识库和新片段...")
        
        # 去重：基于代码内容的哈希
        existing_hashes = set()
        for snippet in existing_snippets:
            code_hash = hash(snippet.code)
            existing_hashes.add(code_hash)
        
        # 过滤重复的新片段
        new_snippets = []
        duplicates = 0
        for snippet in self.snippets:
            code_hash = hash(snippet.code)
            if code_hash not in existing_hashes:
                new_snippets.append(snippet)
                existing_hashes.add(code_hash)
            else:
                duplicates += 1
        
        logger.info(f"  - 现有片段: {len(existing_snippets)}")
        logger.info(f"  - 新片段: {len(new_snippets)}")
        logger.info(f"  - 重复片段（已跳过）: {duplicates}")
        
        # 合并片段列表
        self.snippets = existing_snippets + new_snippets
        
        # 保存现有embeddings，稍后只为新片段生成embeddings
        self.existing_embeddings = existing_embeddings
        self.new_snippets_count = len(new_snippets)
        
        logger.info(f"✓ 合并后总片段数: {len(self.snippets)}")
    
    def _convert_model_to_openvino(self, model_name: str) -> str:
        """将模型转换为OpenVINO格式"""
        logger.info("转换模型为OpenVINO格式...")
        
        try:
            from optimum.intel import OVModelForFeatureExtraction
            from transformers import AutoTokenizer
            
            ov_model_dir = self.output_dir / "ov_model"
            ov_model_dir.mkdir(exist_ok=True)
            
            # 检查是否已转换
            if (ov_model_dir / "openvino_model.xml").exists():
                logger.info("✓ 模型已转换，跳过")
                return str(ov_model_dir)
            
            logger.info("首次转换，这可能需要几分钟...")
            
            # 导出为OpenVINO格式
            model = OVModelForFeatureExtraction.from_pretrained(
                model_name,
                export=True,
                compile=False
            )
            
            # 保存
            model.save_pretrained(ov_model_dir)
            
            # 保存tokenizer
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            tokenizer.save_pretrained(ov_model_dir)
            
            logger.info(f"✓ 模型已转换并保存到: {ov_model_dir}")
            return str(ov_model_dir)
        
        except Exception as e:
            logger.error(f"✗ 模型转换失败: {str(e)}")
            raise
    
    def generate_embeddings_npu(self, batch_size: int = 32):
        """使用Intel NPU生成Embedding"""
        logger.info("使用Intel NPU生成Embedding...")
        
        try:
            from optimum.intel import OVModelForFeatureExtraction
            from transformers import AutoTokenizer
            import torch
        except ImportError:
            logger.error("请安装依赖: pip install optimum[openvino] transformers")
            raise
        
        # 检查NPU
        npu_available = self._check_npu_available()
        device = "NPU" if (npu_available and self.use_npu) else "CPU"
        
        logger.info(f"使用设备: {device}")
        
        # 转换模型
        ov_model_path = self._convert_model_to_openvino(self.embedding_model_name)
        
        # 加载模型
        logger.info(f"加载OpenVINO模型...")
        model = OVModelForFeatureExtraction.from_pretrained(
            ov_model_path,
            device=device
        )
        tokenizer = AutoTokenizer.from_pretrained(ov_model_path)
        
        # 准备文本
        texts = []
        for snippet in self.snippets:
            text = f"{snippet.description}\n\n{snippet.code}"
            texts.append(text)
        
        # 生成Embedding
        logger.info(f"生成 {len(texts)} 个Embedding...")
        all_embeddings = []
        
        for i in tqdm(range(0, len(texts), batch_size), desc="生成Embedding"):
            batch_texts = texts[i:i+batch_size]
            
            # Tokenize
            inputs = tokenizer(
                batch_texts,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt"
            )
            
            # 推理
            with torch.no_grad():
                outputs = model(**inputs)
            
            # 提取embedding（使用[CLS] token或mean pooling）
            embeddings = outputs.last_hidden_state[:, 0, :].numpy()
            all_embeddings.append(embeddings)
        
        self.embeddings = np.vstack(all_embeddings)
        logger.info(f"✓ Embedding生成完成，维度: {self.embeddings.shape}")
    
    def generate_embeddings_cpu(self, batch_size: int = 32):
        """使用CPU生成Embedding（备用方案）"""
        logger.info("使用CPU生成Embedding...")
        
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            logger.error("请安装: pip install sentence-transformers")
            raise
        
        # 加载模型
        logger.info(f"加载Embedding模型: {self.embedding_model_name}")
        model = SentenceTransformer(self.embedding_model_name, device='cpu')
        
        # 准备文本
        texts = []
        for snippet in self.snippets:
            text = f"{snippet.description}\n\n{snippet.code}"
            texts.append(text)
        
        # 生成Embedding
        logger.info(f"生成 {len(texts)} 个Embedding...")
        embeddings = model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_numpy=True
        )
        
        self.embeddings = embeddings
        logger.info(f"✓ Embedding生成完成，维度: {embeddings.shape}")
    
    def generate_embeddings(self, batch_size: int = 32):
        """生成Embedding（自动选择NPU或CPU）"""
        # 如果是叠加模式且有现有embeddings，只为新片段生成
        if self.append_mode and hasattr(self, 'existing_embeddings') and self.existing_embeddings is not None:
            logger.info("叠加模式：只为新片段生成Embedding...")
            
            # 只处理新片段
            new_snippets_start = len(self.snippets) - self.new_snippets_count
            new_snippets = self.snippets[new_snippets_start:]
            
            # 临时保存完整片段列表
            all_snippets = self.snippets
            self.snippets = new_snippets
            
            # 生成新片段的embeddings
            if self.use_npu:
                try:
                    self.generate_embeddings_npu(batch_size)
                except Exception as e:
                    logger.warning(f"NPU生成失败，回退到CPU: {str(e)}")
                    self.generate_embeddings_cpu(batch_size)
            else:
                self.generate_embeddings_cpu(batch_size)
            
            # 合并embeddings
            new_embeddings = self.embeddings
            self.embeddings = np.vstack([self.existing_embeddings, new_embeddings])
            
            # 恢复完整片段列表
            self.snippets = all_snippets
            
            logger.info(f"✓ 合并后Embedding总数: {self.embeddings.shape[0]}")
        else:
            # 正常模式：为所有片段生成embeddings
            if self.use_npu:
                try:
                    self.generate_embeddings_npu(batch_size)
                except Exception as e:
                    logger.warning(f"NPU生成失败，回退到CPU: {str(e)}")
                    self.generate_embeddings_cpu(batch_size)
            else:
                self.generate_embeddings_cpu(batch_size)
    
    def build_faiss_index(self):
        """构建FAISS向量索引"""
        logger.info("构建FAISS索引...")
        
        try:
            import faiss
        except ImportError:
            logger.error("请安装: pip install faiss-cpu")
            raise
        
        if self.embeddings is None:
            raise ValueError("请先生成Embedding")
        
        dimension = self.embeddings.shape[1]
        index = faiss.IndexFlatL2(dimension)
        index.add(self.embeddings.astype('float32'))
        
        index_path = self.output_dir / "faiss_index.bin"
        faiss.write_index(index, str(index_path))
        
        logger.info(f"✓ FAISS索引已保存: {index_path}")
    
    def build_bm25_index(self):
        """构建BM25关键词索引"""
        logger.info("构建BM25索引...")
        
        if not HAS_BM25:
            logger.warning("跳过BM25索引（rank_bm25未安装）")
            return
        
        tokenized_corpus = []
        for snippet in tqdm(self.snippets, desc="分词"):
            text = f"{snippet.description} {snippet.code}"
            tokens = text.lower().split()
            tokenized_corpus.append(tokens)
        
        bm25 = BM25Okapi(tokenized_corpus)
        
        index_path = self.output_dir / "bm25_index.pkl"
        with open(index_path, 'wb') as f:
            pickle.dump(bm25, f)
        
        logger.info(f"✓ BM25索引已保存: {index_path}")
    
    def save_snippets(self):
        """保存代码片段"""
        snippets_data = []
        for snippet in self.snippets:
            snippets_data.append({
                'code': snippet.code,
                'path': snippet.path,
                'language': snippet.language,
                'description': snippet.description,
                'metadata': snippet.metadata
            })
        
        json_path = self.output_dir / "snippets.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(snippets_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✓ 代码片段已保存: {json_path}")
    
    def save_embeddings(self):
        """保存Embedding"""
        if self.embeddings is None:
            return
        
        embeddings_path = self.output_dir / "embeddings.npy"
        np.save(embeddings_path, self.embeddings)
        logger.info(f"✓ Embedding已保存: {embeddings_path}")
    
    def build(self):
        """执行完整构建流程"""
        logger.info("=" * 60)
        logger.info(f"开始构建知识库（{'叠加' if self.append_mode else '覆盖'}模式）")
        logger.info("=" * 60)
        
        if len(self.snippets) == 0:
            raise ValueError("没有代码片段")
        
        # 如果是叠加模式，先加载现有知识库
        if self.append_mode:
            result = self.load_existing_knowledge_base()
            if result:
                existing_snippets, existing_embeddings = result
                self.merge_with_existing(existing_snippets, existing_embeddings)
        
        self.generate_embeddings()
        self.build_faiss_index()
        self.build_bm25_index()
        self.save_snippets()
        self.save_embeddings()
        
        logger.info("=" * 60)
        logger.info("知识库构建完成！")
        logger.info("=" * 60)
        logger.info(f"输出目录: {self.output_dir}")
        logger.info(f"代码片段数: {len(self.snippets)}")
        
        self._save_config()
    
    def _save_config(self):
        """保存配置"""
        config = {
            'embedding_model': self.embedding_model_name,
            'num_snippets': len(self.snippets),
            'embedding_dim': int(self.embeddings.shape[1]) if self.embeddings is not None else 0,
            'use_npu': self.use_npu,
            'files': {
                'faiss_index': 'faiss_index.bin',
                'bm25_index': 'bm25_index.pkl',
                'snippets': 'snippets.json',
                'embeddings': 'embeddings.npy'
            }
        }
        
        config_path = self.output_dir / "config.json"
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"✓ 配置已保存: {config_path}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="构建知识库（Intel NPU加速）")
    parser.add_argument("--source", required=True, help="代码源")
    parser.add_argument("--output", default="./knowledge_base", help="输出目录")
    parser.add_argument("--model", default="sentence-transformers/all-MiniLM-L6-v2", help="模型")
    parser.add_argument("--no-npu", action="store_true", help="禁用NPU")
    parser.add_argument("--extensions", default=".py,.js,.java", help="文件扩展名")
    parser.add_argument("--max-files", type=int, default=1000, help="最大文件数")
    
    args = parser.parse_args()
    
    builder = NPUKnowledgeBaseBuilder(
        embedding_model=args.model,
        output_dir=args.output,
        use_npu=not args.no_npu
    )
    
    source_path = Path(args.source)
    if source_path.is_file() and source_path.suffix == '.json':
        builder.collect_from_json(args.source)
    elif source_path.is_dir():
        extensions = args.extensions.split(',')
        builder.collect_from_directory(args.source, extensions, args.max_files)
    else:
        logger.error(f"无效源: {args.source}")
        return
    
    builder.build()


if __name__ == "__main__":
    main()
