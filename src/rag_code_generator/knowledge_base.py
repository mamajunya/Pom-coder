"""知识库管理模块

实现代码知识库的存储、索引和管理。

支持需求：
- 11.1: 添加新代码片段时验证质量分数不低于5.0
- 11.2: 添加新代码片段时验证GitHub stars不低于100
- 11.3: 自动生成向量表示
- 11.4: 自动生成代码摘要
- 11.5: 同时更新FAISS向量索引和BM25关键词索引
"""

import json
import sqlite3
from pathlib import Path
from typing import List, Optional, Dict, Any
from loguru import logger

from .models import CodeSnippet


class KnowledgeBaseError(Exception):
    """知识库错误异常"""
    pass


class QualityValidator:
    """代码质量验证器"""
    
    MIN_QUALITY_SCORE = 5.0
    MIN_STARS = 100
    
    @staticmethod
    def validate_snippet(snippet: CodeSnippet) -> tuple[bool, str]:
        """
        验证代码片段质量
        
        支持需求11.1和11.2：验证质量分数和stars
        
        Args:
            snippet: 代码片段
            
        Returns:
            (是否通过, 错误信息)
        """
        # 验证质量分数
        if snippet.quality_score < QualityValidator.MIN_QUALITY_SCORE:
            return False, (
                f"质量分数过低: {snippet.quality_score} < "
                f"{QualityValidator.MIN_QUALITY_SCORE}"
            )
        
        # 验证stars
        if snippet.stars < QualityValidator.MIN_STARS:
            return False, (
                f"GitHub stars过低: {snippet.stars} < "
                f"{QualityValidator.MIN_STARS}"
            )
        
        # 验证代码非空
        if not snippet.code or len(snippet.code.strip()) == 0:
            return False, "代码内容为空"
        
        # 验证摘要非空
        if not snippet.summary or len(snippet.summary.strip()) == 0:
            return False, "代码摘要为空"
        
        return True, ""


