from typing import Dict, Generator, Any, Optional
from django.http import JsonResponse, StreamingHttpResponse, HttpResponse
import json

def parse_json(request) -> Dict[str, Any]:
    try:
        return json.loads(request.body.decode("utf-8"))
    except Exception:
        return {}

def error_json(status: int, code: str, msg: str, trace: Optional[Dict]=None):
    payload = {"error": code, "message": msg}
    if trace: payload["trace_id"] = trace
    return JsonResponse(payload, status=status)

def ok(data: Dict[str, Any], status: int = 200) -> JsonResponse:
    return JsonResponse(data, status=status, json_dumps_params={"ensure_ascii": False})

def sse_pack(data: Dict[str, Any]) -> bytes:
    """
    Server-Sent Events 규격: 'data: <json>\n\n'
    """
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n".encode("utf-8")