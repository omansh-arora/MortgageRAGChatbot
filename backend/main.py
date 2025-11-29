from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import logging
from typing import Optional
from contextlib import asynccontextmanager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from rag import get_rag_instance
import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

rag_system = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global rag_system
    try:
        logger.info("Initializing RAG system...")
        rag_system = get_rag_instance()
        logger.info("RAG system initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize RAG system: {e}")
        raise
    
    yield
    
    # Shutdown (if needed)
    logger.info("Shutting down...")


app = FastAPI(
    title="Mortgage RAG Chatbot API",
    description="AI-powered mortgage information chatbot using RAG",
    version="1.0.0",
    lifespan=lifespan
)

# Rate limiting setup
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="User's question")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "What documents do I need for a mortgage application?"
            }
        }


class SourceInfo(BaseModel):
    content: str
    metadata: dict


class ChatResponse(BaseModel):
    answer: str = Field(..., description="AI-generated answer")
    sources: list[SourceInfo] = Field(default=[], description="Source documents used")
    
    class Config:
        json_schema_extra = {
            "example": {
                "answer": "For a mortgage application, you typically need...",
                "sources": [
                    {
                        "content": "Required documents include proof of income...",
                        "metadata": {"source": "mortgage_requirements.md"}
                    }
                ]
            }
        }


@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "Mortgage RAG Chatbot API",
        "version": "1.0.0",
        "endpoints": {
            "chat": "/chat",
            "health": "/health",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    try:
        if rag_system is None:
            return JSONResponse(
                status_code=503,
                content={"status": "unhealthy", "message": "RAG system not initialized"}
            )
        
        return {
            "status": "healthy",
            "rag_initialized": True,
            "vectorstore_ready": rag_system.vectorstore is not None
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "message": str(e)}
        )


@app.post("/chat", response_model=ChatResponse)
@limiter.limit("20/minute")
async def chat(request: Request, chat_request: ChatRequest):
    try:
        logger.info(f"Received chat request: {chat_request.message[:100]}...")
        
        if rag_system is None:
            raise HTTPException(
                status_code=503,
                detail="RAG system not initialized. Please try again later."
            )
        
        result = rag_system.query(chat_request.message)
        
        response = ChatResponse(
            answer=result["answer"],
            sources=[
                SourceInfo(
                    content=source["content"],
                    metadata=source["metadata"]
                )
                for source in result["sources"]
            ]
        )
        
        logger.info("Chat request processed successfully")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing chat request: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred processing your request. Please try again."
        )


@app.post("/rebuild-index")
async def rebuild_index():
    try:
        logger.info("Rebuilding vectorstore index...")
        
        if rag_system is None:
            raise HTTPException(
                status_code=503,
                detail="RAG system not initialized"
            )
        
        rag_system.rebuild_index()
        
        return {
            "status": "success",
            "message": "Vectorstore index rebuilt successfully"
        }
        
    except Exception as e:
        logger.error(f"Error rebuilding index: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to rebuild index: {str(e)}"
        )


@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": "The requested endpoint does not exist",
            "path": str(request.url)
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred. Please try again later."
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting server on {config.API_HOST}:{config.API_PORT}")
    uvicorn.run(
        "main:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=True,  # Enable auto-reload during development
        log_level="info"
    )
