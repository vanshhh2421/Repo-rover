from __future__ import annotations

import json
import re
import traceback

from openai import OpenAI

from app.core.settings import settings
from app.infrastructure.neo4j_client import Neo4jClient
from app.query.tools import build_tools

SYSTEM_PROMPT = """You are RepoRover, an expert AI assistant for understanding codebases.

Available tools:
"""


def _build_system_prompt(tools) -> str:
    lines = [SYSTEM_PROMPT]
    for t in tools:
        lines.append(f"- `{t.name}`: {t.description}")
    lines.append(f"""
When you need to call a tool, output EXACTLY one line like this:

TOOL: {{"name": "tool_name", "arguments": {{"param1": "value1"}}}}

Then wait for the result. Call at most 3 tools. Once you have the information, answer directly.
""")
    return "\n".join(lines)


def _parse_tool_call(text: str):
    m = re.search(r"^TOOL:\s*(\{.*\})", text.strip(), re.MULTILINE | re.DOTALL)
    if not m:
        return None, None
    try:
        obj = json.loads(m.group(1))
        return obj.get("name"), obj.get("arguments", {})
    except json.JSONDecodeError:
        return None, None


async def run_agent_query(
    neo4j: Neo4jClient,
    repo_id: str,
    question: str,
) -> tuple[str, int]:
    if not settings.llm_api_key:
        return "LLM_API_KEY is missing. Set it in .env to enable answers.", 0

    tools = build_tools(neo4j, repo_id)
    system_prompt = _build_system_prompt(tools)

    client = OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)

    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]

    tool_call_count = 0
    max_tool_calls = 2

    try:
        for _ in range(max_tool_calls):
            response = client.chat.completions.create(
                model=settings.llm_model,
                messages=messages,
                temperature=0.2,
                max_tokens=2000,
            )

            content = response.choices[0].message.content or ""
            name, args = _parse_tool_call(content)

            if name is None:
                if content.strip():
                    return content, tool_call_count
                break

            messages.append({"role": "assistant", "content": content})
            tool_call_count += 1

            tool_fn = next((t for t in tools if t.name == name), None)
            if not tool_fn:
                result = f"Unknown tool: {name}"
            else:
                try:
                    result = tool_fn.invoke(args)
                except Exception as e:
                    result = f"Tool error: {e}"

            messages.append({"role": "user", "content": f"Tool result: {result}"})

        prompt = f"Based on the information above, answer this question concisely:\n\n{question}"
        messages.append({"role": "user", "content": prompt})
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            temperature=0.2,
            max_tokens=2000,
        )
        answer = response.choices[0].message.content or ""
        return answer, tool_call_count

    except Exception as e:
        traceback.print_exc()
        return f"Agent error: {e}", tool_call_count
