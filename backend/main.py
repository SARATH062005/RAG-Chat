# File: backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import rag_core

# Define the data model for the request body
class QueryRequest(BaseModel):
    query: str

# Initialize the FastAPI app
app = FastAPI()

# Configure CORS (Cross-Origin Resource Sharing)
# This allows your React frontend (running on a different port) to communicate with the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # The origin of your React app
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "Visual RAG API is running"}

@app.post("/api/query")
def process_query(request: QueryRequest):
    """
    Receives a query, processes it using the RAG pipeline, 
    and returns the answer and sources.
    """
    result = rag_core.query_visual_rag(request.query)
    return result

# To run the server: uvicorn main:app --reload