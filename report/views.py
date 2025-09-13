from django.shortcuts import render

def report(request):
    # 실제로는 DB에서 Report 모델을 가져오면 됩니다.
    report = {
        "user_name": "박주연",
        "user_initial": "J",
        "author_name": "관리자",
        "date": "2025년 8월 18일",
        "summary": "오늘 하루 대부분 안정적이었으나, 오후 4시 30분경 '등록되지 않은 지역'에서 외부 충격과 급심한 스트레스 반응이 동반된 복합 위험이 1회 발생했습니다.",
        "metrics": [
            {"label": "총 위험 이벤트", "value": "4회"},
            {"label": "외부 충격 감지(움직임 센서)", "value": "1회"},
            {"label": "정신적 압박 감지", "value": "3회"},
            {"label": "최고 스트레스 지수", "value": "99 (오후 4시 35분)"},
        ],
        "timeline": [
            {"time": "오전 9시 05분", "text": "별다른 움직임 없이 스트레스 반응만 감지됨."},
            {"time": "오후 2시 15분", "text": "스트레스 반응 2차 감지됨."},
            {"time": "오후 4시 35분", "text": "'등록되지 않은 지역'에서 외부 충격 및 스트레스 반응 동시 발생."},
            {"time": "오후 6시 45분", "text": "집으로 복귀 후 신호 안정."},
        ],
        "conclusion": "어제 발생한 위험 이벤트는 특정 장소에서 갑작스럽게 발생했으며, 그 전후로 스트레스 반응이 선행되는 패턴을 보였습니다. 해당 시간대의 동선과 상황에 대한 확인이 필요해 보입니다."
    }
    return render(request, "report.html", {"report": report})
