"""代码质量评分系统

实现多维度的代码质量评分。

支持需求11.1：实现代码质量评分系统
"""

import re
import ast
from typing import Dict, Any, List
from loguru import logger


class QualityScorer:
    """代码质量评分器
    
    从多个维度评估代码质量：
    1. 结构质量（函数/类定义、文档字符串）
    2. 代码规范（命名、缩进、长度）
    3. 可读性（注释、空行、复杂度）
    4. 健壮性（错误处理、类型提示）
    5. 现代性（Python版本特性）
    """
    
    # 权重配置
    WEIGHTS = {
        'structure': 0.25,      # 结构质量
        'style': 0.20,          # 代码规范
        'readability': 0.20,    # 可读性
        'robustness': 0.20,     # 健壮性
        'modernity': 0.15       # 现代性
    }
    
    def __init__(self):
        """初始化质量评分器"""
        logger.info("QualityScorer初始化完成")
    
    def score(self, code: str, language: str = "python") -> Dict[str, Any]:
        """
        评估代码质量
        
        Args:
            code: 代码内容
            language: 编程语言
            
        Returns:
            包含各维度分数和总分的字典
        """
        if language.lower() != "python":
            logger.warning(f"暂不支持{language}语言的质量评分")
            return {
                'total_score': 5.0,
                'language': language,
                'supported': False
            }
        
        try:
            # 计算各维度分数
            structure_score = self._score_structure(code)
            style_score = self._score_style(code)
            readability_score = self._score_readability(code)
            robustness_score = self._score_robustness(code)
            modernity_score = self._score_modernity(code)
            
            # 计算加权总分
            total_score = (
                structure_score * self.WEIGHTS['structure'] +
                style_score * self.WEIGHTS['style'] +
                readability_score * self.WEIGHTS['readability'] +
                robustness_score * self.WEIGHTS['robustness'] +
                modernity_score * self.WEIGHTS['modernity']
            )
            
            result = {
                'total_score': round(total_score, 2),
                'structure': round(structure_score, 2),
                'style': round(style_score, 2),
                'readability': round(readability_score, 2),
                'robustness': round(robustness_score, 2),
                'modernity': round(modernity_score, 2),
                'language': language,
                'supported': True
            }
            
            logger.debug(f"代码质量评分: {total_score:.2f}/10")
            
            return result
        
        except Exception as e:
            logger.error(f"质量评分失败: {str(e)}")
            return {
                'total_score': 5.0,
                'error': str(e),
                'language': language,
                'supported': True
            }
    
    def _score_structure(self, code: str) -> float:
        """
        评估结构质量
        
        检查项：
        - 函数/类定义
        - 文档字符串
        - 代码组织
        
        Args:
            code: 代码内容
            
        Returns:
            结构质量分数 [0-10]
        """
        score = 5.0  # 基础分
        
        try:
            tree = ast.parse(code)
            
            # 统计函数和类
            functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
            
            # 有函数或类定义 +1
            if functions or classes:
                score += 1.0
            
            # 检查文档字符串
            docstring_count = 0
            for node in functions + classes:
                if ast.get_docstring(node):
                    docstring_count += 1
            
            # 文档字符串覆盖率
            total_definitions = len(functions) + len(classes)
            if total_definitions > 0:
                docstring_ratio = docstring_count / total_definitions
                score += docstring_ratio * 2.0  # 最多+2分
            
            # 有类定义 +1
            if classes:
                score += 1.0
            
            # 代码不是单一表达式 +1
            if len(tree.body) > 1:
                score += 1.0
            
        except SyntaxError:
            score = 2.0  # 语法错误，低分
        except Exception:
            pass
        
        return min(score, 10.0)
    
    def _score_style(self, code: str) -> float:
        """
        评估代码规范
        
        检查项：
        - 命名规范
        - 行长度
        - 缩进一致性
        
        Args:
            code: 代码内容
            
        Returns:
            代码规范分数 [0-10]
        """
        score = 5.0  # 基础分
        
        lines = code.split('\n')
        
        # 检查行长度（PEP 8: 79字符）
        long_lines = sum(1 for line in lines if len(line) > 100)
        if long_lines == 0:
            score += 1.5
        elif long_lines < len(lines) * 0.1:  # 少于10%
            score += 0.5
        
        # 检查命名规范
        # 函数名应该是snake_case
        snake_case_pattern = r'^[a-z_][a-z0-9_]*$'
        function_names = re.findall(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)', code)
        
        if function_names:
            valid_names = sum(1 for name in function_names if re.match(snake_case_pattern, name))
            name_ratio = valid_names / len(function_names)
            score += name_ratio * 1.5  # 最多+1.5分
        
        # 检查缩进一致性（4空格）
        indented_lines = [line for line in lines if line.startswith(' ') and line.strip()]
        if indented_lines:
            four_space_indent = sum(1 for line in indented_lines 
                                   if len(line) - len(line.lstrip()) % 4 == 0)
            indent_ratio = four_space_indent / len(indented_lines)
            score += indent_ratio * 1.0  # 最多+1分
        
        # 没有过多空行
        empty_lines = sum(1 for line in lines if not line.strip())
        if empty_lines < len(lines) * 0.3:  # 空行少于30%
            score += 1.0
        
        return min(score, 10.0)
    
    def _score_readability(self, code: str) -> float:
        """
        评估可读性
        
        检查项：
        - 注释
        - 空行使用
        - 代码复杂度
        
        Args:
            code: 代码内容
            
        Returns:
            可读性分数 [0-10]
        """
        score = 5.0  # 基础分
        
        lines = code.split('\n')
        non_empty_lines = [line for line in lines if line.strip()]
        
        # 检查注释
        comment_lines = sum(1 for line in lines if line.strip().startswith('#'))
        if non_empty_lines:
            comment_ratio = comment_lines / len(non_empty_lines)
            if comment_ratio > 0.05:  # 超过5%有注释
                score += min(comment_ratio * 20, 2.0)  # 最多+2分
        
        # 检查空行（适当的空行提高可读性）
        empty_lines = sum(1 for line in lines if not line.strip())
        if non_empty_lines:
            empty_ratio = empty_lines / len(lines)
            if 0.05 < empty_ratio < 0.25:  # 5%-25%的空行
                score += 1.5
        
        # 检查行数（不要太长）
        total_lines = len(non_empty_lines)
        if total_lines < 50:
            score += 1.0
        elif total_lines < 100:
            score += 0.5
        
        # 检查平均行长度
        if non_empty_lines:
            avg_line_length = sum(len(line) for line in non_empty_lines) / len(non_empty_lines)
            if 20 < avg_line_length < 60:  # 合理的行长度
                score += 1.5
        
        return min(score, 10.0)
    
    def _score_robustness(self, code: str) -> float:
        """
        评估健壮性
        
        检查项：
        - 错误处理（try/except）
        - 类型提示
        - 输入验证
        
        Args:
            code: 代码内容
            
        Returns:
            健壮性分数 [0-10]
        """
        score = 5.0  # 基础分
        
        # 检查错误处理
        if 'try:' in code and 'except' in code:
            score += 2.0
        
        # 检查类型提示
        type_hints = re.findall(r':\s*[A-Z][a-zA-Z0-9_\[\],\s]*', code)
        if type_hints:
            score += min(len(type_hints) * 0.3, 2.0)  # 最多+2分
        
        # 检查输入验证
        validation_patterns = [
            r'if\s+.*\s+is\s+None',
            r'if\s+not\s+',
            r'assert\s+',
            r'raise\s+ValueError',
            r'raise\s+TypeError'
        ]
        
        validation_count = sum(1 for pattern in validation_patterns 
                              if re.search(pattern, code))
        if validation_count > 0:
            score += min(validation_count * 0.5, 1.5)  # 最多+1.5分
        
        # 有日志记录
        if 'logger.' in code or 'logging.' in code or 'print(' in code:
            score += 0.5
        
        return min(score, 10.0)
    
    def _score_modernity(self, code: str) -> float:
        """
        评估现代性
        
        检查项：
        - Python 3特性（f-string, type hints等）
        - 现代库使用
        - 推导式
        
        Args:
            code: 代码内容
            
        Returns:
            现代性分数 [0-10]
        """
        score = 5.0  # 基础分
        
        # f-string
        if "f'" in code or 'f"' in code:
            score += 1.5
        
        # 类型提示
        if '->' in code or ': ' in code:
            score += 1.5
        
        # 推导式
        comprehensions = [
            r'\[.*for.*in.*\]',  # 列表推导
            r'\{.*for.*in.*\}',  # 集合/字典推导
            r'\(.*for.*in.*\)',  # 生成器表达式
        ]
        for pattern in comprehensions:
            if re.search(pattern, code):
                score += 0.5
        
        # 上下文管理器
        if 'with ' in code:
            score += 1.0
        
        # 装饰器
        if '@' in code:
            score += 0.5
        
        # dataclass
        if '@dataclass' in code:
            score += 0.5
        
        # 异步特性
        if 'async ' in code or 'await ' in code:
            score += 0.5
        
        return min(score, 10.0)
    
    def get_recommendations(self, score_result: Dict[str, Any]) -> List[str]:
        """
        根据评分结果生成改进建议
        
        Args:
            score_result: 评分结果
            
        Returns:
            建议列表
        """
        recommendations = []
        
        if not score_result.get('supported', True):
            return ["暂不支持该语言的质量评分"]
        
        # 结构质量建议
        if score_result.get('structure', 5.0) < 6.0:
            recommendations.append("建议添加函数和类定义，提高代码结构化程度")
            recommendations.append("为函数和类添加文档字符串")
        
        # 代码规范建议
        if score_result.get('style', 5.0) < 6.0:
            recommendations.append("遵循PEP 8代码规范，使用snake_case命名")
            recommendations.append("控制行长度在100字符以内")
        
        # 可读性建议
        if score_result.get('readability', 5.0) < 6.0:
            recommendations.append("添加适当的注释说明复杂逻辑")
            recommendations.append("使用空行分隔逻辑块")
        
        # 健壮性建议
        if score_result.get('robustness', 5.0) < 6.0:
            recommendations.append("添加错误处理（try/except）")
            recommendations.append("添加类型提示提高代码可靠性")
            recommendations.append("添加输入验证")
        
        # 现代性建议
        if score_result.get('modernity', 5.0) < 6.0:
            recommendations.append("使用f-string代替字符串格式化")
            recommendations.append("使用类型提示")
            recommendations.append("考虑使用推导式简化代码")
        
        return recommendations if recommendations else ["代码质量良好，继续保持！"]
