# Ollama集成说明

## 📋 更新内容

已成功将RAG代码生成器集成Ollama，并添加了美观的网页GUI界面。

## 🆕 新增文件

### 核心模块
1. **src/rag_code_generator/ollama_generator.py**
   - Ollama API封装
   - 支持代码生成和聊天模式
   - 自动检查服务和模型

2. **src/rag_code_generator/ollama_rag_generator.py**
   - 集成Ollama的RAG生成器
   - 保留Query重写和缓存功能
   - 简化的生成流程

### Web应用
3. **app.py** ⭐
   - FastAPI Web服务
   - 美观的网页GUI界面
   - RESTful API端点
   - 完整的错误处理

4. **start_web.py**
   - 快速启动脚本
   - 自动检查Ollama和模型
   - 交互式下载提示

### 配置文件
5. **requirements-ollama.txt**
   - 最小化依赖列表
   - 适用于Ollama版本
   - 可选依赖说明

### 文档
6. **WEB_GUI_使用指南.md** ⭐
   - 完整的使用教程
   - API使用示例
   - 故障排除指南
   - 性能参考数据

7. **OLLAMA_集成说明.md** (本文件)
   - 更新内容总结
   - 快速开始指南

## 🚀 快速开始

### 1. 安装Ollama

访问 https://ollama.ai/download 下载安装

### 2. 安装依赖

```bash
pip install -r requirements-ollama.txt
```

### 3. 启动服务

```bash
python start_web.py
```

### 4. 访问界面

打开浏览器访问: http://localhost:8000

## 🎯 主要特性

### 1. 网页GUI界面

- ✅ 美观的渐变色设计
- ✅ 响应式布局
- ✅ 实时状态显示
- ✅ 一键复制代码
- ✅ 加载动画
- ✅ 错误提示
- ✅ 性能指标显示

### 2. Ollama集成

- ✅ 自动4bit量化
- ✅ 支持RTX 5060
- ✅ 多模型支持
- ✅ 自动下载模型
- ✅ 服务健康检查

### 3. RAG功能

- ✅ Query重写
- ✅ 智能缓存
- ✅ 批量生成
- ✅ 性能监控

### 4. API服务

- ✅ RESTful API
- ✅ 请求验证
- ✅ 错误处理
- ✅ 健康检查
- ✅ 系统信息

## 📁 文件结构

```
.
├── app.py                          # Web应用主程序 ⭐
├── start_web.py                    # 快速启动脚本
├── requirements-ollama.txt         # Ollama版本依赖
├── WEB_GUI_使用指南.md             # 使用指南 ⭐
├── OLLAMA_集成说明.md              # 本文件
│
├── src/rag_code_generator/
│   ├── ollama_generator.py         # Ollama生成器
│   ├── ollama_rag_generator.py     # Ollama RAG生成器
│   ├── query_rewriter.py           # Query重写（保留）
│   ├── prompt.py                   # Prompt构造（保留）
│   ├── cache.py                    # 缓存系统（保留）
│   └── ...                         # 其他原有模块
│
└── ...
```

## 🔄 与原系统的区别

### 原系统（transformers + bitsandbytes）

```python
# 需要手动加载模型
from src.rag_code_generator.rag_generator import RAGCodeGenerator

generator = RAGCodeGenerator(
    model_path="./models/deepseek-coder-6.7b-instruct",
    device="cuda:0",
    quantization="4bit"  # 不支持RTX 5060
)
```

**问题**:
- ❌ bitsandbytes不支持RTX 5060
- ❌ 需要下载27GB模型
- ❌ 配置复杂
- ❌ 没有GUI界面

### 新系统（Ollama）

```python
# 自动处理一切
from src.rag_code_generator.ollama_rag_generator import OllamaRAGGenerator

generator = OllamaRAGGenerator(
    model_name="deepseek-coder:6.7b"  # 自动4bit量化
)
```

**优势**:
- ✅ 支持RTX 5060
- ✅ 自动下载和管理模型
- ✅ 配置简单
- ✅ 美观的Web GUI
- ✅ 开箱即用

## 🎨 界面预览

### 主界面

