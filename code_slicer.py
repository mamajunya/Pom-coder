"""
智能代码切片工具

功能：
1. 自动分析代码文件
2. 提取函数、类、方法
3. 生成描述和元数据
4. 输出为JSON格式
"""

import ast
import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from loguru import logger
from dataclasses import dataclass, asdict


@dataclass
class CodeSlice:
    """代码片段"""
    code: str
    path: str
    language: str
    name: str
    type: str  # function, class, method
    description: str
    start_line: int
    end_line: int
    complexity: int = 0
    metadata: Dict[str, Any] = None
    
    def to_dict(self):
        """转换为字典"""
        data = asdict(self)
        if data['metadata'] is None:
            data['metadata'] = {}
        return data


class PythonSlicer:
    """Python代码切片器"""
    
    def __init__(self):
        self.slices: List[CodeSlice] = []
    
    def slice_file(self, file_path: Path) -> List[CodeSlice]:
        """切片单个Python文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            tree = ast.parse(content)
            slices = []
            
            for node in ast.walk(tree):
                # 提取函数
                if isinstance(node, ast.FunctionDef):
                    slice_obj = self._extract_function(node, lines, file_path)
                    if slice_obj:
                        slices.append(slice_obj)
                
                # 提取类
                elif isinstance(node, ast.ClassDef):
                    slice_obj = self._extract_class(node, lines, file_path)
                    if slice_obj:
                        slices.append(slice_obj)
            
            return slices
        
        except Exception as e:
            logger.warning(f"切片文件失败 {file_path}: {str(e)}")
            return []
    
    def _extract_function(self, node: ast.FunctionDef, lines: List[str], file_path: Path) -> Optional[CodeSlice]:
        """提取函数"""
        try:
            start_line = node.lineno - 1
            end_line = node.end_lineno
            
            # 提取代码
            code = '\n'.join(lines[start_line:end_line])
            
            # 跳过太短的函数
            if len(code) < 20:
                return None
            
            # 提取文档字符串
            docstring = ast.get_docstring(node) or ""
            
            # 生成描述
            description = self._generate_description(node.name, docstring, "function")
            
            # 计算复杂度
            complexity = self._calculate_complexity(node)
            
            # 提取参数
            args = [arg.arg for arg in node.args.args]
            
            return CodeSlice(
                code=code,
                path=str(file_path),
                language="python",
                name=node.name,
                type="function",
                description=description,
                start_line=start_line + 1,
                end_line=end_line,
                complexity=complexity,
                metadata={
                    "args": args,
                    "docstring": docstring,
                    "is_async": isinstance(node, ast.AsyncFunctionDef)
                }
            )
        
        except Exception as e:
            logger.debug(f"提取函数失败: {str(e)}")
            return None
    
    def _extract_class(self, node: ast.ClassDef, lines: List[str], file_path: Path) -> Optional[CodeSlice]:
        """提取类"""
        try:
            start_line = node.lineno - 1
            end_line = node.end_lineno
            
            # 提取代码
            code = '\n'.join(lines[start_line:end_line])
            
            # 跳过太短的类
            if len(code) < 30:
                return None
            
            # 提取文档字符串
            docstring = ast.get_docstring(node) or ""
            
            # 生成描述
            description = self._generate_description(node.name, docstring, "class")
            
            # 提取方法
            methods = [m.name for m in node.body if isinstance(m, ast.FunctionDef)]
            
            # 提取基类
            bases = [self._get_name(base) for base in node.bases]
            
            return CodeSlice(
                code=code,
                path=str(file_path),
                language="python",
                name=node.name,
                type="class",
                description=description,
                start_line=start_line + 1,
                end_line=end_line,
                complexity=len(methods),
                metadata={
                    "methods": methods,
                    "bases": bases,
                    "docstring": docstring
                }
            )
        
        except Exception as e:
            logger.debug(f"提取类失败: {str(e)}")
            return None
    
    def _generate_description(self, name: str, docstring: str, type_: str) -> str:
        """生成描述"""
        if docstring:
            # 使用文档字符串的第一行
            first_line = docstring.split('\n')[0].strip()
            return f"{name} - {first_line}"
        else:
            # 根据名称生成描述
            return f"{type_} {name}"
    
    def _calculate_complexity(self, node: ast.AST) -> int:
        """计算圈复杂度"""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity
    
    def _get_name(self, node: ast.AST) -> str:
        """获取节点名称"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        else:
            return "Unknown"


