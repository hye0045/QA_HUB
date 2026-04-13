from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings
from api import testcases, specs, defects, delivery, chat

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="QA HUB API backend managing Specs, Testcases, Defects, and AI Chatbot integrations.",
    version="1.0.0"
)

# CORS configuration for Frontend and Extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict to frontend & extension domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Welcome to QA HUB API"}

app.include_router(testcases.router, prefix="/api")
app.include_router(specs.router, prefix="/api")
app.include_router(defects.router, prefix="/api")
app.include_router(delivery.router, prefix="/api")
app.include_router(chat.router, prefix="/api")

