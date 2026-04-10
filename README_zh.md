# pomCoder - 智能代码生成助手

基于 Ollama + RAG 的智能代码生成系统，提供代码生成、AI对话、知识库管理等功能。

## ✨ 最新更新 (V3.6.2)

### 🆕 新增功能
- **离线模式支持** - 自动使用本地缓存，断网环境下也能运行
- **AI对话右键删除** - 右键点击对话项快速删除
- **知识库自动重载** - 训练完成后自动刷新，无需重启服务
- **一键清除知识库** - 快速清空所有embedding数据

### 🚀 快速启动（离线模式）

**Windows**:
```bash
start_offline.bat
```

**Linux/Mac**:
```bash
chmod +x start_offline.sh
./start_offline.sh
```

**Python**:
```bash
python start_offline.py
```

##  快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动 Ollama

确保 Ollama 服务运行在 `http://localhost:11434`

```bash
ollama serve
```

### 3. 下载模型

```bash
ollama pull deepseek-coder:6.7b
#您也可以下载自己需要的模型
```

### 4. 启动服务

```bash
python app_full.py
```

服务将运行在：http://localhost:58761

##  功能特性

### 1. 代码生成
- 基于自然语言描述生成代码
- 支持多种编程语言
- 可调节温度和Token数
- 代码语法高亮显示

### 2. AI对话助手 ⭐ 新增右键删除
- 多轮对话支持
- 对话历史持久化
- **右键菜单快速删除对话**
- Markdown渲染
- 代码块语法高亮
- 可选RAG增强（默认关闭）

### 3. 代码切片工具 (V3.5 S+级)
- 自动扫描文件夹
- 支持多种文件类型（.py, .js, .ts, .jsx, .tsx, .java, .cpp, .c）
- 自动跳过依赖目录（node_modules, __pycache__等）
- **Token级精确控制**（最大/最小Token、重叠）
- **多级切片策略**（结构 → Token → Fallback）
- **质量评分系统**（0-10分）
- **深度AST子节点切片**（控制流级别）
- **语义上下文增强**（10+项特征）
- 丰富的元数据提取

### 4. 知识库管理 ⭐ 新增自动重载
- 导入代码切片
- 叠加/覆盖模式
- **训练完成后自动重载**（无需重启）
- **一键清除知识库**
- NPU加速支持
- FAISS向量检索
- BM25文本检索

### 5. 离线模式 ⭐ 新增
- **自动使用本地缓存**
- **断网环境下正常运行**
- **专用离线启动脚本**
- 多重环境变量保护

### 6. OpenAI兼容API
- Chat Completions API
- Completions API
- 支持流式响应
- API密钥：`pom-0721`

## 🔧 配置说明

### 默认配置
- **模型名称**：deepseek-coder:6.7b
- **API端口**：58761
- **API密钥**：pom-0721
- **Embedding模型**：sentence-transformers/all-MiniLM-L6-v2
- **知识库路径**：./knowledge_base
- **对话存储**：./conversations

### 修改配置

编辑 `config.yaml` 或在启动时指定参数：

```bash
python app_full.py --model deepseek-coder:6.7b --port 58761
```

## API文档

### OpenAI兼容API

**Base URL**: `http://localhost:58761/v1`

**Chat Completions**:
```bash
curl http://localhost:58761/v1/chat/completions \
  -H "Authorization: Bearer pom-0721" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "pomcoder",
    "messages": [{"role": "user", "content": "写一个快速排序"}],
    "temperature": 0.2,
    "max_tokens": 512
  }'
```

### 代码生成API

```bash
curl http://localhost:58761/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "query": "写一个Python快速排序函数",
    "temperature": 0.2,
    "max_tokens": 512
  }'
```

### 对话管理API

- `POST /api/conversations/create` - 创建对话
- `GET /api/conversations/list` - 列出对话
- `GET /api/conversations/{id}` - 获取对话详情
- `POST /api/conversations/chat` - 发送消息
- `DELETE /api/conversations/{id}` - 删除对话

## 项目结构

