import os
from typing import List, Optional
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent.mentor_agent import create_mentor_agent, format_history

load_dotenv()

app = FastAPI(title="DS Mentor Bot")

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
        agent = get_agent()
        history = format_history([msg.model_dump() for msg in request.history])

        result = await agent.ainvoke({
            "input": request.message,
            "chat_history": history,
        })

        return ChatResponse(
            response=result["output"],
            session_id=request.session_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health():
    return {"status": "ok"}