import os
import re
from google import genai
from dotenv import load_dotenv

try:
    from llm.prompt import SYSTEM_PROMPT
except ModuleNotFoundError:
    from prompt import SYSTEM_PROMPT

load_dotenv()

MODEL_NAME = "gemini-3.6-flash"

_client = None


def _get_client():
    """
    Build the Gemini client lazily, on first use, instead of at
    import time. A missing/invalid GEMINI_API_KEY (or any other
    client-construction error) then only fails the individual
    request - it can't take down the whole app on startup.
    """

    global _client

    if _client is None:
        _client = genai.Client(
            api_key=os.getenv("GEMINI_API_KEY")
        )

    return _client


def normalize_prompt(user_prompt):

    response = _get_client().models.generate_content(
        model=MODEL_NAME,
        contents=(
            SYSTEM_PROMPT +
            "\n\nUser Prompt:\n" +
            user_prompt
        )
    )

    text = response.text.strip()

    # Remove markdown if Gemini returns it
    text = text.replace("```", "")
    text = text.replace("json", "")

    # Remove extra blank lines
    text = re.sub(r"\n+", "\n", text)

    return text.strip()