class JavaScriptSlicer:
    """JavaScript代码切片器（简化版）"""
    
    def slice_file(self, file_path: Path) -> List[CodeSlice]:
        """切片JavaScript文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            slices = []
            
            # 简单的正则匹配（可以改进为使用JS解析器）
            import re
            
            # 匹配函数定义
            func_pattern = r'function\s+(\w+)\s*\([^)]*\)\s*\{'
            for match in re.finditer(func_pattern, content):
                name = match.group(1)
                start = content[:match.start()].count('\n')
                
                # 找到函数结束
                brace_count = 1
                pos = match.end()
                while pos < len(content) and brace_count > 0:
                    if content[pos] == '{':
                        brace_count += 1
                    elif content[pos] == '}':
                        brace_count -= 1
                    pos += 1
                
                end = content[:pos].count('\n')
                code = '\n'.join(lines[start:end+1])
                
                if len(code) > 20:
                    slices.append(CodeSlice(
                        code=code,
                        path=str(file_path),
                        language="javascript",
                        name=name,
                        type="function",
                        description=f"JavaScript function {name}",
                        start_line=start + 1,
                        end_line=end + 1,
                        metadata={}
                    ))
            
            return slices
        
        except Exception as e:
            logger.warning(f"切片JS文件失败 {file_path}: {str(e)}")
            return []


class CodeSlicerTool:
    """代码切片工具"""
    
    def __init__(self):
        self.python_slicer = PythonSlicer()
        self.js_slicer = JavaScriptSlicer()
        self.slices: List[CodeSlice] = []
    
    def slice_directory(
        self,
        directory: str,
        extensions: List[str] = [".py", ".js"],
        max_files: int = 1000,
        min_code_length: int = 50,
        max_code_length: int = 5000
    ) -> List[CodeSlice]:
        """切片整个目录"""
        logger.info(f"开始切片目录: {directory}")
        
        directory = Path(directory)
        slices = []
        file_count = 0
        
        for ext in extensions:
            for file_path in directory.rglob(f"*{ext}"):
                if file_count >= max_files:
                    break
                
                # 跳过特定目录
                if any(skip in str(file_path) for skip in [
                    'node_modules', '__pycache__', '.git', 'venv', 'env',
                    'dist', 'build', '.pytest_cache'
                ]):
                    continue
                
                # 根据扩展名选择切片器
                if ext == '.py':
                    file_slices = self.python_slicer.slice_file(file_path)
                elif ext == '.js':
                    file_slices = self.js_slicer.slice_file(file_path)
                else:
                    continue
                
                # 过滤切片
                for slice_obj in file_slices:
                    if min_code_length <= len(slice_obj.code) <= max_code_length:
                        slices.append(slice_obj)
                
                file_count += 1
        
        logger.info(f"✓ 切片完成: {len(slices)} 个代码片段，来自 {file_count} 个文件")
        self.slices = slices
        return slices
    
    def save_to_json(self, output_file: str):
        """保存为JSON"""
        logger.info(f"保存到JSON: {output_file}")
        
        data = [slice_obj.to_dict() for slice_obj in self.slices]
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✓ 已保存 {len(data)} 个代码片段")
    
    def generate_statistics(self) -> Dict[str, Any]:
        """生成统计信息"""
        stats = {
            'total': len(self.slices),
            'by_type': {},
            'by_language': {},
            'avg_complexity': 0,
            'avg_length': 0
        }
        
        for slice_obj in self.slices:
            # 按类型统计
            stats['by_type'][slice_obj.type] = stats['by_type'].get(slice_obj.type, 0) + 1
            
            # 按语言统计
            stats['by_language'][slice_obj.language] = stats['by_language'].get(slice_obj.language, 0) + 1
        
        # 计算平均值
        if self.slices:
            stats['avg_complexity'] = sum(s.complexity for s in self.slices) / len(self.slices)
            stats['avg_length'] = sum(len(s.code) for s in self.slices) / len(self.slices)
        
        return stats
    
    def print_statistics(self):
        """打印统计信息"""
        stats = self.generate_statistics()
        
        logger.info("=" * 60)
        logger.info("代码切片统计")
        logger.info("=" * 60)
        logger.info(f"总片段数: {stats['total']}")
        logger.info(f"\n按类型:")
        for type_, count in stats['by_type'].items():
            logger.info(f"  {type_}: {count}")
        logger.info(f"\n按语言:")
        for lang, count in stats['by_language'].items():
            logger.info(f"  {lang}: {count}")
        logger.info(f"\n平均复杂度: {stats['avg_complexity']:.2f}")
        logger.info(f"平均长度: {stats['avg_length']:.0f} 字符")
        logger.info("=" * 60)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="智能代码切片工具")
    parser.add_argument("--source", required=True, help="源代码目录")
    parser.add_argument("--output", default="code_slices.json", help="输出JSON文件")
    parser.add_argument("--extensions", default=".py,.js", help="文件扩展名（逗号分隔）")
    parser.add_argument("--max-files", type=int, default=1000, help="最大文件数")
    parser.add_argument("--min-length", type=int, default=50, help="最小代码长度")
    parser.add_argument("--max-length", type=int, default=5000, help="最大代码长度")
    
    args = parser.parse_args()
    
    # 创建切片器
    slicer = CodeSlicerTool()
    
    # 切片目录
    extensions = args.extensions.split(',')
    slices = slicer.slice_directory(
        directory=args.source,
        extensions=extensions,
        max_files=args.max_files,
        min_code_length=args.min_length,
        max_code_length=args.max_length
    )
    
    if not slices:
        logger.error("没有找到代码片段")
        return
    
    # 保存结果
    slicer.save_to_json(args.output)
    
    # 打印统计
    slicer.print_statistics()
    
    logger.info(f"\n下一步:")
    logger.info(f"  python build_knowledge_base_npu.py --source {args.output}")


if __name__ == "__main__":
    main()
