from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langgraph.errors import GraphRecursionError
from app.graph.workflow import run_graph
from app.utils.intent import classify_intent_llm, list_known_names
import asyncio, re

router = APIRouter()

class AskRequest(BaseModel):
    thread_id: str | None = None
    question: str
    options: dict = {}
    ui_context: dict = {}
    recursive_limit: int | None = None

def _strip_tag(text: str) -> str:
    if not isinstance(text, str):
        return text
    return re.sub(r'(?m)^\s*(Final:|Answer:)\s*', '', text).strip()

def _build_guide() -> str:
    names = list_known_names(limit=3)
    name_hint = (f" (예: {', '.join(names)})" if names else "")
    return (
        "이 화면에서는 보호대상자의 데이터 조건 검색만 가능합니다.\n"
        "누구의 어떤 정보를 알고싶으신가요? 😊\n"
    )


@router.post("/ask")
async def ask(req: AskRequest):
    q = (req.question or "").strip()
    if not q:
        return {"thread_id": req.thread_id or "temp",
                "message": {"role": "ai", "content": "질문을 입력해 주세요."}}

    intent = classify_intent_llm(q)
    if intent != "db_query":
        guide = _build_guide()
        return {"thread_id": req.thread_id or "temp",
                "message": {"role": "ai", "content": guide}}

    limit = req.recursive_limit if req.recursive_limit is not None else req.options.get("recursive_limit", 30)
    if isinstance(limit, int):
        limit = max(15, min(limit, 100))

    try:
        state = run_graph(q, recursive_limit=limit)
    except GraphRecursionError as e:
        raise HTTPException(status_code=422, detail=str(e))

    messages = state.get("messages", [])
    final = answer = fallback = None
    for m in reversed(messages):
        c = getattr(m, "content", None)
        t = getattr(m, "type", None)
        if isinstance(c, str) and c.strip():
            if t == "ai" and c.startswith("Final:"):
                final = c; break
            if t == "ai" and c.startswith("Answer:") and answer is None:
                answer = c
            if fallback is None:
                fallback = c
    content = _strip_tag(final or answer or (fallback or "응답 없음"))

    return {"thread_id": req.thread_id or "temp",
            "message": {"role": "ai", "content": content}}


# /ask_stream : 스트리밍(유사-토큰) 
def _chunk_text(s: str, *, size: int = 16):
    """문자열을 size 크기 조각으로 잘라 순서대로 반환"""
    for i in range(0, len(s), size):
        yield s[i:i+size]

@router.post("/ask_stream")
async def ask_stream(req: AskRequest):
    q = (req.question or "").strip()

    async def _once(text: str):
        for part in _chunk_text(text, size=32):
            yield part
            await asyncio.sleep(0.008)

    # 빈 질문
    if not q:
        return StreamingResponse(
            _once("질문을 입력해 주세요."),
            media_type="text/plain; charset=utf-8",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},  # Nginx 버퍼 끄기
        )

    # 인텐트 확인
    intent = classify_intent_llm(q)
    if intent != "db_query":
        guide = _build_guide()
        return StreamingResponse(
            _once(guide),
            media_type="text/plain; charset=utf-8",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # 그래프 실행
    limit = req.recursive_limit if req.recursive_limit is not None else req.options.get("recursive_limit", 30)
    if isinstance(limit, int):
        limit = max(15, min(limit, 100))

    async def generator():
        try:
            state = run_graph(q, recursive_limit=limit)
            messages = state.get("messages", [])
            final = answer = fallback = None
            for m in reversed(messages):
                c = getattr(m, "content", None)
                t = getattr(m, "type", None)
                if isinstance(c, str) and c.strip():
                    if t == "ai" and c.startswith("Final:"):
                        final = c; break
                    if t == "ai" and c.startswith("Answer:") and answer is None:
                        answer = c
                    if fallback is None:
                        fallback = c
            content = _strip_tag(final or answer or (fallback or "응답 없음"))

            # 본문을 잘게 잘라 전송
            for part in _chunk_text(content, size=18):
                yield part
                await asyncio.sleep(0.008)

            # 끝 표시
            yield "\n"
        except GraphRecursionError as e:
            yield f"[오류] {str(e)}\n"
        except Exception as e:
            yield f"[예외] {repr(e)}\n"

    return StreamingResponse(
        generator(),
        media_type="text/plain; charset=utf-8",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},  # Nginx 버퍼 끄기
    )


# 디버그용 스트림: 파이프라인 확인용 
@router.get("/_debug/stream")
async def debug_stream():
    async def gen():
        for i in range(1, 8):
            yield f"chunk-{i}\n"
            await asyncio.sleep(0.25)
    return StreamingResponse(
        gen(),
        media_type="text/plain; charset=utf-8",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )