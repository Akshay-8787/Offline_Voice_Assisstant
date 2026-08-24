from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import List, Dict


OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "qwen2.5:3b"

SYSTEM_PROMPT = """
You are the AI brain of a personal desktop voice assistant.

Rules:
- Be helpful, concise, and natural.
- The user may speak English or Hinglish.
- Reply in the same language/style as the user when practical.
- Do not claim to have performed a computer action.
- Do not invent current information. Web access will be added separately later.
- Keep normal spoken answers reasonably short.
""".strip()


class AIBrain:
    def __init__(
        self,
        model: str = MODEL_NAME,
        max_history: int = 12,
    ) -> None:
        self.model = model
        self.max_history = max_history
        self.history: List[Dict[str, str]] = []

    def reset(self) -> None:
        """Clear the current conversation memory."""
        self.history.clear()

    def ask(self, user_text: str) -> str:
        """Send a message to the local Ollama model and return its answer."""
        user_text = user_text.strip()

        if not user_text:
            return "Please say something."

        messages: List[Dict[str, str]] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

        messages.extend(self.history[-self.max_history:])
        messages.append(
            {"role": "user", "content": user_text}
        )

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }

        request = urllib.request.Request(
            OLLAMA_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                data = json.loads(response.read().decode("utf-8"))

        except urllib.error.URLError as exc:
            raise RuntimeError(
                "Could not connect to Ollama. Make sure Ollama is running."
            ) from exc

        except TimeoutError as exc:
            raise RuntimeError(
                "The local AI took too long to respond."
            ) from exc

        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "Ollama returned an invalid response."
            ) from exc

        message = data.get("message", {})
        answer = str(message.get("content", "")).strip()

        if not answer:
            raise RuntimeError("The AI returned an empty response.")

        # Save conversation only after a successful response.
        self.history.append(
            {"role": "user", "content": user_text}
        )
        self.history.append(
            {"role": "assistant", "content": answer}
        )

        return answer


def main() -> None:
    print("Local AI Brain")
    print("----------------")
    print(f"Model: {MODEL_NAME}")
    print("Type 'exit' to quit or 'clear' to reset conversation.")
    print()

    brain = AIBrain()

    while True:
        try:
            user_text = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            break

        if not user_text:
            continue

        if user_text.lower() in {"exit", "quit", "bye"}:
            print("AI: Goodbye.")
            break

        if user_text.lower() in {"clear", "reset"}:
            brain.reset()
            print("AI: Conversation memory cleared.")
            continue

        try:
            answer = brain.ask(user_text)
            print(f"AI: {answer}")
        except Exception as exc:
            print(f"AI Error: {exc}")


if __name__ == "__main__":
    main()