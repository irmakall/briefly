"""The agent loop: the model decides which tools to call, we run them (FR-12 to FR-15)."""
import json
import logging
import time
from dataclasses import dataclass

from google import genai
from google.genai import types

from agent.prompts import SYSTEM_INSTRUCTION, WRITE_BULLETIN, build_task
from agent.schema import Bulletin
from tools.finance import get_market_rates, get_stock_info
from tools.news import get_financial_news, get_tech_news

logger = logging.getLogger(__name__)

MAX_STEPS = 10  # FR-14

# NFR-4: to add a tool, write the function and add it to this list.
TOOLS = [get_tech_news, get_stock_info, get_financial_news, get_market_rates]
TOOLS_BY_NAME = {tool.__name__: tool for tool in TOOLS}


class AgentError(Exception):
    """A critical failure: the agent could not produce a bulletin."""


@dataclass
class AgentResult:
    """What the agent hands back to main.py."""

    bulletin: Bulletin
    tool_calls: list[dict]  # every call: {"name", "args", "result"}; used for FR-20/21


def run_tool(name: str, args: dict) -> dict:
    """Run one tool by name and log it (FR-15). Never raises (FR-10)."""
    tool = TOOLS_BY_NAME.get(name)
    if tool is None:
        return {"error": f"Unknown tool: {name}"}

    start = time.perf_counter()
    try:
        result = tool(**args)
    except Exception as exc:
        result = {"error": f"{name} failed ({type(exc).__name__})."}
    seconds = time.perf_counter() - start

    status = "FAILED" if "error" in result else "ok"
    logger.info("%s(%s) -> %s in %.1fs", name, args, status, seconds)
    return result


def collect_data(client: genai.Client, model: str, tickers: list[str]) -> list[dict]:
    """Phase 1: let the model call tools until it says it's done."""
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        tools=TOOLS,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),  # FR-13
    )
    contents = [types.Content(role="user", parts=[types.Part(text=build_task(tickers))])]
    tool_calls = []

    for step in range(1, MAX_STEPS + 1):
        response = client.models.generate_content(model=model, contents=contents, config=config)
        contents.append(response.candidates[0].content)

        if not response.function_calls:
            logger.info("Model finished collecting after %d step(s).", step)
            break

        result_parts = []
        for call in response.function_calls:
            args = dict(call.args or {})
            result = run_tool(call.name, args)
            tool_calls.append({"name": call.name, "args": args, "result": result})
            result_parts.append(types.Part.from_function_response(name=call.name, response=result))
        contents.append(types.Content(role="user", parts=result_parts))
    else:
        logger.warning("Step limit (%d) reached; writing with the data collected so far.", MAX_STEPS)

    return tool_calls


def write_bulletin(client: genai.Client, model: str, tool_calls: list[dict]) -> Bulletin:
    """Phase 2: one request that turns the collected data into a Bulletin (FR-19)."""
    data = json.dumps(tool_calls, ensure_ascii=False, indent=1)
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        response_mime_type="application/json",
        response_schema=Bulletin,
    )
    response = client.models.generate_content(
        model=model, contents=f"{WRITE_BULLETIN}\nData:\n{data}", config=config
    )

    if isinstance(response.parsed, Bulletin):
        return response.parsed
    try:
        return Bulletin.model_validate_json(response.text or "")
    except ValueError as exc:
        raise AgentError("The model did not return a valid bulletin.") from exc


def run_agent(client: genai.Client, model: str, tickers: list[str]) -> AgentResult:
    """Run both phases and return the bulletin plus the raw tool results."""
    tool_calls = collect_data(client, model, tickers)
    if not tool_calls:
        raise AgentError("The model did not call any tools.")
    bulletin = write_bulletin(client, model, tool_calls)
    return AgentResult(bulletin=bulletin, tool_calls=tool_calls)
