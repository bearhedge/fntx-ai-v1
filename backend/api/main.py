#!/usr/bin/env python3
"""
FNTX AI Clean API Server
Minimal FastAPI server focused on authentication and core functionality
"""

import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="FNTX AI API",
    description="Clean API server for FNTX trading system",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include authentication router
from backend.api.auth_api import router as auth_router
app.include_router(auth_router)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "FNTX AI API is running", "version": "2.0.0"}

@app.get("/health")
async def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "service": "fntx-api",
        "version": "2.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.api.main:app", 
        host=os.getenv("API_HOST", "127.0.0.1"),
        port=int(os.getenv("API_PORT", "8000")),
        reload=False  # Simplified for now
    )