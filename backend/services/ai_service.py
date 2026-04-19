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

# 4. Groq LLM Integrations
from groq import AsyncGroq
import json
import logging
from core.config import settings

logger = logging.getLogger("qa_hub.ai_service")

async def clean_and_classify_bug(bug_subject: str, bug_description: str) -> dict:
    """
    Sử dụng Groq AI để làm sạch mô tả Bug và phân loại thành JSON.
    """
    if not settings.GROQ_API_KEY:
        logger.warning("[AI Service] GROQ_API_KEY missing. Returning mock classification.")
        return {
            "cleaned_description": f"[{bug_subject}] {bug_description[:50]}...",
            "bug_category": "Uncategorized",
            "root_cause_guess": "N/A",
            "module": "General"
        }
    
    client = AsyncGroq(api_key=settings.GROQ_API_KEY)
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
        chat_completion = await client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="qwen/qwen3-32b",
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        content = chat_completion.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        logger.error(f"[AI Service] classify_bug failed: {e}", exc_info=True)
        return {
            "cleaned_description": "AI Classification Failed. " + masked_subj,
            "bug_category": "Error",
            "root_cause_guess": "Error analyzing",
            "module": "Unknown"
        }

async def generate_testcases_from_spec(spec_content: str, base_model_testcases: list) -> dict:
    """
    Sử dụng Groq AI (Llama3-70b) để sinh Testcase Json Format dựa trên Specs 
    và các base rules truyền vào từ testcases trước đó.
    """
    if not settings.GROQ_API_KEY:
        logger.warning("[AI Service] GROQ_API_KEY missing. Returning mock array.")
        return {"testcases": []}
        
    client = AsyncGroq(api_key=settings.GROQ_API_KEY)
    masked_spec = mask_sensitive_data(spec_content)
    
    # Chuẩn bị context của Base models
    base_context = ""
    for tc in base_model_testcases:
        base_context += f"- Title: {tc.get('title')}\n  Precondition: {tc.get('precondition')}\n  Steps: {tc.get('steps')}\n  Expected: {tc.get('expected')}\n"

    system_prompt = f"""Bạn là Test Automation Engineer Senior của công ty Thundersoft.
Nhiệm vụ: Viết Testcases chất lượng cao cho Software Specification dưới đây.
HỌC HỎI văn phong và độ chi tiết từ các Testcase Base Model sau:
{base_context}

Yêu cầu output BẮT BUỘC trả về ĐÚNG ĐỊNH DẠNG JSON MẢNG OBJECT NHƯ SAU:
{{"testcases": [ {{"test_id": "1", "title": "Kiem tra chuc nang", "precondition": "Dieu kien", "steps": "Cac buoc...", "expected_result": "Ket qua..."}} ]}}
KHÔNG output markdown ````json hay bất kỳ chú thích nào khác."""

    try:
        chat_completion = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"SPECIFICATION:\n{masked_spec}"}
            ],
            model="qwen/qwen3-32b",
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        content = chat_completion.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        logger.error(f"[AI Service] generate_testcases failed: {e}", exc_info=True)
        return {"testcases": [{"test_id": "ERR-01", "title": "AI Error", "precondition": "", "steps": str(e), "expected_result": "Failed to generate"}]}