```
pom_coder/
├── app_full.py                 # 主服务器
├── build_knowledge_base_npu.py # 知识库构建工具
├── code_slicer.py              # 代码切片工具（V3.5 S+级）
├── start_offline.py            # 离线模式启动脚本
├── start_offline.bat           # Windows离线启动
├── start_offline.sh            # Linux/Mac离线启动
├── kill_port_58761.py          # 端口管理工具
├── restart_server.py           # 服务器重启脚本
├── CHANGELOG.md                # 版本更新日志
├── config.yaml                 # 配置文件
├── requirements.txt            # Python依赖
├── static/                     # 前端静态文件
│   ├── index.html             # 主页面
│   ├── app.js                 # JavaScript逻辑
│   ├── styles.css             # 样式表
│   └── icon.jpg               # 网站图标
├── src/                        # 后端源码
│   └── rag_code_generator/
│       ├── ollama_rag_generator.py
│       ├── ollama_generator.py
│       ├── conversation.py
│       └── ...
├── docs/                       # 文档目录
│   ├── V3.6_知识库自动重载功能.md
│   ├── AI对话右键删除功能.md
│   ├── 离线模式配置指南.md
│   ├── 知识库构建指南.md
│   └── ...
├── knowledge_base/             # 知识库数据
│   ├── faiss_index.bin
│   ├── embeddings.npy
│   ├── snippets.json
│   └── ...
└── conversations/              # 对话历史
```

## 工具脚本

### 重启服务器
```bash
python restart_server.py
```

### 停止占用端口的进程
```bash
python kill_port_58761.py
```

### 构建知识库
```bash
python build_knowledge_base_npu.py
```

### 代码切片
```bash
python code_slicer.py
```

## 使用说明

### 离线模式使用

**首次使用（联网环境）**：
```bash
# 正常启动，会自动下载模型到本地缓存
python app_full.py
```

**断网环境使用**：
```bash
# 使用离线启动脚本
start_offline.bat  # Windows
./start_offline.sh  # Linux/Mac
python start_offline.py  # 跨平台
```

### AI对话功能

1. 在Web界面选择"AI对话"标签
2. 点击"新建对话"创建新会话
3. 输入消息并发送
4. **右键点击对话项可快速删除**
5. 可选择是否使用RAG增强
6. 调节温度参数控制创造性

### 代码切片工作流

1. 在Web界面选择"代码切片"标签
2. 输入要扫描的目录路径
3. 选择文件类型
4. 点击"开始切片"
5. 等待切片完成，结果保存在 `code_slices.json`

### 知识库构建工作流

1. 在Web界面选择"知识库管理"标签
2. 上传 `code_slices.json` 文件
3. 选择导入模式（叠加/覆盖）
4. 勾选"使用NPU加速"（如果支持）
5. 点击"构建知识库"
6. **等待构建完成，自动重载（无需重启）**
7. 可使用"清除知识库"按钮一键清空

## 故障排除

### 断网环境下无法启动

**问题**：提示无法连接到 huggingface.co

**解决**：
```bash
# 使用离线启动脚本
start_offline.bat  # Windows
./start_offline.sh  # Linux/Mac
```

详见：`docs/离线模式配置指南.md`

### 端口被占用
```bash
python kill_port_58761.py
```

### 模型未下载
```bash
ollama pull deepseek-coder:6.7b
```

### Ollama服务未启动
```bash
ollama serve
```

### 知识库未加载
检查 `knowledge_base/` 目录是否存在必要文件

### 知识库训练后不生效

**V3.6+版本**：自动重载，无需重启

**旧版本**：需要手动重启服务
```bash
python restart_server.py
```

## 📚 文档

- [CHANGELOG.md](CHANGELOG.md) - 版本更新日志
- [V3.6 知识库自动重载功能](docs/V3.6_知识库自动重载功能.md)
- [AI对话右键删除功能](docs/AI对话右键删除功能.md)
- [离线模式配置指南](docs/离线模式配置指南.md)
- [知识库构建指南](docs/知识库构建指南.md)
- [代码切片系统说明](docs/代码切片系统说明.md)


## 贡献

欢迎提交 Issue 和 Pull Request！

## 联系方式

如有问题，请提交 Issue。
