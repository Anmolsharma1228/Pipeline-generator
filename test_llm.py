from llm.llm_parser import normalize_prompt

prompt = "Read empdata1.xlsx Sheet1 keep only fullname and salary and save output.csv"

print(normalize_prompt(prompt))