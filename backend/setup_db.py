# File: backend/setup_db.py
import fitz  # PyMuPDF
import os
import json
import chromadb
from chromadb.utils import embedding_functions
from langchain_text_splitters import RecursiveCharacterTextSplitter

# --- Configuration ---
PDF_PATH = "book/Howse-Joshi-Beyeler_opencv_computer_vision_projects_with_python.pdf" # Make sure this path is correct
OUTPUT_DIR = "processed_book"
IMAGE_DIR = os.path.join(OUTPUT_DIR, "images")
TEXT_DIR = os.path.join(OUTPUT_DIR, "texts")
METADATA_PATH = os.path.join(OUTPUT_DIR, "metadata.json")

DB_PATH = "chroma_db"
TEXT_COLLECTION_NAME = "cv_book_texts"
IMAGE_COLLECTION_NAME = "cv_book_images"

def process_pdf():
    # (This is the exact code from your first script)
    print(f"Starting PDF processing for: {PDF_PATH}")
    os.makedirs(IMAGE_DIR, exist_ok=True)
    os.makedirs(TEXT_DIR, exist_ok=True)
    try:
        doc = fitz.open(PDF_PATH)
    except Exception as e:
        print(f"Error opening PDF file: {e}")
        return False
    
    metadata = []
    print(f"PDF has {len(doc)} pages.")
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        page_label = page_num + 1
        pix = page.get_pixmap(dpi=150)
        image_path = os.path.join(IMAGE_DIR, f"page_{page_label}.png")
        pix.save(image_path)
        text = page.get_text()
        text_path = os.path.join(TEXT_DIR, f"page_{page_label}.txt")
        with open(text_path, "w", encoding="utf-8") as text_file:
            text_file.write(text)
        metadata.append({"page": page_label, "image_path": image_path, "text_path": text_path})
        if page_label % 20 == 0:
            print(f"Processed page {page_label}/{len(doc)}")

    with open(METADATA_PATH, "w") as f:
        json.dump(metadata, f, indent=4)
    print(f"Successfully processed {len(doc)} pages.")
    return True


def create_and_store_embeddings():
    # (This is the exact code from your second script)
    print("\nStarting embedding process...")
    client = chromadb.PersistentClient(path=DB_PATH)
    embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    
    text_collection = client.get_or_create_collection(name=TEXT_COLLECTION_NAME, embedding_function=embedding_func, metadata={"hnsw:space": "cosine"})
    image_collection = client.get_or_create_collection(name=IMAGE_COLLECTION_NAME, embedding_function=embedding_func, metadata={"hnsw:space": "cosine"})
    
    with open(METADATA_PATH, "r") as f:
        metadata = json.load(f)

    print("\n--- Embedding Text Chunks ---")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    all_chunks, all_chunk_metadata = [], []

    for item in metadata:
        with open(item['text_path'], 'r', encoding='utf-8') as f:
            page_text = f.read()
        if not page_text.strip(): continue
        chunks = text_splitter.split_text(page_text)
        for chunk in chunks:
            all_chunks.append(chunk)
            all_chunk_metadata.append({"source_page": item['page'], "image_path": item['image_path']})

    batch_size = 100
    for i in range(0, len(all_chunks), batch_size):
        text_collection.add(
            documents=all_chunks[i:i+batch_size],
            metadatas=all_chunk_metadata[i:i+batch_size],
            ids=[f"text_{i+j}" for j in range(len(all_chunks[i:i+batch_size]))]
        )
        print(f"Added batch {i//batch_size + 1} of text chunks.")

    print("\n--- Embedding Image Paths ---")
    image_paths = [item['image_path'] for item in metadata]
    image_metadatas = [{"source_page": item['page']} for item in metadata]
    image_ids = [f"image_{item['page']}" for item in metadata]
    image_collection.add(documents=image_paths, metadatas=image_metadatas, ids=image_ids)
    
    print("-" * 50)
    print("Embedding process complete.")
    print(f"Total text chunks: {text_collection.count()}, Total images: {image_collection.count()}")

if __name__ == "__main__":
    if not os.path.exists(PDF_PATH):
        print(f"ERROR: Book not found at {PDF_PATH}. Please place your PDF there.")
    else:
        if process_pdf():
            create_and_store_embeddings()