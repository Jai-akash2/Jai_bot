import os
from dotenv import load_dotenv
from agent.mentor_agent import create_mentor_agent
from agent.mentor_agent import format_history

load_dotenv()


def main():
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ OPENROUTER_API_KEY not set in .env")
        print("   Copy .env.example to .env and add your key")
        return

    model = os.getenv("OPENROUTER_MODEL", "qwen/qwen3-coder:free")
    agent = create_mentor_agent(api_key, model)

    print(f"\n{'='*50}")
    print("🧠 Buddy - DS Mentor Bot")
    print("Type 'exit' to quit, 'clear' to reset history")
    print(f"Model: {model}")
    print(f"{'='*50}\n")

    history = []

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye! Keep learning! 👋")
            break

        if user_input.lower() in ("exit", "quit"):
            print("Bye! Keep learning! 👋")
            break
        if user_input.lower() == "clear":
            history = []
            print("🧹 History cleared.\n")
            continue
        if not user_input:
            continue

        result = agent.invoke({
            "input": user_input,
            "chat_history": format_history(history),
        })

        response = result["output"]
        print(f"\nBuddy: {response}\n")

        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": response})


if __name__ == "__main__":
    main()