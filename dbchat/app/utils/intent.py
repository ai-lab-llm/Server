from __future__ import annotations
from typing import Dict, Any
import json, re
from app.core.llm import get_chat_llm
from app.core.database import get_db
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda

SCHEMA_HINT = """
You are a gatekeeper for a database Q&A endpoint.

This endpoint ONLY accepts questions that can be answered by querying a small SQLite DB
with tables: users(id, name), event(protectee_id -> users.id, timestamp, ppg_json, ppg_threat_detected, hrv, stress, imu_danger_level, latitude, longitude, zone_type, is_watch_connected).

Label the user's input as either:
- "db_query": if the intent is to retrieve/aggregate/filter something from these tables/columns (highest/lowest/average, latest time, count, list within date range, filter by user name, zone_type, watch connection, etc.)
- "other": greetings, chit-chat, general questions, non-database tasks, or requests without any retrievable target from this schema.

ALWAYS return pure JSON: {{\"intent\": \"db_query\"}} or {{\"intent\": \"other\"}}
Do not add explanations. No code fences.
"""

PROMPT = ChatPromptTemplate.from_messages([
    ("system", SCHEMA_HINT),
    ("system",
     "Examples:\n"
     "Q: \"박해름의 스트레스가 가장 높았던 시각 알려줘\" -> {{\"intent\":\"db_query\"}}\n"
     "Q: \"안녕?\" -> {{\"intent\":\"other\"}}\n"
     "Q: \"요즘 날씨 어때?\" -> {{\"intent\":\"other\"}}\n"
     "Q: \"박주연의 HRV 최저값과 시각\" -> {{\"intent\":\"db_query\"}}\n"
     "Q: \"워치가 최근에 끊긴 시간\" -> {{\"intent\":\"db_query\"}}\n"
     "Q: \"수학 문제 풀어줘\" -> {{\"intent\":\"other\"}}\n"
    ),
    ("human", "{question}")
])

