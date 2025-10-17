# dbchat/views_api.py
from __future__ import annotations
import json, time
from django.http import JsonResponse, StreamingHttpResponse, HttpResponseNotAllowed
from django.views.decorators.csrf import csrf_exempt
from dbchat.app.entrypoint import ask_once
from dbchat.app.utils.intent import classify_intent_llm, list_known_names

def _guide() -> str:
    names = list_known_names(limit=3)
    hint = f" (예: {', '.join(names)})" if names else ""
    return "이 화면은 보호대상자 데이터 조건 검색 전용입니다.\n누구의 어떤 정보를 원하시나요?" + hint

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

    # 인텐트 게이트(네가 쓰던 규칙 그대로)
    if classify_intent_llm(q) != "db_query":
        return JsonResponse({"ok": True, "answer": _guide()}, status=200)

    res = ask_once(q, recursive_limit=30)
    return JsonResponse(res, status=200)

@csrf_exempt
def api_ask_stream(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    try:
        body = json.loads(request.body.decode("utf-8") or "{}")
        q = (body.get("question") or "").strip()
    except Exception:
        q = ""

    def gen():
        if not q:
            yield "질문을 입력해 주세요."
            return
        if classify_intent_llm(q) != "db_query":
            yield _guide()
            return
        text = ask_once(q, recursive_limit=30)["answer"]
        # 필요하면 천천히 잘라서 전송
        chunk = 18
        for i in range(0, len(text), chunk):
            yield text[i:i+chunk]
            time.sleep(0.008)
        yield "\n"

    return StreamingHttpResponse(
        gen(),
        content_type="text/plain; charset=utf-8",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
