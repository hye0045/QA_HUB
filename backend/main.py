import time
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from core.config import settings
from api import testcases, testcases_upload, specs, defects, delivery, chat, auth, users

# -------------------------------------------------------------------
# Logging setup
# -------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("qa_hub")


# -------------------------------------------------------------------
# Audit/Request logging middleware
# -------------------------------------------------------------------
class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start
        logger.info(
            f"{request.method} {request.url.path} "
            f"status={response.status_code} "
            f"duration={duration:.3f}s "
            f"client={request.client.host if request.client else 'unknown'}"
        )
        return response


# -------------------------------------------------------------------
# FastAPI app
# -------------------------------------------------------------------
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="QA HUB API backend managing Specs, Testcases, Defects, and AI Chatbot integrations.",
    version="1.0.0",
)

# Whitelist cụ thể - KHÔNG dùng ["*"] trong production
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://qa-hub.thundersoft.vn",
    "https://extension.thundersoft.vn",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(LoggingMiddleware)


# -------------------------------------------------------------------
# Routes
# -------------------------------------------------------------------
@app.get("/")
def root():
    return {"message": "Welcome to QA HUB API"}


@app.get("/api/ai/status")
def ai_status():
    """Kiểm tra trạng thái Ollama và model. Frontend gọi để hiển thị thông báo."""
    from services.ollama_service import ollama_client
    server_up = ollama_client.is_available()
    model_ready = ollama_client.is_model_ready() if server_up else False
    return {
        "server_running": server_up,
        "model_ready": model_ready,
        "model_name": ollama_client.model,
        "base_url": ollama_client.base_url,
        "available_models": ollama_client.get_available_models() if server_up else [],
        "status_message": ollama_client.get_status_message(),
        "ai_features_enabled": model_ready,
    }


app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(testcases.router, prefix="/api")
app.include_router(testcases_upload.router, prefix="/api")
app.include_router(specs.router, prefix="/api")
app.include_router(defects.router, prefix="/api")
app.include_router(delivery.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
