import os
import uuid
from typing import List, Optional
from dotenv import load_dotenv

from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from agent.mentor_agent import create_mentor_agent, format_history
from memory import db

load_dotenv()

app = FastAPI(title="DS Mentor Bot")

PUBLIC_DIR = Path(__file__).resolve().parent.parent / "public"
app.mount("/public", StaticFiles(directory=str(PUBLIC_DIR)), name="public")


@app.get("/")
async def serve_frontend():
    return FileResponse(str(PUBLIC_DIR / "index.html"))


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    session_id: Optional[str] = None


_agent = None


def get_agent():
    global _agent
    if _agent is None:
        api_key = os.getenv("OPENROUTER_API_KEY")
        model = os.getenv("OPENROUTER_MODEL", "openrouter/free")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not set")
        _agent = create_mentor_agent(api_key, model)
    return _agent


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        session_id = request.session_id or str(uuid.uuid4())[:8]

        db.save_chat_message(session_id, "user", request.message)

        saved = db.get_chat_history(session_id, limit=20)
        history = format_history(saved)

        agent = get_agent()
        result = await agent.ainvoke({
            "input": request.message,
            "chat_history": history,
        })

        response_text = result["output"]
        db.save_chat_message(session_id, "assistant", response_text)

        return ChatResponse(
            response=response_text,
            session_id=session_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health():
    return {"status": "ok"}