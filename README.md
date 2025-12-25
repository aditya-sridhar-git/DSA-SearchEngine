# 🔍 Mini Google - RAG Search Engine

A powerful mini search engine that combines **C data structures** (Trie, Hash Table, Linked Lists) with **AI-powered RAG** (Retrieval-Augmented Generation) using Ollama. Features both a sleek React chat interface and a standalone HTML search dashboard.

## ✨ Features

### 🧠 Core Search Engine (C)
- **Trie Data Structure** - Efficient prefix-based searching and autocomplete
- **Hash Table** - O(1) average-case lookup for exact keyword searches
- **Linked Lists** - Document occurrence tracking and collision handling
- **Word Frequency Analysis** - Track word occurrences across documents
- **Multi-Keyword Search** - Find documents containing all specified keywords

### 🤖 AI Integration
- **Ollama Integration** - Local LLM support (phi model) for intelligent responses
- **Document Summarization** - AI-powered text summarization
- **RAG Queries** - Ask questions and get AI-generated answers

### 💻 Dual Interface
- **React Chat UI** - Modern ChatGPT-style chat interface with file upload
- **HTML Dashboard** - Traditional search engine interface with visual stats

## 🏗️ Architecture

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│   React/HTML    │◄────►│  Python Bridge   │◄────►│   C Search      │
│   Frontend      │      │  Server (8080)   │      │   Engine CLI    │
└─────────────────┘      └────────┬─────────┘      └─────────────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │  Ollama (LLM)    │
                         │  localhost:11434 │
                         └──────────────────┘
```

## 📁 Project Structure

```
RAGSearchEngine/
├── bridgeServer.py      # Python HTTP server (API endpoints)
├── searchCLI.c          # C search engine CLI wrapper
├── searchCLI.exe        # Compiled C executable
├── searchEngine.c       # Core C search engine implementation
├── index.html           # Standalone HTML search interface
├── documents/           # Sample text documents
│   ├── artificial_intelligence.txt
│   ├── climate_change.txt
│   ├── quantum_computing.txt
│   ├── renewable_energy.txt
│   └── space_exploration.txt
└── frontend/            # React chat interface
    ├── src/
    │   ├── App.tsx
    │   └── components/
    │       ├── ChatInterface.tsx
    │       └── MessageBubble.tsx
    └── package.json
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 18+ (for React frontend)
- GCC compiler (for C code)
- [Ollama](https://ollama.ai/) (for AI features)

### 1. Compile the C Search Engine
```bash
gcc searchCLI.c -o searchCLI.exe
```

### 2. Start Ollama (for AI features)
```bash
ollama run phi
```

### 3. Start the Bridge Server
```bash
python bridgeServer.py
```

### 4. Access the Application

**Option A: HTML Interface**
- Open browser to `http://localhost:8080`

**Option B: React Chat Interface**
```bash
cd frontend
npm install
npm run dev
```
- Open browser to `http://localhost:5173`

## 🔧 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/documents` | GET | Get all indexed documents |
| `/api/stats` | GET | Get search engine statistics |
| `/api/search?query=&type=` | GET | Perform search (keyword/prefix/multi) |
| `/api/autocomplete?q=` | GET | Get autocomplete suggestions |
| `/api/index` | POST | Index a new document |
| `/api/rag` | POST | Query AI with RAG |
| `/api/upload` | POST | Upload file for summarization |
| `/api/analyze` | POST | Analyze document with C engine |

## 💡 Usage Examples

### Keyword Search
Search for exact word matches across all documents.

### Prefix Search
Find all words starting with a given prefix (autocomplete).

### Multi-Keyword Search
Find documents containing **all** specified keywords, ranked by relevance.

### Document Analysis (C Engine)
Upload a `.txt` file and analyze it using:
- **Word Frequency** - Count occurrences of a specific word
- **Keyword Search** - Find documents containing a keyword
- **Prefix Search** - Find all words with a given prefix

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Search Engine | C (Trie, Hash Table, Linked Lists) |
| Backend Server | Python (http.server) |
| AI/LLM | Ollama (phi model) |
| Chat Frontend | React + TypeScript + Vite |
| Dashboard Frontend | Vanilla HTML/CSS/JavaScript |

## 📊 Data Structures

### Trie
- Stores words character by character
- Enables O(m) prefix search where m = prefix length
- Each end node contains document occurrence list

### Hash Table
- DJB2 hash function for word hashing
- Chaining for collision resolution
- Direct pointer to trie nodes for O(1) lookup

### Linked Lists
- Document occurrence tracking (doc_id, frequency)
- Hash table collision chains
- Document metadata storage

## 🔮 Possible Extensions
- TF-IDF scoring for better relevance ranking
- Phrase searching with quotes
- Boolean operators (AND, OR, NOT)
- File crawler to index entire directories
- Multiple LLM model support

## 📄 License

MIT License - feel free to use and modify!

## 👨‍💻 Author

Created with ❤️ as a demonstration of fundamental data structures in action.
