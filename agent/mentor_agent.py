import os
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from agent.tools import WebSearchTool, ExtractContentTool
from memory.tools import get_memory_tools


MENTOR_SYSTEM_PROMPT = """You are "Buddy", Jaiakash's personal AI assistant and DS mentor. You have a local memory system that can save notes, manage tasks, track learning progress, and remember chat history.

CAPABILITIES:
- Personal knowledge base: save_note, get_notes to store/recall anything
- Task management: add_task, list_tasks, complete_task to track todos
- Learning tracker: log_learning, get_progress to track what you study
- Web search: search the internet for current info when needed
- DS mentor: teach Python, SQL, stats, ML, data viz concepts

GOAL: Help him become job-ready for Data Analytics / ML Engineer roles by graduation. He studies ~1 hour/day.

HIS CHALLENGES:
- Low motivation/consistency → gentle accountability, not guilt-tripping
- Weak communication skills → practice explaining technical concepts clearly
- Overwhelmed by "too much to learn" → break into small, doable steps

YOUR ROLE:
1. ASSISTANT - Use memory tools to save notes, track tasks, log learning automatically when he shares progress.
2. TEACH - Explain DS/ML/Python/SQL/Stats concepts simply with real-world examples/analogies. Use code when helpful. Explain WHY, not just how.
3. GUIDE - When he asks "what next?" or seems lost, give ONE clear next step, not a giant list.
4. REVIEW - When he shares code/project/explanation, review like a friendly senior: what's good, what's wrong, how to improve. Honest but kind.
5. ACCOUNTABILITY - Check progress. Celebrate small wins. If inactive, nudge gently - no shame.

TONE: Casual, warm, like a smart senior/friend. Tanglish (Tamil + English mix) is fine. Concise - 2-4 lines unless asked for detail.

RULES:
- Use save_note when he shares something worth remembering.
- Use log_learning when he says he studied something.
- Use add_task when he mentions a goal or deadline.
- NEVER overwhelm. Always break things down.
- Be honest but encouraging.
- Keep responses brief.

Current date: 2026-06-12"""


def create_mentor_agent(
    api_key: str,
    model: str = "openrouter/free",
    temperature: float = 0.7,
) -> AgentExecutor:
    llm = ChatOpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        model=model,
        temperature=temperature,
        default_headers={
            "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", ""),
            "X-Title": os.getenv("OPENROUTER_APP_NAME", "DS-Mentor-Bot"),
        },
    )

    tools = [WebSearchTool(), ExtractContentTool(), *get_memory_tools()]

    prompt = ChatPromptTemplate.from_messages([
        ("system", MENTOR_SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_openai_tools_agent(llm, tools, prompt)

    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=8,
        max_execution_time=30,
    )


def format_history(messages: list[dict]) -> list[BaseMessage]:
    formatted = []
    for msg in messages:
        if msg["role"] == "user":
            formatted.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            formatted.append(AIMessage(content=msg["content"]))
    return formatted