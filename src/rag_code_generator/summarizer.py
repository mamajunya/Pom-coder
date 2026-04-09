"""
代码摘要生成模块

实现功能：
1. 自动生成代码摘要
2. 提取关键信息（函数名、类名、主要功能）
3. 支持多种编程语言
"""

import re
from typing import Optional


class CodeSummarizer:
    """代码摘要生成器"""
    
    def __init__(self):
        """初始化摘要生成器"""
        pass
    
    def generate_summary(
        self,
        code: str,
        language: str = "python",
        max_length: int = 200
    ) -> str:
        """
        生成代码摘要
        
        Args:
            code: 代码内容
            language: 编程语言
            max_length: 最大摘要长度
        
        Returns:
            代码摘要
        """
        if language.lower() == "python":
            return self._summarize_python(code, max_length)
        elif language.lower() in ["javascript", "typescript"]:
            return self._summarize_javascript(code, max_length)
        elif language.lower() in ["java", "c++", "c"]:
            return self._summarize_c_like(code, max_length)
        else:
            return self._summarize_generic(code, max_length)

    def _summarize_python(self, code: str, max_length: int) -> str:
        """生成Python代码摘要"""
        elements = []
        
        # 提取类名
        classes = re.findall(r'class\s+(\w+)', code)
        if classes:
            elements.append(f"类: {', '.join(classes[:3])}")
        
        # 提取函数名
        functions = re.findall(r'def\s+(\w+)', code)
        if functions:
            elements.append(f"函数: {', '.join(functions[:5])}")
        
        # 提取文档字符串
        docstrings = re.findall(r'"""(.*?)"""', code, re.DOTALL)
        if docstrings:
            first_doc = docstrings[0].strip().split('\n')[0]
            if first_doc and len(first_doc) < 100:
                elements.insert(0, first_doc)
        
        summary = "; ".join(elements)
        return summary[:max_length] if summary else "Python代码片段"
    
    def _summarize_javascript(self, code: str, max_length: int) -> str:
        """生成JavaScript/TypeScript代码摘要"""
        elements = []
        
        # 提取类名
        classes = re.findall(r'class\s+(\w+)', code)
        if classes:
            elements.append(f"Classes: {', '.join(classes[:3])}")
        
        # 提取函数名
        functions = re.findall(r'function\s+(\w+)', code)
        const_funcs = re.findall(r'const\s+(\w+)\s*=\s*(?:async\s*)?\(', code)
        all_funcs = functions + const_funcs
        if all_funcs:
            elements.append(f"Functions: {', '.join(all_funcs[:5])}")
        
        summary = "; ".join(elements)
        return summary[:max_length] if summary else "JavaScript code snippet"
    
    def _summarize_c_like(self, code: str, max_length: int) -> str:
        """生成C/C++/Java代码摘要"""
        elements = []
        
        # 提取类名
        classes = re.findall(r'class\s+(\w+)', code)
        if classes:
            elements.append(f"Classes: {', '.join(classes[:3])}")
        
        # 提取函数名
        functions = re.findall(r'\w+\s+(\w+)\s*\([^)]*\)\s*\{', code)
        if functions:
            elements.append(f"Functions: {', '.join(functions[:5])}")
        
        summary = "; ".join(elements)
        return summary[:max_length] if summary else "Code snippet"
    
    def _summarize_generic(self, code: str, max_length: int) -> str:
        """生成通用代码摘要"""
        # 提取第一行注释
        lines = code.strip().split('\n')
        for line in lines[:5]:
            line = line.strip()
            if line.startswith('//') or line.startswith('#'):
                comment = line.lstrip('/#').strip()
                if comment:
                    return comment[:max_length]
        
        # 返回前几行代码
        preview = ' '.join(lines[:2])
        return preview[:max_length] if preview else "Code snippet"