class CodeKnowledgeBase:
    """代码知识库
    
    管理代码片段的存储、索引和检索。
    """
    
    def __init__(
        self,
        db_path: str,
        faiss_index_path: Optional[str] = None,
        bm25_index_path: Optional[str] = None,
        auto_commit: bool = True
    ):
        """
        初始化代码知识库
        
        Args:
            db_path: SQLite数据库路径
            faiss_index_path: FAISS索引路径
            bm25_index_path: BM25索引路径
            auto_commit: 是否自动提交
        """
        self.db_path = Path(db_path)
        self.faiss_index_path = Path(faiss_index_path) if faiss_index_path else None
        self.bm25_index_path = Path(bm25_index_path) if bm25_index_path else None
        self.auto_commit = auto_commit
        
        # 创建数据库连接
        self._init_database()
        
        logger.info(f"CodeKnowledgeBase初始化: {self.db_path}")
    
    def _init_database(self) -> None:
        """初始化数据库表"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # 创建代码片段表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS code_snippets (
                snippet_id TEXT PRIMARY KEY,
                code TEXT NOT NULL,
                summary TEXT NOT NULL,
                imports TEXT,
                path TEXT NOT NULL,
                language TEXT NOT NULL,
                tags TEXT,
                quality_score REAL NOT NULL,
                stars INTEGER NOT NULL,
                last_update TEXT NOT NULL,
                lines_of_code INTEGER DEFAULT 0,
                complexity REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_quality_score 
            ON code_snippets(quality_score)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_stars 
            ON code_snippets(stars)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_language 
            ON code_snippets(language)
        """)
        
        conn.commit()
        conn.close()
        
        logger.info("数据库表初始化完成")
    
    def add_snippet(
        self,
        snippet: CodeSnippet,
        skip_validation: bool = False
    ) -> bool:
        """
        添加代码片段
        
        支持需求：
        - 11.1: 验证质量分数不低于5.0
        - 11.2: 验证GitHub stars不低于100
        - 11.3: 自动生成向量表示（TODO）
        - 11.4: 自动生成代码摘要（TODO）
        - 11.5: 更新索引
        
        Args:
            snippet: 代码片段
            skip_validation: 是否跳过验证
            
        Returns:
            是否成功
            
        Raises:
            KnowledgeBaseError: 验证失败或添加失败
        """
        # 验证质量（支持需求11.1和11.2）
        if not skip_validation:
            valid, error_msg = QualityValidator.validate_snippet(snippet)
            if not valid:
                raise KnowledgeBaseError(f"代码片段验证失败: {error_msg}")
        
        # 生成snippet_id（如果没有）
        if not snippet.snippet_id:
            import hashlib
            snippet.snippet_id = hashlib.md5(
                f"{snippet.path}{snippet.code}".encode()
            ).hexdigest()
        
        # TODO: 生成向量表示（支持需求11.3）
        # if not snippet.embedding:
        #     snippet.embedding = self._generate_embedding(snippet.code)
        
        # TODO: 生成代码摘要（支持需求11.4）
        # if not snippet.summary:
        #     snippet.summary = self._generate_summary(snippet.code)
        
        # 计算代码行数
        if snippet.lines_of_code == 0:
            snippet.lines_of_code = len(snippet.code.split('\n'))
        
        # 存储到数据库
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO code_snippets (
                    snippet_id, code, summary, imports, path, language,
                    tags, quality_score, stars, last_update,
                    lines_of_code, complexity, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                snippet.snippet_id,
                snippet.code,
                snippet.summary,
                snippet.imports,
                snippet.path,
                snippet.language,
                json.dumps(snippet.tags),
                snippet.quality_score,
                snippet.stars,
                snippet.last_update,
                snippet.lines_of_code,
                snippet.complexity
            ))
            
            if self.auto_commit:
                conn.commit()
            
            conn.close()
            
            logger.info(
                f"代码片段已添加: {snippet.snippet_id} "
                f"(质量={snippet.quality_score}, stars={snippet.stars})"
            )
            
            # TODO: 更新索引（支持需求11.5）
            # self._update_faiss_index(snippet)
            # self._update_bm25_index(snippet)
            
            return True
        
        except Exception as e:
            logger.error(f"添加代码片段失败: {str(e)}")
            raise KnowledgeBaseError(f"添加代码片段失败: {str(e)}")
    
    def get_snippet(self, snippet_id: str) -> Optional[CodeSnippet]:
        """
        获取代码片段
        
        Args:
            snippet_id: 片段ID
            
        Returns:
            代码片段，如果不存在则返回None
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM code_snippets WHERE snippet_id = ?
            """, (snippet_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row is None:
                return None
            
            # 转换为CodeSnippet对象
            snippet = CodeSnippet(
                code=row['code'],
                summary=row['summary'],
                imports=row['imports'] or '',
                path=row['path'],
                language=row['language'],
                tags=json.loads(row['tags']) if row['tags'] else [],
                quality_score=row['quality_score'],
                stars=row['stars'],
                last_update=row['last_update'],
                snippet_id=row['snippet_id'],
                lines_of_code=row['lines_of_code'],
                complexity=row['complexity']
            )
            
            return snippet
        
        except Exception as e:
            logger.error(f"获取代码片段失败: {str(e)}")
            return None
    
    def search_snippets(
        self,
        language: Optional[str] = None,
        min_quality: Optional[float] = None,
        min_stars: Optional[int] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[CodeSnippet]:
        """
        搜索代码片段
        
        Args:
            language: 编程语言
            min_quality: 最小质量分数
            min_stars: 最小stars
            tags: 标签列表
            limit: 返回数量限制
            
        Returns:
            代码片段列表
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 构建查询
            conditions = []
            params = []
            
            if language:
                conditions.append("language = ?")
                params.append(language)
            
            if min_quality is not None:
                conditions.append("quality_score >= ?")
                params.append(min_quality)
            
            if min_stars is not None:
                conditions.append("stars >= ?")
                params.append(min_stars)
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            query = f"""
                SELECT * FROM code_snippets
                WHERE {where_clause}
                ORDER BY quality_score DESC, stars DESC
                LIMIT ?
            """
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            # 转换为CodeSnippet对象
            snippets = []
            for row in rows:
                snippet = CodeSnippet(
                    code=row['code'],
                    summary=row['summary'],
                    imports=row['imports'] or '',
                    path=row['path'],
                    language=row['language'],
                    tags=json.loads(row['tags']) if row['tags'] else [],
                    quality_score=row['quality_score'],
                    stars=row['stars'],
                    last_update=row['last_update'],
                    snippet_id=row['snippet_id'],
                    lines_of_code=row['lines_of_code'],
                    complexity=row['complexity']
                )
                
                # 过滤标签
                if tags:
                    if any(tag in snippet.tags for tag in tags):
                        snippets.append(snippet)
                else:
                    snippets.append(snippet)
            
            return snippets[:limit]
        
        except Exception as e:
            logger.error(f"搜索代码片段失败: {str(e)}")
            return []
    
    def update_quality_score(
        self,
        snippet_id: str,
        score: float
    ) -> bool:
        """
        更新质量分数
        
        Args:
            snippet_id: 片段ID
            score: 新的质量分数
            
        Returns:
            是否成功
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE code_snippets
                SET quality_score = ?, updated_at = CURRENT_TIMESTAMP
                WHERE snippet_id = ?
            """, (score, snippet_id))
            
            if self.auto_commit:
                conn.commit()
            
            affected = cursor.rowcount
            conn.close()
            
            if affected > 0:
                logger.info(f"质量分数已更新: {snippet_id} -> {score}")
                return True
            else:
                logger.warning(f"代码片段不存在: {snippet_id}")
                return False
        
        except Exception as e:
            logger.error(f"更新质量分数失败: {str(e)}")
            return False
    
    def delete_snippet(self, snippet_id: str) -> bool:
        """
        删除代码片段
        
        Args:
            snippet_id: 片段ID
            
        Returns:
            是否成功
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM code_snippets WHERE snippet_id = ?
            """, (snippet_id,))
            
            if self.auto_commit:
                conn.commit()
            
            affected = cursor.rowcount
            conn.close()
            
            if affected > 0:
                logger.info(f"代码片段已删除: {snippet_id}")
                # TODO: 从索引中删除
                return True
            else:
                logger.warning(f"代码片段不存在: {snippet_id}")
                return False
        
        except Exception as e:
            logger.error(f"删除代码片段失败: {str(e)}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取知识库统计信息
        
        Returns:
            统计信息字典
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # 总数
            cursor.execute("SELECT COUNT(*) FROM code_snippets")
            total_count = cursor.fetchone()[0]
            
            # 按语言统计
            cursor.execute("""
                SELECT language, COUNT(*) as count
                FROM code_snippets
                GROUP BY language
                ORDER BY count DESC
            """)
            by_language = dict(cursor.fetchall())
            
            # 平均质量分数
            cursor.execute("SELECT AVG(quality_score) FROM code_snippets")
            avg_quality = cursor.fetchone()[0] or 0
            
            # 平均stars
            cursor.execute("SELECT AVG(stars) FROM code_snippets")
            avg_stars = cursor.fetchone()[0] or 0
            
            conn.close()
            
            return {
                'total_snippets': total_count,
                'by_language': by_language,
                'avg_quality_score': round(avg_quality, 2),
                'avg_stars': round(avg_stars, 0)
            }
        
        except Exception as e:
            logger.error(f"获取统计信息失败: {str(e)}")
            return {}
    
    def close(self) -> None:
        """关闭知识库"""
        logger.info("知识库已关闭")
