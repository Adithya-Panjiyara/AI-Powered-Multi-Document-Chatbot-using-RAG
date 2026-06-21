# AI-Powered Multi-Document Chatbot using RAG

## Overview

AI-Powered Multi-Document Chatbot is an intelligent Retrieval-Augmented Generation (RAG) system that allows users to upload and interact with multiple document formats, including PDF, Word, Excel, and CSV files. The chatbot combines semantic search, vector embeddings, SQL querying, and Generative AI to provide accurate answers from uploaded documents.

The system automatically extracts text and tables from documents, stores them in vector and relational databases, and enables natural language interaction with the stored knowledge.

---
## Features

### Document Processing

* Upload and process PDF, DOCX, XLSX, XLS, and CSV files
* Automatic text extraction from documents
* Table extraction and storage in SQLite database
* Support for multiple documents

### Vector Search (RAG)

* Semantic document search using embeddings
* ChromaDB vector database for retrieval
* High-quality embeddings using BAAI/bge-large-en-v1.5
* Context-aware question answering

### AI-Powered Responses

* Google Gemini integration
* Intelligent query classification
* Context-based answer generation
* Source chunk tracking for transparency

### SQL Query Generation

* Natural language to SQL conversion
* Automatic database schema understanding
* Query execution on extracted tables
* Data analysis through conversational queries

### File Management

* Add new documents
* Replace existing documents
* Remove documents and associated vectors
* View available tables

---
## Project Architecture

```text
AI-Powered Multi-Document Chatbot
│
├── chroma_db/
│
├── Data Files/
│
├── models/
│   ├── db.py
│   ├── schema.sql
│   └── table_processor.py
│
├── utils/
│   ├── chroma_utils.py
│   ├── Chunks_vectorization.py
│   ├── File_handling.py
│   ├── gemini_handler.py
│   └── synonym_inserter.py
│
├── data.db
├── main.py
├── requirements.txt
└── README.md
```

---
## Technologies Used

### Artificial Intelligence

* Google Gemini API
* Retrieval-Augmented Generation (RAG)
* Semantic Search
* Embedding Models

### Machine Learning

* Sentence Transformers
* BAAI/bge-large-en-v1.5

### Databases

* ChromaDB (Vector Database)
* SQLite (Structured Data Storage)

### Python Libraries

* Sentence Transformers
* ChromaDB
* PyMuPDF
* pdfplumber
* pandas
* torch
* python-docx

---
## Workflow

1. User uploads a document.
2. Text is extracted from the document.
3. Text is divided into chunks.
4. Chunks are converted into embeddings.
5. Embeddings are stored in ChromaDB.
6. Tables are extracted and stored in SQLite.
7. User asks a question.
8. Relevant chunks are retrieved using semantic search.
9. Gemini generates a response using retrieved context.
10. The chatbot returns the answer along with source references.

---
## Example Queries

### Document Queries

* Summarize this document
* What is the main topic of the report?
* Show key insights from the document
* What information is available in this file?

### Data Queries

* Show all rows
* Count total records
* What is the average sales value?
* Which region has the highest sales?
* Show top 10 entries by revenue

---
## Installation

### Clone Repository
```bash
git clone https://github.com/Adithya-Panjiyara/AI-Powered-Multi-Document-Chatbot-using-RAG.git
cd AI-Powered-Multi-Document-Chatbot-using-RAG
```

### Create Virtual Environment
```bash
python -m venv .venv
```

### Activate Environment
Windows:

```bash
.venv\Scripts\activate
```

Linux/Mac:

```bash
source .venv/bin/activate
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Configure Gemini API Key
Create a `.env` file:
```env
GEMINI_API_KEY=your_api_key_here
```

### Run Application
```bash
python main.py
```

---
## Future Improvements

* Multi-file querying
* Chat history memory
* Web-based interface using Streamlit
* OCR support for scanned PDFs
* Image understanding using Gemini Vision
* User authentication
* Export chat conversations
* Hybrid search (Keyword + Vector Search)
* Reranking for improved retrieval accuracy

---
## Applications

* Educational Assistance
* Research Document Analysis
* Business Intelligence
* Financial Report Analysis
* Knowledge Management
* Enterprise Search Systems
* Data Analytics

---
## Author

**Adithya Panjiyara**

B.Tech Artificial Intelligence & Machine Learning

Interested in:

* NLP
* Generative AI
* Computer Vision
* Reinforcement Learning

GitHub: https://github.com/Adithya-Panjiyara
