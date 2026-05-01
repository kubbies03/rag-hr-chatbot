"""
Document ingestion pipeline for the RAG subsystem.

Pipeline stages:
1. Load raw content from PDF, DOCX, or TXT
2. Split content into retrieval-friendly chunks
3. Attach metadata used later for filtering and citations
4. Generate embeddings for each chunk
5. Persist chunks and vectors into ChromaDB

This module is the write path for the document knowledge base.
"""

import os
import uuid
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.core.config import settings
from app.services.embedding_service import get_embeddings
from app.services.retriever_service import get_collection


def load_document(file_path: str) -> list:
    """
    Read a supported source file and return LangChain document objects.
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        loader = PyPDFLoader(file_path)
        return loader.load()

    if ext == ".docx":
        from docx import Document as DocxDocument
        from langchain_core.documents import Document

        doc = DocxDocument(file_path)
        full_text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        return [Document(page_content=full_text, metadata={"source": file_path})]

    if ext == ".txt":
        loader = TextLoader(file_path, encoding="utf-8")
        return loader.load()

    raise ValueError(f"Unsupported file format: {ext}")


def split_documents(documents: list) -> list:
    """
    Split source documents into chunks sized for embedding and retrieval.
    """
    # The separator order matters. We prefer preserving higher-level structure
    # first (headings, sections, lists, paragraphs) before falling back to
    # sentence and word boundaries. That usually produces cleaner retrieval
    # chunks for policy and handbook style documents.
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        separators=[
            "\n# ",
            "\n## ",
            "\n### ",
            "\n#### ",
            "\nChapter ",
            "\nSection ",
            "\nPart ",
            "\nArticle ",
            "\n- ",
            "\n* ",
            "\n• ",
            "\n1. ",
            "\n2. ",
            "\n3. ",
            "\n4. ",
            "\n5. ",
            "\n\n",
            "\n",
            ". ",
            "? ",
            "! ",
            " ",
            "",
        ],
    )
    return splitter.split_documents(documents)


def ingest_file(
    file_path: str,
    title: str = None,
    category: str = "general",
    access_level: str = "all",
    department: str = "general",
) -> dict:
    """
    Ingest one file end-to-end into the vector store.
    """
    documents = load_document(file_path)
    if not documents:
        return {"status": "error", "message": "Failed to read file"}

    chunks = split_documents(documents)
    if not chunks:
        return {"status": "error", "message": "Failed to create chunks"}

    file_name = os.path.basename(file_path)
    if title is None:
        title = os.path.splitext(file_name)[0]

    embeddings = get_embeddings()
    texts = [chunk.page_content for chunk in chunks]
    vectors = embeddings.embed_documents(texts)

    collection = get_collection()

    ids = []
    metadatas = []
    for i, chunk in enumerate(chunks):
        chunk_id = f"{file_name}_{uuid.uuid4().hex[:8]}"
        ids.append(chunk_id)

        page = chunk.metadata.get("page", i + 1)

        # Metadata is duplicated per chunk so retrieval can enforce access rules
        # and the API can return user-facing source citations without re-reading
        # the original document.
        metadatas.append({
            "title": title,
            "category": category,
            "access_level": access_level,
            "department": department,
            "source_file": file_name,
            "page": page,
        })

    collection.add(
        ids=ids,
        documents=texts,
        embeddings=vectors,
        metadatas=metadatas,
    )

    return {
        "status": "success",
        "file": file_name,
        "title": title,
        "chunks_created": len(chunks),
        "category": category,
        "access_level": access_level,
    }


def ingest_directory(directory: str = None) -> list[dict]:
    """
    Ingest all supported files in a directory.
    """
    if directory is None:
        directory = settings.DOCS_DIR

    results = []
    supported_exts = {".pdf", ".docx", ".txt"}

    if not os.path.exists(directory):
        return [{"status": "error", "message": f"Directory {directory} does not exist"}]

    for filename in os.listdir(directory):
        ext = os.path.splitext(filename)[1].lower()
        if ext in supported_exts:
            file_path = os.path.join(directory, filename)
            try:
                result = ingest_file(file_path)
                results.append(result)
            except Exception as e:
                results.append({
                    "status": "error",
                    "file": filename,
                    "message": str(e),
                })

    return results


def get_collection_stats() -> dict:
    """Return vector collection statistics."""
    collection = get_collection()
    return {
        "collection_name": settings.CHROMA_COLLECTION_NAME,
        "total_chunks": collection.count(),
    }
