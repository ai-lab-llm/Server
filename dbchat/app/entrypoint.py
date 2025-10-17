from __future__ import annotations
from typing import Any, Dict, List
import re
from dbchat.app.graph.workflow import run_graph  # LangGraph 실행기
# intent가 필요하면: from dbchat.app.utils.intent import classify_intent_llm, list_known_names

def _extract_final(messages: List[Any]) -> str:
    last = None
    for m in reversed(messages):
        c = getattr(m, "content", None)
        t = getattr(m, "type", None)
        if not c or not isinstance(c, str):
            continue
        if t == "ai" and c.startswith("Final:"):
            return re.sub(r"^Final:\s*", "", c, flags=re.S).strip()
        if t == "ai" and c.startswith("Answer:") and last is None:
            last = re.sub(r"^Answer:\s*", "", c, flags=re.S).strip()
    return last or "응답 없음"

def ask_once(question: str, recursive_limit: int = 30) -> Dict[str, Any]:
    state = run_graph(question, recursive_limit=recursive_limit)
    return {"ok": True, "answer": _extract_final(state.get("messages", []))}