def _robust_json(text: str) -> Dict[str, Any]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?|```$", "", cleaned, flags=re.MULTILINE)
    m = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if m:
        cleaned = m.group(0)
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict) and data.get("intent") in {"db_query", "other"}:
            return data
    except Exception:
        pass
    return {"intent": "other"}

def classify_intent_llm(question: str) -> str:
    """Return 'db_query' or 'other'."""
    llm = get_chat_llm()
    chain = PROMPT | llm | StrOutputParser() | RunnableLambda(_robust_json)
    out = chain.invoke({"question": question})
    return out.get("intent", "other")

def list_known_names(limit: int = 5) -> list[str]:
    names: list[str] = []
    try:
        rows = get_db().run("SELECT name FROM users LIMIT 20")
        for r in rows or []:
            if isinstance(r, (list, tuple)) and r and isinstance(r[0], str):
                names.append(r[0])
    except Exception:
        pass
    return names[:limit]



_MAX_PAT = re.compile(r"(가장\s*높|최대|최고|highest|max)", re.I)
_MIN_PAT = re.compile(r"(가장\s*낮|최소|lowest|min)", re.I)
_WHEN_PAT = re.compile(r"(언제|시각|시간|몇\s*시|시점|때)", re.I)

def detect_extreme_direction(question: str) -> str | None:
    if _MAX_PAT.search(question):
        return "max"
    if _MIN_PAT.search(question):
        return "min"
    return None

def asks_when(question: str) -> bool:
    return _WHEN_PAT.search(question) is not None



# ===========================================
# 상태 필터 (정규식 기반 Fallback)

_ZONE_SAFE_RE   = re.compile(r"(?:\b|^)(safe|안전(?:한|함)?|안전\s*구역)(?:\b|$)", re.I)
_ZONE_UNFAM_RE  = re.compile(r"(?:\b|^)(unfamiliar|낯선(?:\s*(?:곳|장소))?|낯설|초행)(?:\b|$)", re.I)

# watch 끊김(0) / 연결(1)
_WATCH_OFF_RE = re.compile(
    r"(워치|watch|시계|블루투스).*(끊김|해제|끊어|끊겼|끊긴|off|0|연결\s*안|연결\s*없|끊긴\s*상태|페어링\s*실패|불안정)",
    re.I
)
_WATCH_ON_RE = re.compile(
    r"(워치|watch|시계|블루투스).*(연결(?!\s*안)|유지|붙어|on|1|연동|페어링(?!\s*실패)|정상)",
    re.I
)

_NUMERIC_HINT_RE = re.compile(
    r"(stress|hrv|ppg|imu|지수|값|수치|퍼센트|%|평균|최소|최대|가장|높|낮|랭킹|순위|분산|표준편차)",
    re.I
)
_STATUS_HINT_RE = re.compile(
    r"(워치|watch|시계|연결|끊김|zone|safe|unfamiliar|낯선|안전|구역)",
    re.I
)

def detect_zone_and_watch_filters(q: str) -> Dict[str, Any]:
    """키워드/정규식 기반 상태 필터 추출."""
    zone = None
    if _ZONE_UNFAM_RE.search(q): zone = "unfamiliar"
    elif _ZONE_SAFE_RE.search(q): zone = "safe"

    watch = None
    if _WATCH_OFF_RE.search(q): watch = 0
    elif _WATCH_ON_RE.search(q): watch = 1

    return {"zone": zone, "watch": watch}

def target_is_numeric_metric(q: str) -> bool:
    """
    질문이 '수치/최고/최저/평균' 등 메트릭 중심인지 판별.
    zone/watch 신호만 있고 수치 힌트가 없으면 False.
    """
    has_num = bool(_NUMERIC_HINT_RE.search(q))
    has_status = bool(_STATUS_HINT_RE.search(q))
    if has_status and not has_num:
        return False
    return has_num


# =========================
# 4) LLM 의미 추출기 (하이브리드)
# =========================
_STATUS_SYS = (
    "You are a precise Korean question analyzer.\n"
    "Return STRICT JSON with exactly these keys:\n"
    "- zone: one of safe | unfamiliar | empty\n"
    "- zone_conf: integer 0~100\n"
    "- watch: one of 1 | 0 | empty (1=connected, 0=disconnected)\n"
    "- watch_conf: integer 0~100\n"
    "- notes: short reason\n"
    "Prefer precision over recall; do NOT guess."
)

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.core.llm import get_chat_llm

_STATUS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _STATUS_SYS),
    ("human", "Question: {q}\nJSON only:")
])



def _safe_json_load(s: str) -> dict:
    """완전한 JSON이 아니어도 { ... } 블록만 떼어 파싱."""
    s = (s or "").strip()
    m = re.search(r"\{[\s\S]*\}$", s)
    if m:
        s = m.group(0)
    try:
        data = json.loads(s)
        if not isinstance(data, dict):
            raise ValueError
        return data
    except Exception:
        return {
            "zone": "empty", "zone_conf": 0,
            "watch": "empty", "watch_conf": 0,
            "notes": "parse_error"
        }

def semantic_status_extractor(q: str) -> dict:
    """
    LLM으로 질문을 의미 해석해서 zone/watch을 구조화해 반환.
    반환 예:
      {"zone": "safe"| "unfamiliar"| None,
       "zone_conf": 0~100,
       "watch": 1|0|None,
       "watch_conf": 0~100,
       "notes": "..."}
    """
    llm = get_chat_llm()  # temperature=0 권장
    out = (_STATUS_PROMPT | llm | StrOutputParser()).invoke({"q": q})
    data = _safe_json_load(out)

    zone = data.get("zone", "empty")
    if zone not in ("safe", "unfamiliar"):
        zone = "empty"
    watch = data.get("watch", "empty")
    if str(watch) not in ("1", "0", "empty"):
        watch = "empty"

    def _to_int(x, default=0):
        try:
            return int(float(x))
        except Exception:
            return default

    return {
        "zone": None if zone == "empty" else zone,
        "zone_conf": _to_int(data.get("zone_conf", 0)),
        "watch": None if watch == "empty" else int(watch),
        "watch_conf": _to_int(data.get("watch_conf", 0)),
        "notes": data.get("notes", "")
    }

def resolve_status_filters(q: str, llm_threshold: int = 70) -> dict:
    """
    하이브리드 해석기:
      1) LLM 의미 추출 시도 → conf >= threshold 면 채택
      2) 아니면 정규식 기반 detect_zone_and_watch_filters 결과로 폴백
    반환: {"zone": "safe"|"unfamiliar"|None, "watch": 1|0|None, "source": "llm|regex", "conf": int}
    """
    sem = semantic_status_extractor(q)
    use_llm = (
        (sem["zone"] is not None and sem["zone_conf"] >= llm_threshold) or
        (sem["watch"] is not None and sem["watch_conf"] >= llm_threshold)
    )
    if use_llm:
        return {
            "zone": sem["zone"],
            "watch": sem["watch"],
            "source": "llm",
            "conf": max(sem["zone_conf"], sem["watch_conf"])
        }

    fb = detect_zone_and_watch_filters(q)  # Fallback
    return {"zone": fb["zone"], "watch": fb["watch"], "source": "regex", "conf": 0}