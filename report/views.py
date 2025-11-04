from django.shortcuts import render
print("✅ report/views.py loaded")
from .db_service import get_daily_data
from .ai_service import generate_report
import re
from django.http import JsonResponse
from .models import User
import sqlite3

def build_report_prompt(
    person, date,threat_count, imu_count, hrv_count, stress_count,
    unfamiliar_count, max_stress, max_stress_time,
    threat_count_timeline, imu_count_timeline, hrv_count_timeline,
    stress_count_timeline, unfamiliar_count_timeline,
    timeline, disconnected_timeline
):
    prompt = f"""
다음 데이터를 기반으로 보고서를 작성하세요.

보호자 이름: {person}
보고서 날짜 : {date}
총 위험 이벤트: {threat_count}회
위험 이벤트 타임라인: {threat_count_timeline}
외부 충격 감지 (움직임 센서): {imu_count}회
외부 충격 감지 타임라인: {imu_count_timeline}
정신적 압박 감지 (심박수 분석): {hrv_count}회
정신적 압박 감지 타임라인: {hrv_count_timeline}
스트레스 감지: {stress_count}
스트레스 감지 타임라인: {stress_count_timeline}
비안전지대 감지: {unfamiliar_count}
비안전지대 감지 타임라인: {unfamiliar_count_timeline}
최고 스트레스 지수: {max_stress} ({max_stress_time})
주요 이벤트 타임라인: {timeline}
연결 끊김 타임라인: {disconnected_timeline}

각 timeline은 아래의 쿼리문을 실행해서 나온 결과이다. 참고하시오:
 GROUP_CONCAT(CASE WHEN f.ppg_threat_detected >= 80 THEN f.timestamp || '|' || f.ppg_threat_detected  END, ';') AS ppg_event_group,
    GROUP_CONCAT(CASE WHEN f.imu_danger_level >= 4 THEN f.timestamp || '|' || f.imu_danger_level END, ';') AS imu_event_group,
    GROUP_CONCAT(CASE WHEN f.hrv >= 120 OR f.hrv<=40 THEN f.timestamp || '|' || f.hrv END, ';') AS hrv_event_group,
    GROUP_CONCAT(CASE WHEN f.stress >= 80 THEN f.timestamp || '|' || f.stress END, ';') AS stress_event_group,
    GROUP_CONCAT(CASE WHEN f.zone_type = 'unfamiliar' THEN f.timestamp || '|' || f.zone_type END, ';') AS unfamiliar_event_group,

    -- 2조건 이상 동시 충족 타임라인
    GROUP_CONCAT(
        CASE
            WHEN (CASE WHEN f.ppg_threat_detected >= 80 THEN 1 ELSE 0 END) +
                 (CASE WHEN f.imu_danger_level >= 4 THEN 1 ELSE 0 END) +
                 (CASE WHEN f.hrv >= 120 OR f.hrv <= 40 THEN 1 ELSE 0 END) +
                 (CASE WHEN f.stress >= 80 THEN 1 ELSE 0 END) +
                 (CASE WHEN f.zone_type = 'unfamiliar' THEN 1 ELSE 0 END) >= 2
            THEN f.timestamp || '|' || f.ppg_threat_detected || '|' || f.imu_danger_level || '|' ||
                 f.hrv || '|' || f.stress || '|' || f.zone_type
        END, ';'
    ) AS 주요_이벤트_타임라인,

보고서는 다음 형식을 따라 작성합니다:
1. 핵심 요약: 오늘 하루의 전반적 상태와 위험 이벤트 핵심 요약(안정 상태 평균과 가장 핵심 이벤트 하나 설명)
2. 주요 지표: 위의 데이터를 설명을 참고하여 순서대로 작성하시오. 횟수와 해당 이벤트의 타임라인 설명, 타임라인 timestamp는 00시 00분으로 설정해라. 타임라인 데이터를 보고 한 줄 설명문(요약) 작성 
3. 주요 이벤트 타임라인: 시간순으로 정리, 이벤트 설명, 다음의 조건에 해당하는 부분을 요약·설명. 
4. 종합 의견 및 제안: 위험 이벤트의 의미, 주의할 점, 제안 등

다음의 예시를 참고해서 입력받은 데이터를 기반으로 보고서를 작성합니다:

**핵심 요약**
오늘 하루 대부분 안정적이었으나, 오후 4시 30분경 '등록되지 않은 지역'에서 외부 충격과 극심한 스트레스 반응이 동반된 복합 위협이 1회 발생했습니다.
---
**주요 지표**

- 총 위험 이벤트(PPG 불안정지수 80 이상): 3회
    - 9시 05분: (안전구역) 외부 충격과 함께 PPG 불안정 지수 80으로 감지됨.
    - 14시 15분: (비안전구역) PPG 불안정 지수 90으로 감지됨.
    - 14시 30분: (비안전구역) 안전 구역을 벗어나 불안정이 지속됨.
- 외부 충격 감지 (움직임 센서): 2회
    - 9시 05분: (안전구역) 동작 위험 라벨 4
    - 15시 15분: (비안전구역) 동작 위험 라벨 5
- 정신적 압박 감지 (심박수 분석): 1회
    - 10시 25분: (비안전구역) 심박변이도 30으로 평균보다 낮게 감지됨.
- 스트레스 감지: 1회
    - 11시 40분: (비안전구역) 스트레스 지수 80으로 감지됨.
- 비안전지대 감지: 2회
    - 10시 25분: 비안전구역에 위치함.
    - 14시 15분: 비안전구역에 위치함.

- 최고 스트레스 지수: 99 (오후 4시 35분)

---
**주요 타임라인 (불안정 상태 2개 이상인 이벤트)**

- 9시 05분: (안전구역) 외부 충격과 함께 PPG 불안정 지수 80으로 감지됨.
- 15시 15분: (비안전구역) 동작 위험 라벨 5

---
**종합 의견 및 제안**
어제 발생한 위험 이벤트는 특정 장소에서 갑작스럽게 발생했으며, 그 전후로 스트레스 반응이 선행되는 패턴을 보였습니다. 해당 시간대의 동선과 상황에 대한 확인이 필요해 보입니다. 현재는 안정 상태를 유지하고 있습니다.

Answer:
"""
    return prompt