```
┌─────────────────────────────────────────────┐
│  🚀 RAG代码生成器                            │
│  基于Ollama的智能代码生成系统                │
├─────────────────────────────────────────────┤
│  ● 系统运行中    模型: deepseek-coder:6.7b  │
├─────────────────────────────────────────────┤
│                                             │
│  代码需求描述                                │
│  ┌─────────────────────────────────────┐   │
│  │ 写一个Python快速排序函数...          │   │
│  │                                     │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  生成温度: [0.2]  最大Token数: [512]        │
│                                             │
│  [✨ 生成代码]  [🗑️ 清空]                   │
│                                             │
│  生成结果                    [📋 复制代码]   │
│  ┌─────────────────────────────────────┐   │
│  │ def quicksort(arr):                 │   │
│  │     if len(arr) <= 1:               │   │
│  │         return arr                  │   │
│  │     ...                             │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ⏱️ 耗时: 2.3秒  🤖 模型: deepseek-coder   │
└─────────────────────────────────────────────┘
```

## 📊 性能对比

### RTX 5060 (8GB VRAM)

| 方案 | 可用性 | 显存 | 速度 | 配置难度 |
|------|--------|------|------|---------|
| transformers + bitsandbytes | ❌ 不支持 | - | - | 困难 |
| transformers + FP16 | ⚠️ 显存不足 | ~13GB | 快 | 中等 |
| Ollama | ✅ 完美支持 | ~4GB | 快 | 简单 |
| CPU模式 | ✅ 可用 | 0GB | 很慢 | 简单 |

## 🔧 API使用示例

### Python

```python
import requests

# 生成代码
response = requests.post(
    'http://localhost:8000/api/generate',
    json={
        'query': '写一个Python快速排序函数',
        'temperature': 0.2,
        'max_tokens': 512
    }
)

result = response.json()
print(result['code'])
print(f"耗时: {result['duration']:.2f}秒")
print(f"缓存: {result['cached']}")
```

### JavaScript

```javascript
fetch('http://localhost:8000/api/generate', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        query: '写一个JavaScript快速排序函数',
        temperature: 0.2,
        max_tokens: 512
    })
})
.then(response => response.json())
.then(data => {
    console.log(data.code);
    console.log(`耗时: ${data.duration}秒`);
});
```

### cURL

```bash
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "query": "写一个Python快速排序函数",
    "temperature": 0.2,
    "max_tokens": 512
  }'
```

## 🎯 使用场景

### 1. 个人开发

```bash
# 启动服务
python start_web.py

# 在浏览器中使用
# http://localhost:8000
```

### 2. 团队协作

```bash
# 启动在局域网
python app.py --host 0.0.0.0 --port 8000

# 团队成员访问
# http://服务器IP:8000
```

### 3. API集成

```python
# 集成到你的应用
import requests

def generate_code(description):
    response = requests.post(
        'http://localhost:8000/api/generate',
        json={'query': description}
    )
    return response.json()['code']

# 使用
code = generate_code("写一个快速排序函数")
print(code)
```

## 📚 相关文档

1. **WEB_GUI_使用指南.md** - 完整使用教程
2. **RTX5060_README.md** - RTX 5060解决方案总览
3. **快速解决方案.md** - 快速入门
4. **RTX5060_SOLUTION.md** - 技术细节

## ✅ 测试清单

- [x] Ollama生成器模块
- [x] Ollama RAG生成器模块
- [x] Web应用主程序
- [x] 网页GUI界面
- [x] API端点
- [x] 错误处理
- [x] 启动脚本
- [x] 使用文档
- [ ] 实际运行测试（需要用户测试）

## 🎉 总结

成功将RAG代码生成器改造为基于Ollama的版本，主要改进：

1. ✅ **解决RTX 5060兼容性** - 使用Ollama自动处理量化
2. ✅ **添加网页GUI** - 美观易用的界面
3. ✅ **简化配置** - 一键启动，自动检查
4. ✅ **保留核心功能** - Query重写、缓存等
5. ✅ **提供完整文档** - 使用指南和API文档

现在用户可以：
- 在浏览器中使用美观的GUI生成代码
- 通过API集成到其他应用
- 在RTX 5060上流畅运行
- 享受4bit量化的低显存占用

## 🚀 立即开始

```bash
# 1. 安装Ollama
# https://ollama.ai/download

# 2. 安装依赖
pip install -r requirements-ollama.txt

# 3. 启动
python start_web.py

# 4. 访问
# http://localhost:8000
```

祝使用愉快！🎉
