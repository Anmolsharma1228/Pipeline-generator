import os
import re
from google import genai
from dotenv import load_dotenv

from llm.prompt import SYSTEM_PROMPT

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

MODEL_NAME = "gemini-2.5-flash"


def normalize_prompt(user_prompt):

    response = client.models.generate_content(
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