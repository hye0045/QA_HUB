import numpy as np
import re
from typing import List, Tuple
from sentence_transformers import SentenceTransformer

# 1. Global Local Embedding Model
# This will be loaded into RAM when the FastAPI app starts
print("Loading Local Embedding Model: all-MiniLM-L6-v2 ...")
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

def get_embedding(text: str) -> List[float]:
    """
    Generate a vector embedding using the local sentence-transformer model.
    Returns a Python list of floats that can be stored natively in Postgres JSONB.
    """
    if not text.strip():
        return []
    vector = embedding_model.encode(text)
    return vector.tolist()

# 2. In-Memory Cosine Similarity Calculation
def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate the cosine similarity between two vectors."""
    if not vec1 or not vec2:
        return -1.0
    
    a = np.array(vec1)
    b = np.array(vec2)
    
    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    
    if norm_a == 0 or norm_b == 0:
        return -1.0
        
    return float(dot_product / (norm_a * norm_b))

def retrieve_top_k_similar(query_text: str, candidates: List[dict], k: int = 3, threshold: float = 0.3) -> List[dict]:
    """
    Search against candidate objects (which must have an 'embedding' key with a float list).
    Returns top-k candidates passing the threshold.
    """
    query_vector = get_embedding(query_text)
    if not query_vector:
        return []
        
    scored_candidates = []
    for cand in candidates:
        if cand.get("embedding"):
            sim = cosine_similarity(query_vector, cand["embedding"])
            if sim >= threshold:
                scored_candidates.append((sim, cand))
                
    # Sort by similarity descending
    scored_candidates.sort(key=lambda x: x[0], reverse=True)
    
    # Return top K
    return [item[1] for item in scored_candidates[:k]]

# 3. Data Masking (Security)
def mask_sensitive_data(text: str) -> str:
    """
    Hide sensitive patterns before sending to Cloud APIs.
    """
    if not text:
        return text
        
    # Mask Emails
    email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    text = re.sub(email_pattern, '[MASKED_EMAIL]', text)
    
    # Mask Potential Phone Numbers (simple logic)
    phone_pattern = r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'
    text = re.sub(phone_pattern, '[MASKED_PHONE]', text)
    
    # Mask specific internal identifiers like Thundersoft secret codes if any exist
    # (Example custom rule)
    secret_code_pattern = r'\bTS-[A-Z0-9]{8}\b'
    text = re.sub(secret_code_pattern, '[MASKED_CODE]', text)
    
    return text
