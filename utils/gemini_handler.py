import os
import re
from google import genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError(
        "GEMINI_API_KEY not found in .env file"
    )

client = genai.Client(api_key=api_key)

MODEL = "gemini-2.5-flash"



def generate_answer(prompt: str):
    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config={
                "temperature": 0.4
            }
        )
        return response.text

    except Exception as e:
        print(f"Gemini Error: {e}")
        return "Failed to generate answer."


def generate_sql(prompt: str):
    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config={
                "temperature": 0.0
            }
        )
        return response.text

    except Exception as e:
        print(f"Gemini Error: {e}")
        return ""


def generate_sql_from_query(user_query: str, table_schema: str):
    prompt = f"""
        You are an expert SQLite query generator.

        Database Schema:
        {table_schema}

        Convert the following natural language request into a valid SQLite query.

        Rules:
        1. Return ONLY the SQL query.
        2. Do not provide explanations.
        3. Do not use markdown code blocks.
        4. Use exact table names from the schema.
        5. SQLite syntax only.

        User Request:
        {user_query}
    """

    sql = generate_sql(prompt)

    if not sql:
        return ""

    # Remove markdown if Gemini adds it
    sql = re.sub(
        r"```sql|```",
        "",
        sql,
        flags=re.IGNORECASE
    ).strip()

    sql = re.sub(
        r"```(?:sql)?|```",
        "",
        sql,
        flags=re.IGNORECASE
    ).strip()

    if not sql.endswith(";"):
        sql += ";"

    return sql


def classify_query(query: str):
    try:
        prompt = f"""
            Classify the user query.

            Return ONLY:

            SQL
            or
            DOCUMENT

            Examples:

            Show all rows -> SQL
            Count records -> SQL
            Average sales -> SQL
            Top 10 products -> SQL

            Summarize the report -> DOCUMENT
            Explain the findings -> DOCUMENT
            What is the conclusion -> DOCUMENT

            User Query:
            {query}
        """

        response = client.models.generate_content(
            model=MODEL,
            contents=prompt
        )

        result = response.text.strip().upper()

        if "SQL" in result:
            return "SQL"

        return "DOCUMENT"

    except Exception as e:
        print(f"Classification Error: {e}")

        return "DOCUMENT"


