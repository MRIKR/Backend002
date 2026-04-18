from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from app.routes import sales  # noqa: E402

app = FastAPI(title="TehBotol ERP Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://localhost:5173",
        "https://tehbotol-erp-flow.lovable.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sales.router, prefix="/api")


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "tehbotol-erp-backend"}
