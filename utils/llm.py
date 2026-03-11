"""Shared LLM client using Ollama via the OpenAI-compatible API."""

import json
import os
import re

from openai import OpenAI

DEFAULT_MODEL = os.getenv("LLM_MODEL", "llama3.1:8b-instruct")

client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")


def chat(system: str, user: str, model: str | None = None) -> str:
    """Send a system+user message pair to the LLM and return the response text."""
    model_to_use = model or DEFAULT_MODEL
    response = client.chat.completions.create(
        model=model_to_use,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return response.choices[0].message.content


def safe_parse_json(text: str) -> dict:
    """Parse JSON from LLM output, handling markdown fences and extra text."""
    text = text.strip()
    text = re.sub(r"^```json\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise
