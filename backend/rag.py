import os
from pathlib import Path
from typing import List, Dict, Any
import logging
import mailbox

from langchain_community.document_loaders import (
    DirectoryLoader, 
    TextLoader, 
    PyPDFLoader,
    UnstructuredPDFLoader,
    Docx2txtLoader
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MortgageRAG:
    
    def __init__(self):
        self.embeddings = None
        self.vectorstore = None
        self.retriever = None
        self.llm = None
        self.qa_chain = None
        
        logger.info("Initializing OpenAI embeddings...")
        self.embeddings = OpenAIEmbeddings(
            model=config.EMBEDDING_MODEL,
            openai_api_key=config.OPENAI_API_KEY
        )
        
        logger.info(f"Initializing LLM: {config.LLM_MODEL}")
        self.llm = ChatOpenAI(
            model=config.LLM_MODEL,
            temperature=config.LLM_TEMPERATURE,
            openai_api_key=config.OPENAI_API_KEY
        )
        
        self._initialize_vectorstore()
    
    def _initialize_vectorstore(self):
        try:
            if config.CHROMA_DB_DIR.exists() and any(config.CHROMA_DB_DIR.iterdir()):
                logger.info("Loading existing ChromaDB vectorstore...")
                self.vectorstore = Chroma(
                    collection_name=config.COLLECTION_NAME,
                    embedding_function=self.embeddings,
                    persist_directory=str(config.CHROMA_DB_DIR)
                )
                logger.info(f"Loaded vectorstore with {self.vectorstore._collection.count()} documents")
            else:
                logger.info("No existing vectorstore found. Creating new one...")
                self._build_vectorstore_from_documents()
            
            self.retriever = self.vectorstore.as_retriever(
                search_kwargs={"k": config.RETRIEVAL_K}
            )
            
            self._create_qa_chain()
            
        except Exception as e:
            logger.error(f"Error initializing vectorstore: {e}")
            raise
    
    def _load_email_file(self, file_path: Path) -> List[Document]:
        logger.info(f"Note: Email file detected. Please pre-process with email_processor.py for PII redaction")
        logger.info(f"Skipping direct loading of: {file_path.name}")
        return []

    def _build_vectorstore_from_documents(self):
        logger.info("Building vectorstore from documents...")
        
        if not config.RAW_DOCS_DIR.exists():
            logger.warning("raw_docs directory doesn't exist. Creating empty vectorstore.")
            self.vectorstore = Chroma(
                collection_name=config.COLLECTION_NAME,
                embedding_function=self.embeddings,
                persist_directory=str(config.CHROMA_DB_DIR)
            )
            return
        
        all_documents = []

        # Prefer scraped 'web' folder if present, but include raw_docs as well
        web_dir = config.RAW_DOCS_DIR / 'web'
        data_roots = [web_dir, config.RAW_DOCS_DIR] if web_dir.exists() else [config.RAW_DOCS_DIR]

        logger.info(f"Loading documents from: {', '.join(str(p) for p in data_roots)}")

        def gather_files(pattern: str):
            seen = []
            seen_paths = set()
            for root in data_roots:
                if not root.exists():
                    continue
                for p in root.glob(f"**/{pattern}"):
                    if p.resolve() not in seen_paths:
                        seen.append(p)
                        seen_paths.add(p.resolve())
            return seen

        pdf_files = gather_files("*.pdf")
        if pdf_files:
            logger.info(f"Found {len(pdf_files)} PDF files")
            for pdf_file in pdf_files:
                try:
                    loader = PyPDFLoader(str(pdf_file))
                    docs = loader.load()
                    for doc in docs:
                        doc.metadata["type"] = "pdf"
                    all_documents.extend(docs)
                    logger.info(f"Loaded PDF: {pdf_file.name}")
                except Exception as e:
                    logger.error(f"Error loading {pdf_file}: {e}")
        
        txt_files = gather_files("*.txt")
        if txt_files:
            logger.info(f"Found {len(txt_files)} text files")
            for txt_file in txt_files:
                try:
                    loader = TextLoader(str(txt_file), encoding="utf-8")
                    docs = loader.load()
                    for doc in docs:
                        doc.metadata["type"] = "text"
                    all_documents.extend(docs)
                    logger.info(f"Loaded text file: {txt_file.name}")
                except Exception as e:
                    logger.error(f"Error loading {txt_file}: {e}")
        
        mbox_files = gather_files("*.mbox")
        if mbox_files:
            logger.warning(f"Found {len(mbox_files)} mbox files - Please pre-process with email_processor.py first!")
            logger.warning("Mbox files should be converted to .txt with PII redaction before indexing")
        
        docx_files = gather_files("*.docx")
        if docx_files:
            logger.info(f"Found {len(docx_files)} Word documents")
            for docx_file in docx_files:
                try:
                    loader = Docx2txtLoader(str(docx_file))
                    docs = loader.load()
                    for doc in docs:
                        doc.metadata["type"] = "docx"
                    all_documents.extend(docs)
                    logger.info(f"Loaded Word doc: {docx_file.name}")
                except Exception as e:
                    logger.error(f"Error loading {docx_file}: {e}")
        
        md_files = gather_files("*.md")
        if md_files:
            logger.info(f"Found {len(md_files)} markdown files")
            for md_file in md_files:
                try:
                    loader = TextLoader(str(md_file), encoding="utf-8")
                    docs = loader.load()
                    for doc in docs:
                        doc.metadata["type"] = "markdown"
                    all_documents.extend(docs)
                    logger.info(f"Loaded markdown: {md_file.name}")
                except Exception as e:
                    logger.error(f"Error loading {md_file}: {e}")
        
        logger.info(f"Total documents loaded: {len(all_documents)}")
        
        if not all_documents:
            logger.warning("No documents loaded. Creating empty vectorstore.")
            self.vectorstore = Chroma(
                collection_name=config.COLLECTION_NAME,
                embedding_function=self.embeddings,
                persist_directory=str(config.CHROMA_DB_DIR)
            )
            return
        
        logger.info("Splitting documents into chunks...")
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        chunks = text_splitter.split_documents(all_documents)
        logger.info(f"Created {len(chunks)} chunks from documents")
        
        logger.info("Creating embeddings and storing in ChromaDB...")
        self.vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=self.embeddings,
            collection_name=config.COLLECTION_NAME,
            persist_directory=str(config.CHROMA_DB_DIR)
        )
        logger.info("Vectorstore created and persisted successfully")
    
    def _create_qa_chain(self):
        prompt = ChatPromptTemplate.from_template(config.SYSTEM_PROMPT)
        
        def format_docs(docs):
            return "\n\n".join(doc.page_content for doc in docs)
        
        self.qa_chain = (
            {
                "context": self.retriever | format_docs,
                "question": RunnablePassthrough()
            }
            | prompt
            | self.llm
            | StrOutputParser()
        )
    
    def query(self, question: str) -> Dict[str, Any]:
        try:
            logger.info(f"Processing query: {question[:100]}...")
            
            # Get the answer
            answer = self.qa_chain.invoke(question)
            
            # Get source documents separately
            source_docs = self.retriever.invoke(question)
            
            sources = []
            for i, doc in enumerate(source_docs, 1):
                source_info = {
                    "content": doc.page_content[:300] + "..." if len(doc.page_content) > 300 else doc.page_content,
                    "metadata": doc.metadata
                }
                sources.append(source_info)
            
            logger.info(f"Query processed successfully. Retrieved {len(sources)} source chunks.")
            
            return {
                "answer": answer,
                "sources": sources
            }
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return {
                "answer": "I apologize, but I encountered an error processing your question. Please try again or contact our mortgage advisors directly.",
                "sources": []
            }
    
    def add_documents(self, file_paths: List[str]):
        try:
            logger.info(f"Adding {len(file_paths)} new documents...")
            
            documents = []
            for file_path in file_paths:
                loader = TextLoader(file_path, encoding="utf-8")
                documents.extend(loader.load())
            
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=config.CHUNK_SIZE,
                chunk_overlap=config.CHUNK_OVERLAP,
                length_function=len,
                separators=["\n\n", "\n", " ", ""]
            )
            chunks = text_splitter.split_documents(documents)
            
            self.vectorstore.add_documents(chunks)
            logger.info(f"Successfully added {len(chunks)} chunks to vectorstore")
            
        except Exception as e:
            logger.error(f"Error adding documents: {e}")
            raise
    
    def rebuild_index(self):
        logger.info("Rebuilding vectorstore from scratch...")
        
        if config.CHROMA_DB_DIR.exists():
            import shutil
            shutil.rmtree(config.CHROMA_DB_DIR)
            config.CHROMA_DB_DIR.mkdir(parents=True, exist_ok=True)
        
        self._build_vectorstore_from_documents()
        
        self.retriever = self.vectorstore.as_retriever(
            search_kwargs={"k": config.RETRIEVAL_K}
        )
        self._create_qa_chain()
        
        logger.info("Vectorstore rebuilt successfully")


_rag_instance = None


def get_rag_instance() -> MortgageRAG:
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = MortgageRAG()
    return _rag_instance
