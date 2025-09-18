from django.http import JsonResponse
from django.shortcuts import render
import uuid


# 메인 채팅 페이지
def chat_page(request):
    return render(request, "dbchat/dbchat.html")

# 질문 전송 (임시 답변 반환)
def ask_api(request):
    if request.method == "POST":
        # 클라이언트에서 넘어온 질문 읽기
        question = request.POST.get("question", "질문 없음")
        session_id = request.POST.get("session_id", str(uuid.uuid4()))

        # 임시 답변
        answer = f"'{question}'에 대한 임시 답변입니다."

        return JsonResponse({
            "session_id": session_id,
            "question": question,
            "answer": answer
        })
    return JsonResponse({"error": "POST 요청만 가능합니다."}, status=400)

# 질문 내역 조회 (임시 데이터)
def history_api(request):
    dummy_history = [
        {"question": "박주연의 17일 스트레스가 가장 높았던 시간은?", "answer": "17일 오후 3시에 가장 높았습니다."},
        {"question": "박주연의 평균 HRV는?", "answer": "52로 계산됩니다."},
    ]
    return JsonResponse({"history": dummy_history})
