"""Prompt构造模块

实现Prompt模板管理和构造逻辑。

支持需求：
- 4.1: 构造包含系统指令、参考代码和用户问题的完整Prompt
- 4.2: 确保构造的Prompt总token数不超过配置的最大值
- 4.3: 检索结果为空时仍然返回有效Prompt
- 4.4: 代码片段总token数超过预算时按分数优先级选择
"""

from typing import List, Optional
from loguru import logger

from .models import CodeSnippet, RetrievalResult


class PromptConstructor:
    """Prompt构造器
    
    负责将检索结果和用户查询组装成高质量的Prompt。
    """
    
    # 默认系统指令模板
    DEFAULT_SYSTEM_PROMPT = """You are a professional programmer. Your task is to generate high-quality, production-ready code based on user requirements. Guidelines:
1. Write clean, readable, and well-commented code
2. Follow best practices and coding standards
3. Include necessary error handling
4. Add helpful comments where appropriate
5. Ensure the code is efficient and maintainable
6. Fully adhere to user requirements

If reference code is provided below, it can be used as inspiration, but it should be adjusted according to the specific requirements."""
    
    # 参考代码部分模板
    REFERENCE_TEMPLATE = """

## Reference Code Examples

The following code snippets may be helpful:

{references}
"""
    
    # 单个代码片段模板
    SNIPPET_TEMPLATE = """
### Example {index}: {summary}
**Source:** {path}
**Quality Score:** {quality_score}/10
**Language:** {language}

```{language}
{imports}

{code}
```
"""
    
    # 用户问题模板
    USER_TEMPLATE = """

## User Request

{query}

## Your Response

Please provide the code implementation:
"""
    
    def __init__(
        self,
        max_tokens: int = 2000,
        system_prompt: Optional[str] = None,
        tokens_per_char: float = 0.25  # 粗略估计：1个token约4个字符
    ):
        """
        初始化Prompt构造器
        
        Args:
            max_tokens: 最大token限制
            system_prompt: 自定义系统指令（可选）
            tokens_per_char: token与字符的转换比例
        """
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT
        self.tokens_per_char = tokens_per_char
        
        logger.info(f"PromptConstructor初始化完成，max_tokens={max_tokens}")
    
    def construct(
        self,
        query: str,
        retrieved_snippets: List[RetrievalResult],
        max_snippets: Optional[int] = None
    ) -> str:
        """
        构造完整Prompt
        
        支持需求：
        - 4.1: 构造包含系统指令、参考代码和用户问题的完整Prompt
        - 4.2: 确保总token数不超过max_tokens
        - 4.3: 检索结果为空时仍返回有效Prompt
        - 4.4: 超过预算时按分数优先级选择代码片段
        
        Args:
            query: 用户原始问题
            retrieved_snippets: 检索到的代码片段列表
            max_snippets: 最大代码片段数量（可选）
            
        Returns:
            完整的Prompt字符串
        """
        if not query or len(query.strip()) == 0:
            raise ValueError("Query不能为空")
        
        # 计算固定部分的token数
        system_tokens = self.count_tokens(self.system_prompt)
        user_part = self.USER_TEMPLATE.format(query=query)
        user_tokens = self.count_tokens(user_part)
        
        fixed_tokens = system_tokens + user_tokens
        
        # 计算可用于参考代码的token预算
        available_tokens = self.max_tokens - fixed_tokens
        
        logger.info(
            f"Token预算: 总计={self.max_tokens}, "
            f"系统指令={system_tokens}, 用户问题={user_tokens}, "
            f"可用于参考代码={available_tokens}"
        )
        
        # 如果没有检索结果，返回仅包含系统指令和用户问题的Prompt
        if not retrieved_snippets or available_tokens <= 0:
            logger.warning("无检索结果或token预算不足，返回基础Prompt")
            return self.system_prompt + user_part
        
        # 按分数排序（确保高分片段优先）
        sorted_snippets = sorted(
            retrieved_snippets,
            key=lambda x: x.score,
            reverse=True
        )
        
        # 限制最大片段数
        if max_snippets:
            sorted_snippets = sorted_snippets[:max_snippets]
        
        # 选择代码片段，确保不超过token预算
        selected_snippets = self._select_snippets_within_budget(
            sorted_snippets,
            available_tokens
        )
        
        # 格式化参考代码部分
        if selected_snippets:
            references = self._format_references(selected_snippets)
            reference_part = self.REFERENCE_TEMPLATE.format(references=references)
        else:
            logger.warning("所有代码片段都超过token预算，返回基础Prompt")
            reference_part = ""
        
        # 组装完整Prompt
        full_prompt = self.system_prompt + reference_part + user_part
        
        # 验证最终token数
        final_tokens = self.count_tokens(full_prompt)
        logger.info(
            f"Prompt构造完成: 总token={final_tokens}, "
            f"包含 {len(selected_snippets)} 个代码片段"
        )
        
        if final_tokens > self.max_tokens:
            logger.warning(
                f"Prompt超过token限制: {final_tokens} > {self.max_tokens}"
            )
        
        return full_prompt
    
    def _select_snippets_within_budget(
        self,
        snippets: List[RetrievalResult],
        token_budget: int
    ) -> List[RetrievalResult]:
        """
        在token预算内选择代码片段
        
        支持需求4.4：按分数优先级选择代码片段直到达到token预算上限
        
        Args:
            snippets: 排序后的代码片段列表
            token_budget: 可用token预算
            
        Returns:
            选中的代码片段列表
        """
        selected = []
        used_tokens = 0
        
        for snippet in snippets:
            # 格式化单个片段以计算其token数
            formatted = self._format_single_snippet(
                snippet.snippet,
                len(selected) + 1
            )
            snippet_tokens = self.count_tokens(formatted)
            
            # 检查是否超过预算
            if used_tokens + snippet_tokens <= token_budget:
                selected.append(snippet)
                used_tokens += snippet_tokens
                logger.debug(
                    f"选择片段 {len(selected)}: {snippet.snippet.path}, "
                    f"tokens={snippet_tokens}, 累计={used_tokens}/{token_budget}"
                )
            else:
                logger.debug(
                    f"跳过片段 {snippet.snippet.path}: "
                    f"会超过预算 ({used_tokens + snippet_tokens} > {token_budget})"
                )
        
        return selected
    
    def _format_references(self, snippets: List[RetrievalResult]) -> str:
        """
        格式化所有参考代码片段
        
        Args:
            snippets: 代码片段列表
            
        Returns:
            格式化后的参考代码字符串
        """
        formatted_snippets = []
        
        for index, result in enumerate(snippets, start=1):
            formatted = self._format_single_snippet(result.snippet, index)
            formatted_snippets.append(formatted)
        
        return "\n".join(formatted_snippets)
    
    def _format_single_snippet(
        self,
        snippet: CodeSnippet,
        index: int
    ) -> str:
        """
        格式化单个代码片段
        
        Args:
            snippet: 代码片段
            index: 片段序号
            
        Returns:
            格式化后的字符串
        """
        return self.SNIPPET_TEMPLATE.format(
            index=index,
            summary=snippet.summary,
            path=snippet.path,
            quality_score=snippet.quality_score,
            language=snippet.language,
            imports=snippet.imports if snippet.imports else "# No imports",
            code=snippet.code
        )
    
    def count_tokens(self, text: str) -> int:
        """
        计算文本的token数量
        
        使用简单的字符数估算。实际应用中应该使用tokenizer。
        
        Args:
            text: 输入文本
            
        Returns:
            估算的token数量
        """
        # 简单估算：1个token约等于4个字符
        # 实际应该使用：len(tokenizer.encode(text))
        estimated_tokens = int(len(text) * self.tokens_per_char)
        return estimated_tokens
    
    def set_system_prompt(self, prompt: str) -> None:
        """
        设置自定义系统指令
        
        Args:
            prompt: 系统指令文本
        """
        self.system_prompt = prompt
        logger.info("系统指令已更新")
    
    def get_token_budget_info(self, query: str) -> dict:
        """
        获取token预算信息
        
        Args:
            query: 用户查询
            
        Returns:
            包含预算信息的字典
        """
        system_tokens = self.count_tokens(self.system_prompt)
        user_part = self.USER_TEMPLATE.format(query=query)
        user_tokens = self.count_tokens(user_part)
        available_tokens = self.max_tokens - system_tokens - user_tokens
        
        return {
            'max_tokens': self.max_tokens,
            'system_tokens': system_tokens,
            'user_tokens': user_tokens,
            'available_for_references': available_tokens,
            'percentage_for_references': (available_tokens / self.max_tokens * 100)
        }
