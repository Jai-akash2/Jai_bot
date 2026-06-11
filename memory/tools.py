from typing import Type, Optional
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
from memory import db


# --- Note Tools ---

class SaveNoteInput(BaseModel):
    title: str = Field(description="Title of the note")
    content: str = Field(description="Content of the note")
    tags: str = Field(default="", description="Optional comma-separated tags")


class SaveNoteTool(BaseTool):
    name: str = "save_note"
    description: str = "Save a note or idea to your personal knowledge base. Use this when you learn something new or want to remember something."
    args_schema: Type[BaseModel] = SaveNoteInput

    def _run(self, title: str, content: str, tags: str = "") -> str:
        note_id = db.save_note(title, content, tags)
        return f"Saved note '{title}' (id: {note_id})"

    async def _arun(self, title: str, content: str, tags: str = "") -> str:
        return self._run(title, content, tags)


class GetNotesInput(BaseModel):
    query: Optional[str] = Field(default="", description="Optional search query to filter notes")


class GetNotesTool(BaseTool):
    name: str = "get_notes"
    description: str = "Retrieve notes from your knowledge base. Optionally search by keyword."
    args_schema: Type[BaseModel] = GetNotesInput

    def _run(self, query: str = "") -> str:
        if query:
            notes = db.search_notes(query)
        else:
            notes = db.get_all_notes()

        if not notes:
            return "No notes found."

        lines = []
        for n in notes[:5]:
            lines.append(f"[{n['id']}] {n['title']}\n{n['content'][:200]}\nTags: {n['tags']}")
        return "\n\n".join(lines)

    async def _arun(self, query: str = "") -> str:
        return self._run(query)


# --- Task Tools ---

class AddTaskInput(BaseModel):
    title: str = Field(description="Task title")
    description: str = Field(default="", description="Optional description")
    deadline: str = Field(default="", description="Optional deadline (YYYY-MM-DD)")
    priority: str = Field(default="medium", description="Priority: high, medium, or low")


class AddTaskTool(BaseTool):
    name: str = "add_task"
    description: str = "Add a new task or todo item to your task list."
    args_schema: Type[BaseModel] = AddTaskInput

    def _run(self, title: str, description: str = "", deadline: str = "", priority: str = "medium") -> str:
        task_id = db.add_task(title, description, deadline, priority)
        return f"Added task '{title}' (id: {task_id})"

    async def _arun(self, title: str, description: str = "", deadline: str = "", priority: str = "medium") -> str:
        return self._run(title, description, deadline, priority)


class ListTasksInput(BaseModel):
    status: str = Field(default="", description="Filter: 'pending', 'completed', or empty for all")


class ListTasksTool(BaseTool):
    name: str = "list_tasks"
    description: str = "List all tasks. Optional filter by status (pending/completed)."
    args_schema: Type[BaseModel] = ListTasksInput

    def _run(self, status: str = "") -> str:
        tasks = db.list_tasks(status)
        if not tasks:
            return "No tasks found."
        lines = []
        for t in tasks:
            status_icon = "[x]" if t["status"] == "completed" else "[ ]"
            deadline = f" (due: {t['deadline']})" if t["deadline"] else ""
            lines.append(f"{status_icon} [{t['id']}] {t['title']}{deadline}")
        return "\n".join(lines)

    async def _arun(self, status: str = "") -> str:
        return self._run(status)


class CompleteTaskInput(BaseModel):
    task_id: str = Field(description="ID of the task to mark complete (number)")


class CompleteTaskTool(BaseTool):
    name: str = "complete_task"
    description: str = "Mark a task as completed by its ID."
    args_schema: Type[BaseModel] = CompleteTaskInput

    def _run(self, task_id: str) -> str:
        tid = int(task_id)
        if db.complete_task(tid):
            return f"Task {tid} marked completed."
        return f"Task {tid} not found."

    async def _arun(self, task_id: str) -> str:
        return self._run(task_id)


# --- Learning Log Tools ---

class LogLearningInput(BaseModel):
    topic: str = Field(description="The topic you studied")
    summary: str = Field(default="", description="Brief summary of what you learned")
    resource: str = Field(default="", description="Optional link/resource used")
    time_spent: str = Field(default="0", description="Minutes spent learning (number)")


class LogLearningTool(BaseTool):
    name: str = "log_learning"
    description: str = "Log what you learned today. Use this to track your learning progress over time."
    args_schema: Type[BaseModel] = LogLearningInput

    def _run(self, topic: str, summary: str = "", resource: str = "", time_spent: str = "0") -> str:
        mins = int(time_spent) if time_spent else 0
        log_id = db.log_learning(topic, summary, resource, mins)
        return f"Logged learning: {topic} (id: {log_id})"

    async def _arun(self, topic: str, summary: str = "", resource: str = "", time_spent: str = "0") -> str:
        return self._run(topic, summary, resource, time_spent)


class GetProgressTool(BaseTool):
    name: str = "get_progress"
    description: str = "Show your learning progress and history."
    args_schema: Type[BaseModel] = None

    def _run(self) -> str:
        logs = db.get_learning_progress()
        if not logs:
            return "No learning logged yet. Start learning and use log_learning to track progress!"
        lines = []
        for l in logs[:10]:
            time_str = f" ({l['time_spent']}min)" if l['time_spent'] else ""
            lines.append(f"[{l['created_at'][:10]}] {l['topic']}{time_str}")
            if l['summary']:
                lines.append(f"    {l['summary'][:100]}")
        return "\n".join(lines)

    async def _arun(self) -> str:
        return self._run()


def get_memory_tools() -> list[BaseTool]:
    return [
        SaveNoteTool(),
        GetNotesTool(),
        AddTaskTool(),
        ListTasksTool(),
        CompleteTaskTool(),
        LogLearningTool(),
        GetProgressTool(),
    ]