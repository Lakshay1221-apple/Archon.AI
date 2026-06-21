# Archon AI

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue.svg">
  <img src="https://img.shields.io/badge/RAG-Retrieval%20Augmented%20Generation-green.svg">
  <img src="https://img.shields.io/badge/VectorDB-ChromaDB-orange.svg">
  <img src="https://img.shields.io/badge/LLM-Qwen%20%7C%20TinyLlama-red.svg">
  <img src="https://img.shields.io/badge/License-MIT-purple.svg">
</p>

---

## Overview

Archon AI is an intelligent Repository Question Answering System powered by Retrieval-Augmented Generation (RAG).

Instead of manually navigating hundreds of files, developers can ask natural language questions about a GitHub repository and receive accurate, source-grounded answers generated from the repository itself.

Archon AI transforms software repositories into searchable knowledge bases using semantic chunking, vector embeddings, metadata-aware retrieval, and Large Language Models.

---

## Why Archon AI?

Modern repositories often contain:

* Thousands of files
* Complex execution flows
* Hidden configuration logic
* Distributed business logic
* Difficult onboarding experiences

Traditional search tools require developers to know exact file names, functions, or keywords.

Archon AI enables semantic understanding of repositories by answering questions such as:

* How does training start?
* Where is LoRA configured?
* Which file loads the dataset?
* Explain the architecture of this repository.
* How does authentication work?
* What is the execution flow of this application?

---

## Key Features

### Repository Ingestion

* Clone GitHub repositories automatically
* Scan and process source files
* Filter unsupported files
* Build repository datasets

### Semantic Code Chunking

Extract meaningful retrieval units:

* Functions
* Classes
* Methods
* Documentation
* Configuration Files

### Metadata-Aware Retrieval

Each chunk stores:

* Repository name
* File path
* Language
* Chunk type
* Symbol name

This improves retrieval accuracy and explainability.

### Vector Search

* Semantic embeddings using Sentence Transformers
* Fast similarity search with ChromaDB
* Top-K context retrieval

### Repository Question Answering

Ask questions in natural language and receive:

* Grounded explanations
* Relevant code context
* Source attribution

### Source Transparency

Every answer includes:

* Source file
* Function/Class name
* Retrieval relevance

---

# System Architecture

```text
Repository URL
      │
      ▼
Repository Loader
      │
      ▼
File Parser
      │
      ▼
Semantic Chunker
      │
      ▼
Metadata Generator
      │
      ▼
Embedding Model
      │
      ▼
ChromaDB Vector Store
      │
      ▼
────────────────────────────
      │
      ▼
User Question
      │
      ▼
Question Embedding
      │
      ▼
Retriever
      │
      ▼
Top-K Chunks
      │
      ▼
Prompt Builder
      │
      ▼
LLM
      │
      ▼
Grounded Answer + Sources
```

---

# Tech Stack

| Component         | Technology            |
| ----------------- | --------------------- |
| Language          | Python                |
| Repository Access | GitPython             |
| Parsing           | AST, Pathlib          |
| Embeddings        | Sentence Transformers |
| Embedding Model   | all-MiniLM-L6-v2      |
| Vector Database   | ChromaDB              |
| Retrieval         | Cosine Similarity     |
| LLM               | TinyLlama / Qwen 2.5  |
| Runtime           | Ollama                |
| Frontend          | Streamlit             |

---

# Project Structure

```text
archon-ai/

├── data/
│   ├── repositories/
│   └── processed/
│
├── chroma_db/
│
├── src/
│   ├── ingestion/
│   │   ├── clone_repo.py
│   │   ├── parser.py
│   │   └── file_filter.py
│   │
│   ├── chunking/
│   │   ├── ast_chunker.py
│   │   └── metadata_builder.py
│   │
│   ├── embeddings/
│   │   └── embedder.py
│   │
│   ├── vectorstore/
│   │   └── chroma_manager.py
│   │
│   ├── retrieval/
│   │   └── retriever.py
│   │
│   ├── prompting/
│   │   └── prompt_builder.py
│   │
│   ├── llm/
│   │   └── generator.py
│   │
│   └── pipeline/
│       └── rag_pipeline.py
│
├── app/
│   └── streamlit_app.py
│
├── tests/
│
├── requirements.txt
├── README.md
└── main.py
```

---

# Installation

## Clone Repository

```bash
git clone https://github.com/Lakshay1221-apple/Archon.AI-.git

cd Archon.AI-
```

## Create Virtual Environment

```bash
python -m venv .venv
```

### Linux / macOS

```bash
source .venv/bin/activate
```

### Windows

```bash
.venv\Scripts\activate
```

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

# Running Archon AI

## Step 1: Ingest Repository

```bash
python src/ingestion/clone_repo.py
```

## Step 2: Generate Chunks

```bash
python src/chunking/ast_chunker.py
```

## Step 3: Create Embeddings

```bash
python src/embeddings/embedder.py
```

## Step 4: Build Vector Database

```bash
python src/vectorstore/chroma_manager.py
```

## Step 5: Start Application

```bash
streamlit run app/streamlit_app.py
```

---

# Repository Dataset Format

Each repository chunk follows a standardized schema:

```json
{
  "id": "chunk_001",
  "repo": "repository_name",
  "path": "src/train.py",
  "language": "python",
  "chunk_type": "function",
  "symbol": "train_model",
  "content": "...",
  "summary": "Initializes model training pipeline"
}
```

---

# Example Questions

```text
How does model training start?

Where is LoRA configured?

Which file loads the dataset?

Explain the architecture of this repository.

How is authentication implemented?

Show the execution flow of the application.
```

---

# Development Roadmap

## Phase 1

* Repository Ingestion
* File Parsing
* Dataset Generation

## Phase 2

* Embeddings
* ChromaDB Integration
* Semantic Retrieval

## Phase 3

* LLM Integration
* Repository QA
* Source Attribution

## Phase 4

* Hybrid Search
* BM25 + Vector Retrieval

## Phase 5

* Cross-Encoder Re-Ranking
* Top-20 → Best-5 Selection

## Phase 6

* Architecture Understanding
* Repository Summaries
* Execution Flow Analysis
* Advanced Code Reasoning

---

# Learning Outcomes

Building Archon AI provides hands-on experience with:

* Retrieval-Augmented Generation (RAG)
* Repository Indexing
* Semantic Search
* Embedding Models
* Vector Databases
* Hybrid Retrieval Systems
* Cross-Encoder Re-ranking
* LLM Integration
* Production AI Pipelines

---

# Future Enhancements

* Multi-repository support
* Graph-based code understanding
* Dependency analysis
* Repository architecture visualization
* Agentic code exploration
* Automated documentation generation
* GitHub pull request understanding
* Code review assistant

---

# Contributing

Contributions are welcome.

If you'd like to improve Archon AI:

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Open a Pull Request

---

# License

This project is licensed under the MIT License.

---

# Author

**Lakshay**

Archon AI was built as a production-focused RAG project to bridge the gap between theoretical Retrieval-Augmented Generation concepts and real-world repository intelligence systems.
