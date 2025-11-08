# File: backend/rag_core.py
import os
import base64
import ollama
import chromadb
from chromadb.utils import embedding_functions

# --- Configuration ---
DB_PATH = "chroma_db"
TEXT_COLLECTION_NAME = "cv_book_texts"
OLLAMA_MODEL = "llava"
TOP_K = 3

# --- Initialize ChromaDB and Embedding Function ---
embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
client = chromadb.PersistentClient(path=DB_PATH)
text_collection = client.get_collection(name=TEXT_COLLECTION_NAME, embedding_function=embedding_func)

def image_to_base64(image_path: str):
    try:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        return None

def query_visual_rag(user_query: str):
    # 1. Retrieve relevant text chunks
    retrieved = text_collection.query(query_texts=[user_query], n_results=TOP_K)
    
    docs = retrieved.get("documents", [[]])[0]
    metas = retrieved.get("metadatas", [[]])[0]

    if not docs:
        return {"answer": "I could not find relevant information in the book to answer your question.", "sources": []}

    context_text = "\n\n---\n\n".join(docs)
    image_path = metas[0].get("image_path")
    image_b64 = image_to_base64(image_path) if image_path and os.path.exists(image_path) else None

    # 2. Build the prompt
    prompt = (
        "You are an expert assistant for computer vision. Use the text context and the image (if provided) to answer.\n"
        "Be technical and concise. If the context is not sufficient, say so.\n\n"
        "--- TEXT CONTEXT ---\n"
        f"{context_text}\n"
        "--------------------\n\n"
        f"USER'S QUESTION: {user_query}\n"
    )

    # 3. Call Ollama LLaVA
    messages = [{"role": "user", "content": prompt}]
    if image_b64:
        messages[0]["images"] = [image_b64]

    try:
        response = ollama.chat(model=OLLAMA_MODEL, messages=messages)
        answer = response["message"]["content"]
    except Exception as e:
        answer = f"Error communicating with Ollama: {e}"

    # 4. Format and return the response
    sources = [{"page": meta.get("source_page"), "image": meta.get("image_path")} for meta in metas]
    return {"answer": answer, "sources": sources}