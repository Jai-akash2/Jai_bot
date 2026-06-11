import os
import uuid
from datetime import datetime
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
import threading
from notification.notifier import check_and_notify

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
        groq_key = os.getenv("GROQ_API_KEY")
        or_key = os.getenv("OPENROUTER_API_KEY")
        model = os.getenv("OPENROUTER_MODEL", "openrouter/free")
        if not groq_key and not or_key:
            raise ValueError("No API key set (GROQ_API_KEY or OPENROUTER_API_KEY)")
        _agent = create_mentor_agent(
            groq_api_key=groq_key or "",
            openrouter_api_key=or_key or "",
            model=model,
        )
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


@app.get("/api/notifications/check")
async def check_notifications():
    alerts = []
    tasks = db.list_tasks("pending")
    today = datetime.now().strftime("%Y-%m-%d")
    due = [t for t in tasks if t["deadline"] == today]
    overdue = [t for t in tasks if t["deadline"] and t["deadline"] < today]
    return {
        "alerts": alerts,
        "due_today": [t["title"] for t in due],
        "overdue": [t["title"] for t in overdue],
    }


# --- Notes API ---

class NotePayload(BaseModel):
    title: str
    content: str
    tags: str = ""


@app.get("/api/notes")
async def list_notes(q: str = ""):
    if q:
        return db.search_notes(q)
    return db.get_all_notes()


@app.post("/api/notes")
async def create_note(payload: NotePayload):
    note_id = db.save_note(payload.title, payload.content, payload.tags)
    return {"id": note_id, "message": "Note saved"}


@app.delete("/api/notes/{note_id}")
async def delete_note(note_id: int):
    if db.delete_note(note_id):
        return {"message": "Deleted"}
    raise HTTPException(404, "Note not found")


# --- Tasks API ---

class TaskPayload(BaseModel):
    title: str
    description: str = ""
    deadline: str = ""
    priority: str = "medium"
    recurring: str = ""
    subtasks: str = ""


@app.get("/api/tasks")
async def list_tasks(status: str = ""):
    return db.list_tasks(status)


def _notify_task():
    try: check_and_notify()
    except: pass

@app.post("/api/tasks")
async def create_task(payload: TaskPayload):
    task_id = db.add_task(payload.title, payload.description, payload.deadline, payload.priority, payload.recurring, payload.subtasks)
    if payload.deadline:
        threading.Thread(target=_notify_task, daemon=True).start()
    return {"id": task_id, "message": "Task added"}


@app.put("/api/tasks/{task_id}/complete")
async def complete_task(task_id: int):
    if db.complete_task(task_id):
        return {"message": "Completed"}
    raise HTTPException(404, "Task not found")


@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: int):
    if db.delete_task(task_id):
        return {"message": "Deleted"}
    raise HTTPException(404, "Task not found")


# --- Progress API ---

class LearningPayload(BaseModel):
    topic: str
    summary: str = ""
    resource: str = ""
    time_spent: int = 0


@app.get("/api/progress")
async def get_progress():
    return db.get_learning_progress()


@app.post("/api/progress")
async def log_progress(payload: LearningPayload):
    log_id = db.log_learning(payload.topic, payload.summary, payload.resource, payload.time_spent)
    return {"id": log_id, "message": "Progress logged"}