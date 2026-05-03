import numpy as np
import re
import os
import logging
from typing import List, Tuple, Optional
from sentence_transformers import SentenceTransformer

logger_embed = logging.getLogger("qa_hub.ai_service.embed")

# 1. Lazy-loaded Local Embedding Model
# Chỉ tải model khi thực sự cần dùng, tránh crash khi khởi động
_embedding_model: Optional[SentenceTransformer] = None

def _get_embedding_model() -> Optional[SentenceTransformer]:
    """Lazy loader cho embedding model. Ưu tiên load từ cache local."""
    global _embedding_model
    if _embedding_model is not None:
        return _embedding_model
    
    try:
        # Thử load từ cache local trước (không cần internet)
        _embedding_model = SentenceTransformer(
            "all-MiniLM-L6-v2",
            local_files_only=True
        )
        logger_embed.info("[Embedding] Model loaded from local cache.")
    except Exception as e1:
        logger_embed.warning(f"[Embedding] Local cache load failed: {e1}. Trying online download...")
        try:
            _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
            logger_embed.info("[Embedding] Model downloaded and loaded successfully.")
        except Exception as e2:
            logger_embed.error(f"[Embedding] Cannot load model (offline + download failed): {e2}")
            _embedding_model = None  # Backend vẫn hoạt động, chỉ tắt tính năng embedding
    
    return _embedding_model

def get_embedding(text: str) -> List[float]:
    """
    Generate a vector embedding using the local sentence-transformer model.
    Returns a Python list of floats that can be stored natively in Postgres JSONB.
    """
    if not text.strip():
        return []
    model = _get_embedding_model()
    if model is None:
        logger_embed.warning("[Embedding] Model unavailable. Returning empty vector.")
        return []
    vector = model.encode(text)
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

# 4. Ollama LLM Integration
import json
import logging
from core.config import settings
from services.ollama_service import ollama_client

logger = logging.getLogger("qa_hub.ai_service")

async def call_llm(prompt: str, system_prompt: str = "You are helpful.") -> str:
    """Gọi Ollama local LLM. Raise RuntimeError nếu Ollama không chạy."""
    if not ollama_client.is_available():
        raise RuntimeError(
            f"Ollama server không chạy tại {ollama_client.base_url}. "
            "Hãy mở terminal và chạy: ollama serve"
        )
    return await ollama_client.generate(prompt, system_prompt)


async def clean_and_classify_bug(bug_subject: str, bug_description: str) -> dict:
    """
    Sử dụng Ollama AI để làm sạch mô tả Bug và phân loại thành JSON.
    """
    masked_desc = mask_sensitive_data(bug_description)
    masked_subj = mask_sensitive_data(bug_subject)

    prompt = f"""Bạn là chuyên gia QA. Đọc Bug thô, làm sạch text, tóm tắt và phân loại lỗi.
Bug Subject: {masked_subj}
Bug Description: {masked_desc}

YÊU CẦU:
1. `cleaned_description`: Viết lại Description gọn gàng, chia bullet point, lịch sự, chuẩn mực QA (loại bỏ cảm xúc, phàn nàn của Tester). BẮT BUỘC KHÔNG VIẾT CHỮ "N/A" hay để trống, hãy sáng tạo lại nội dung thành các bước chuyên nghiệp: "Steps to reproduce", "Actual result", "Expected result".
2. `bug_category`: Chọn chuẩn xác 1 trong: 'UI', 'Logic', 'Crash', 'Performance', 'Security', 'Hardware', 'Other'.
3. `root_cause_guess`: Dự đoán nguyên nhân kỹ thuật dưới góc độ Coder.
4. `module`: Tên chức năng/khu vực code có thể dính lỗi.

Trả về ĐÚNG định dạng JSON sau (không kèm text thừa):
{{"cleaned_description": "mo ta ngan gon...", "bug_category": "UI/Logic/Crash...", "root_cause_guess": "du doan nguyen nhan...", "module": "ten module..."}}"""

    try:
        response = await call_llm(prompt, system_prompt="Bạn là chuyên gia QA. Hãy xuất ra JSON hợp lệ.")
        return json.loads(response)
    except Exception as e:
        logger.error(f"[AI Service] classify_bug failed: {e}", exc_info=True)
        return {
            "cleaned_description": f"[{masked_subj}] {masked_desc[:100]}",
            "bug_category": "Error",
            "root_cause_guess": f"AI không khả dụng: {str(e)}",
            "module": "Unknown"
        }



