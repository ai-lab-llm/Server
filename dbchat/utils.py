from .models import ChatThread
import random
from datetime import datetime

def make_auto_title(first_question: str) -> str:
    s = first_question.strip().replace("\n", " ")
    return (s[:28] + ("…" if len(s) > 28 else "")) or "새 대화"

# def run_dbchat_pipeline(thread: ChatThread):

#     # 1) 직전 대화 이력 불러오기
#     history = list(thread.messages.order_by("created_at").values("role", "content"))
#     # 2) 파이프라인에 맞춰 history 전달 → 답변 생성
#     #    answer = generate_response_from_query_with_history(history, ...)
#     answer = "여기서 SQL-Agent 또는 RAG를 호출해 생성한 답변을 넣습니다."
#     meta = {"latency_ms": 0}
#     return answer, meta


# 임시 더미: 최근 user 메시지를 받아서 에코/규칙 기반으로 간단 응답.
def run_dbchat_pipeline(thread):
    msgs = list(thread.messages.order_by("-created_at")[:10][::-1])  # 최근 10개만
    user_last = next((m.content for m in reversed(msgs) if m.role == "user"), "")

    canned = [
        "네, 확인했어요.",
        "일단 최근 데이터부터 검사해볼게요.",
        "잠깐만요… SQL 쿼리를 구성 중입니다.",
        "그 질문은 날짜가 필요해 보여요. 예: 2025-08-17",
        "관련 이벤트를 정리해서 알려드릴게요."
    ]

    if "안녕" in user_last or "hello" in user_last.lower():
        answer = "안녕하세요! 무엇을 찾아드릴까요?"
    elif "스트레스" in user_last:
        answer = "스트레스 지표를 조회하려면 날짜/이름을 알려주세요. 예) '박주연 8월 17일 스트레스 최고 시각'"
    else:
        answer = f"'{user_last}' 질문을 받았어요. 곧 분석 결과를 붙일게요."

    answer += " " + random.choice(canned)
    meta = {"latency_ms": random.randint(30, 120), "ts": datetime.now().isoformat(timespec="seconds")}
    return answer, meta
