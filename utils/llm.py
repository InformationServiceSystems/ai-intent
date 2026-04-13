"""Shared LLM client using Ollama via the OpenAI-compatible API."""

import ast
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


def _sanitize_json_string(text: str) -> str:
    """Remove or escape control characters that break JSON parsing."""
    text = text.replace("\t", " ")
    # Remove ASCII control chars (0x00-0x1F) except \n, \r, \t
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    # Escape newlines only inside JSON string values, not structural newlines.
    # Strategy: process the text character by character, tracking whether we're
    # inside a quoted string.
    result = []
    in_string = False
    escape_next = False
    for ch in text:
        if escape_next:
            result.append(ch)
            escape_next = False
            continue
        if ch == '\\' and in_string:
            result.append(ch)
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            result.append(ch)
            continue
        if in_string and ch in ('\n', '\r'):
            result.append('\\n')
            continue
        result.append(ch)
    return ''.join(result)


def safe_parse_json(text: str) -> dict:
    """Parse JSON from LLM output, handling markdown fences, control chars, and extra text."""
    text = text.strip()
    text = re.sub(r"^```json\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try sanitizing control characters
        sanitized = _sanitize_json_string(text)
        try:
            return json.loads(sanitized)
        except json.JSONDecodeError:
            pass
        # Try Python literal eval for single-quoted dicts (common llama3.1 issue)
        # ast.literal_eval handles {'key': 'value'} without corrupting apostrophes
        for candidate in (text, sanitized):
            try:
                obj = ast.literal_eval(candidate)
                if isinstance(obj, dict):
                    return obj
            except (ValueError, SyntaxError):
                pass
        # Try extracting just the JSON object
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            extracted = match.group()
            try:
                return json.loads(extracted)
            except json.JSONDecodeError:
                pass
            try:
                sanitized_match = _sanitize_json_string(extracted)
                return json.loads(sanitized_match)
            except json.JSONDecodeError:
                pass
            # Try literal_eval on extracted object too
            try:
                obj = ast.literal_eval(extracted)
                if isinstance(obj, dict):
                    return obj
            except (ValueError, SyntaxError):
                pass
        raise
