# pomCoder - Intelligent Code Generation Assistant

An intelligent code generation system based on Ollama + RAG, providing code generation, AI chat, knowledge base management, and more.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start Ollama

Ensure Ollama service is running at `http://localhost:11434`

```bash
ollama serve
```

### 3. Download Model

```bash
ollama pull deepseek-coder:6.7b
# You can also download other models as needed
```

### 4. Start Service

```bash
python app_full.py
```

Service will run at: http://localhost:58761

## ✨ Features

### 1. Code Generation
- Generate code from natural language descriptions
- Support for multiple programming languages
- Adjustable temperature and token count
- Code syntax highlighting

### 2. AI Chat Assistant
- Multi-turn conversation support
- Persistent conversation history
- Markdown rendering
- Code block syntax highlighting
- Optional RAG enhancement (disabled by default)

### 3. Code Slicer Tool
- Automatic folder scanning
- Support for multiple file types (.py, .js, .ts, .jsx, .tsx, .java, .cpp, .c)
- Auto-skip dependency directories (node_modules, __pycache__, etc.)
- Configurable file count and code length

### 4. Knowledge Base Management
- Import code slices
- Append/Overwrite modes
- NPU acceleration support
- FAISS vector retrieval
- BM25 text retrieval

### 5. OpenAI Compatible API
- Chat Completions API
- Completions API
- Streaming response support
- API Key: `pom-0721`

## 🔧 Configuration

### Default Settings
- **Model Name**: deepseek-coder:6.7b
- **API Port**: 58761
- **API Key**: pom-0721
- **Embedding Model**: sentence-transformers/all-MiniLM-L6-v2
- **Knowledge Base Path**: ./knowledge_base
- **Conversation Storage**: ./conversations

### Modify Configuration

Edit `config.yaml` or specify parameters at startup:

```bash
python app_full.py --model deepseek-coder:6.7b --port 58761
```

## 📚 API Documentation

### OpenAI Compatible API

**Base URL**: `http://localhost:58761/v1`

**Chat Completions**:
```bash
curl http://localhost:58761/v1/chat/completions \
  -H "Authorization: Bearer pom-0721" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "pomcoder",
    "messages": [{"role": "user", "content": "Write a quicksort algorithm"}],
    "temperature": 0.2,
    "max_tokens": 512
  }'
```

### Code Generation API

```bash
curl http://localhost:58761/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Write a Python quicksort function",
    "temperature": 0.2,
    "max_tokens": 512
  }'
```

### Conversation Management API

- `POST /api/conversations/create` - Create conversation
- `GET /api/conversations/list` - List conversations
- `GET /api/conversations/{id}` - Get conversation details
- `POST /api/conversations/chat` - Send message
- `DELETE /api/conversations/{id}` - Delete conversation

## 📁 Project Structure

```
pom_coder/
├── app_full.py                 # Main server
├── build_knowledge_base_npu.py # Knowledge base builder
├── code_slicer.py              # Code slicer tool
├── kill_port_58761.py          # Port management tool
├── restart_server.py           # Server restart script
├── config.yaml                 # Configuration file
├── requirements.txt            # Python dependencies
├── static/                     # Frontend static files
│   ├── index.html             # Main page
│   ├── app.js                 # JavaScript logic
│   ├── styles.css             # Stylesheet
│   └── icon.jpg               # Website icon
├── src/                        # Backend source code
│   └── rag_code_generator/
│       ├── ollama_rag_generator.py
│       ├── ollama_generator.py
│       ├── conversation.py
│       └── ...
├── knowledge_base/             # Knowledge base data
│   ├── faiss_index.bin
│   ├── embeddings.npy
│   ├── snippets.json
│   └── ...
└── conversations/              # Conversation history
```

## 🛠️ Utility Scripts

### Restart Server
```bash
python restart_server.py
```

### Kill Process on Port
```bash
python kill_port_58761.py
```

### Build Knowledge Base
```bash
python build_knowledge_base_npu.py
```

### Code Slicing
```bash
python code_slicer.py
```

## 📖 Usage Guide

### Code Slicing Workflow

1. Select "Code Slicer" tab in web interface
2. Enter directory path to scan
3. Select file types
4. Click "Start Slicing"
5. Wait for completion, results saved in `code_slices.json`

### Knowledge Base Building Workflow

1. Select "Knowledge Base Management" tab in web interface
2. Upload `code_slices.json` file
3. Choose import mode (Append/Overwrite)
4. Check "Use NPU Acceleration" (if supported)
5. Click "Build Knowledge Base"
6. Wait for completion

### AI Chat Workflow

1. Select "AI Chat" tab in web interface
2. Click "New Conversation" to create new session
3. Enter message and send
4. Optionally enable RAG enhancement
5. Adjust temperature parameter to control creativity

## 🔍 Troubleshooting

### Port Already in Use
```bash
python kill_port_58761.py
```

### Model Not Downloaded
```bash
ollama pull deepseek-coder:6.7b
```

### Ollama Service Not Running
```bash
ollama serve
```

### Knowledge Base Not Loaded
Check if necessary files exist in `knowledge_base/` directory

## 🤝 Contributing

Issues and Pull Requests are welcome!

## 📧 Contact

For questions, please submit an Issue.
