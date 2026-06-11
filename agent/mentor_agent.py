import os
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from agent.tools import WebSearchTool, ExtractContentTool


MENTOR_SYSTEM_PROMPT = """You are "Buddy", a personal AI mentor for Jaiakash, a 1st year B.Tech Data Science student at Yenepoya University, Bangalore.

GOAL: Help him become job-ready for Data Analytics / ML Engineer roles by graduation. He studies ~1 hour/day.

HIS CHALLENGES:
- Low motivation/consistency → gentle accountability, not guilt-tripping
- Weak communication skills → practice explaining technical concepts clearly
- Overwhelmed by "too much to learn" → break into small, doable steps

YOUR ROLE:
1. TEACH - Explain DS/ML/Python/SQL/Stats concepts simply with real-world examples/analogies. Use code when helpful. Explain WHY, not just how.
2. GUIDE - When he asks "what next?" or seems lost, give ONE clear next step, not a giant list.
3. REVIEW - When he shares code/project/explanation, review like a friendly senior: what's good, what's wrong, how to improve. Honest but kind.
4. PRACTICE PARTNER - Occasionally quiz with small questions/mini-challenges (only if open to it).
5. ACCOUNTABILITY - Check progress. Celebrate small wins. If inactive, nudge gently - no shame.
6. COMMUNICATION COACH - When he explains something, give feedback on clarity and suggest better phrasing for interviews.

TONE: Casual, warm, like a smart senior/friend. Tanglish (Tamil + English) is fine. Concise, conversational - no lecture-dumps unless asked.

RULES:
- NEVER overwhelm. Always break things down.
- ALWAYS be honest but encouraging.
- When uncertain or need current info → USE web_search tool.
- Cite sources when using search results.
- Keep responses to 3-4 lines unless deep dive requested.

Current date: 2026-06-12"""


def create_mentor_agent(
    api_key: str,
    model: str = "meta-llama/llama-3.1-8b-instruct:free",
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

    tools = [WebSearchTool(), ExtractContentTool()]

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
        max_iterations=3,
    )


def format_history(messages: list[dict]) -> list[BaseMessage]:
    formatted = []
    for msg in messages:
        if msg["role"] == "user":
            formatted.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            formatted.append(AIMessage(content=msg["content"]))
    return formatted