from __future__ import annotations
import json, time, re
from django.http import JsonResponse, StreamingHttpResponse, HttpResponseNotAllowed
from django.views.decorators.csrf import csrf_exempt
from dbchat.app.entrypoint import ask_once
from dbchat.app.utils.intent import classify_intent_llm, list_known_names

def _guide() -> str:
    names = list_known_names(limit=3)
    hint = f" (예: {', '.join(names)})" if names else ""
    return "이 화면에서는 보호대상자의 데이터 조건 검색만 가능합니다. \n누구의 어떤 정보를 알고싶으신가요? 😊" + hint

def _strip_tag(text: str) -> str:
    """
    Final:/Answer: 태그 제거 + 첫 유의미 라인만 반환
    (여러 줄 Final 방지)
    """
    if not isinstance(text, str):
        return ""
    # 줄 단위에서 Final:/Answer: 태그 제거
    cleaned = re.sub(r'(?m)^\s*(Final:|Answer:)\s*', '', text).strip()
    # 첫 유의미 라인만
    for ln in cleaned.splitlines():
        s = ln.strip()
        if s:
            return s
    return ""

@csrf_exempt
def api_ask(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    try:
        body = json.loads(request.body.decode("utf-8") or "{}")
        q = (body.get("question") or "").strip()
    except Exception:
        return JsonResponse({"ok": False, "error": "invalid json"}, status=400)

    if not q:
        return JsonResponse({"ok": False, "error": "empty question"}, status=400)

    # 인텐트 게이트 (오류를 JSON으로 돌려주기)
    try:
        intent = classify_intent_llm(q)
    except Exception as e:
        return JsonResponse({"ok": False, "error": f"intent_error: {e}"}, status=500)

    if intent != "db_query":
        return JsonResponse({"ok": True, "answer": _guide()}, status=200)

    try:
        res = ask_once(q, recursive_limit=30)
        content = _strip_tag(res.get("answer", "") or "")
        return JsonResponse({"ok": True, "answer": content}, status=200)
    except Exception as e:
        return JsonResponse({"ok": False, "error": f"ask_error: {e}"}, status=500)


@csrf_exempt
def api_ask_stream(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    try:
        body = json.loads(request.body.decode("utf-8") or "{}")
        q = (body.get("question") or "").strip()
    except Exception:
        q = ""

    def chunk_text(s: str, size: int = 18):
        for i in range(0, len(s), size):
            yield s[i:i+size]

    def gen():
        if not q:
            yield "질문을 입력해 주세요."
            return
        # 인텐트 게이트 (제너레이터 내부에서 예외 흘려보내기)
        try:
            intent = classify_intent_llm(q)
        except Exception as e:
            yield f"[예외] intent_error: {e}\n"; return

        if intent != "db_query":
            yield _guide()
            return

        # 그래프 실행
        try:
            res = ask_once(q, recursive_limit=30)
            content = _strip_tag(res.get("answer", "") or "")
        except Exception as e:
            yield f"[예외] ask_error: {e}\n"; return

        for part in chunk_text(content, size=18):
            yield part
            time.sleep(0.008)
        yield "\n"

    return StreamingHttpResponse(
        gen(),
        content_type="text/plain; charset=utf-8",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
