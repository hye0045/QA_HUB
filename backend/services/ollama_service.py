import httpx
import logging
from typing import Optional
from core.config import settings

logger = logging.getLogger("qa_hub.ollama")


class OllamaClient:
    """Client tương tác với Ollama local LLM."""

    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL
        self.timeout = 300

    def is_available(self) -> bool:
        """Check nếu Ollama server đang chạy."""
        try:
            with httpx.Client(timeout=5) as client:
                response = client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False

    def is_model_ready(self) -> bool:
        """Check nếu model đã được pull về và sẵn sàng dùng."""
        try:
            with httpx.Client(timeout=5) as client:
                response = client.get(f"{self.base_url}/api/tags")
                if response.status_code != 200:
                    return False
                data = response.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                # So sánh linh hoạt (tên có thể kèm tag như :latest)
                model_base = self.model.split(":")[0]
                for m in models:
                    if m == self.model or m.startswith(model_base + ":"):
                        return True
                return False
        except Exception:
            return False

    def get_available_models(self) -> list:
        """Trả về danh sách tên model đã cài."""
        try:
            with httpx.Client(timeout=5) as client:
                response = client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    return [m.get("name", "") for m in response.json().get("models", [])]
        except Exception:
            pass
        return []

    def get_status_message(self) -> str:
        """Tạo thông báo trạng thái rõ ràng cho người dùng."""
        if not self.is_available():
            return (
                f"🔴 Ollama server chưa chạy tại {self.base_url}. "
                "Hãy mở terminal và chạy: ollama serve"
            )
        models = self.get_available_models()
        if not models:
            return (
                f"🟡 Ollama đang chạy nhưng chưa có model nào. "
                f"Hãy chạy: ollama pull {self.model}"
            )
        if not self.is_model_ready():
            return (
                f"🟡 Model '{self.model}' chưa được cài. "
                f"Các model có sẵn: {', '.join(models)}. "
                f"Hãy chạy: ollama pull {self.model}"
            )
        return f"🟢 Ollama sẵn sàng với model '{self.model}'"

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate text từ Ollama với error message rõ ràng."""
        if not self.is_available():
            raise RuntimeError(
                f"Ollama server không chạy tại {self.base_url}. "
                "Hãy mở terminal và chạy: ollama serve"
            )

        if not self.is_model_ready():
            available = self.get_available_models()
            hint = (
                f"Các model có sẵn: {', '.join(available)}" if available
                else f"Chưa có model nào. Hãy chạy: ollama pull {self.model}"
            )
            raise RuntimeError(
                f"Model '{self.model}' chưa được cài đặt. {hint}"
            )

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.2},
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
                return data.get("message", {}).get("content", "")
        except httpx.HTTPStatusError as e:
            logger.error(f"[Ollama] HTTP error {e.response.status_code}: {e.response.text}")
            raise RuntimeError(
                f"Ollama trả về lỗi {e.response.status_code}. "
                f"Chi tiết: {e.response.text[:200]}"
            )
        except httpx.TimeoutException:
            raise RuntimeError(
                f"Ollama timeout sau {self.timeout}s. "
                "Model có thể đang khởi động lần đầu, thử lại sau vài giây."
            )


ollama_client = OllamaClient()
