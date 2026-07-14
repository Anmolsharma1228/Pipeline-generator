import os
import re
import google.generativeai as genai
from dotenv import load_dotenv

from llm.prompt import SYSTEM_PROMPT

load_dotenv()

genai.configure(
    api_key=os.getenv("GEMINI_API_KEY")
)

model = genai.GenerativeModel(
    "gemini-2.5-flash"
)


def normalize_prompt(user_prompt):

    response = model.generate_content(
        SYSTEM_PROMPT +
        "\n\nUser Prompt:\n" +
        user_prompt
    )

    text = response.text.strip()

    # Remove markdown if Gemini returns it
    text = text.replace("```", "")
    text = text.replace("json", "")

    # Remove extra blank lines
    text = re.sub(r"\n+", "\n", text)

    return text.strip()