def report(request):
    report_text = None
    name = request.GET.get("name")
    date = request.GET.get("period")

    if name and date:
        t_result = get_daily_data(name, date)
        if t_result:
            llm_input = {
                "person": t_result[0],
                "date": t_result[1],
                "threat_count": t_result[2],
                "imu_count": t_result[3],
                "hrv_count": t_result[4],
                "stress_count": t_result[5],
                "unfamiliar_count": t_result[6],
                "max_stress": t_result[7],
                "max_stress_time": t_result[8],
                "threat_count_timeline": t_result[9],
                "imu_count_timeline": t_result[10],
                "hrv_count_timeline": t_result[11] or "",
                "stress_count_timeline": t_result[12],
                "unfamiliar_count_timeline": t_result[13],
                "timeline": t_result[14],
                "disconnected_timeline": t_result[15] or ""
            }

            prompt = build_report_prompt(**llm_input)
            report_text = generate_report(prompt)
            
            match = re.search(r"Answer:\s*(.*)", report_text, re.DOTALL)
            if match:
                report_text = match.group(1).strip()

    return render(request, "report.html", {"report": report_text})


def autocomplete_name(request):
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse([], safe=False)

    db_path = r"C:\Users\user\Server\db\protectee.db"  # 절대경로 사용
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # users 테이블에서 이름 검색
    cursor.execute("SELECT name FROM users WHERE name LIKE ? ORDER BY name LIMIT 10", (f"%{query}%",))
    rows = cursor.fetchall()
    names = [row[0] for row in rows]

    conn.close()
    return JsonResponse(names, safe=False)
