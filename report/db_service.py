from sqlalchemy import create_engine, text


engine = create_engine("sqlite:///./db/protectee.db")

query_template = text("""
WITH
params AS (
    SELECT :name AS name, :date AS date
),
-- 최대 스트레스 1건 선택
max_stress_data AS (
    SELECT e2.protectee_id, e2.stress AS max_stress, e2.timestamp AS max_stress_time
    FROM event e2
    JOIN users u2 ON e2.protectee_id = u2.id
    JOIN params p ON u2.name = p.name
        AND e2.timestamp LIKE p.date || '%'
    ORDER BY e2.stress DESC, e2.timestamp ASC
    LIMIT 1
),
-- 하루 전체 이벤트
user_events AS (
    SELECT e.*
    FROM event e
    JOIN max_stress_data msd ON e.protectee_id = msd.protectee_id
    WHERE e.timestamp LIKE (SELECT date || '%' FROM params)
    ORDER BY e.timestamp
),
-- watch 상태 변화 계산 (1->0, 0->1)
status_changes AS (
    SELECT
        ue.protectee_id,
        ue.timestamp AS ts,
        ue.is_watch_connected AS status,
        CASE
            -- 실제 1->0 전환만 disconnect
            WHEN ue.is_watch_connected = 0 
                 AND LAG(ue.is_watch_connected) OVER (PARTITION BY ue.protectee_id ORDER BY ue.timestamp) = 1
            THEN 1 ELSE 0 END AS is_disconnect,
        CASE
            WHEN ue.is_watch_connected = 1
                 AND LAG(ue.is_watch_connected) OVER (PARTITION BY ue.protectee_id ORDER BY ue.timestamp) = 0
            THEN 1 ELSE 0 END AS is_reconnect
    FROM user_events ue
),
-- disconnect와 reconnect 시점 연결
watch_transitions AS (
    SELECT 
        d.protectee_id,
        d.ts AS disconnect_time,
        r.ts AS reconnect_time
    FROM status_changes d
    LEFT JOIN status_changes r
        ON d.protectee_id = r.protectee_id
        AND r.ts > d.ts
        AND r.is_reconnect = 1
    WHERE d.is_disconnect = 1
),
-- 조건별 이벤트 필터링
filtered AS (
    SELECT *
    FROM user_events
    WHERE
        ppg_threat_detected >= 80 OR
        hrv >= 120 OR
        hrv <= 40 OR
        stress >= 80 OR
        imu_danger_level >= 4 OR
        zone_type = 'unfamiliar' OR
        is_watch_connected = 0
)
SELECT
    u.name,
    p.date,

    -- 조건별 이벤트 횟수
    SUM(CASE WHEN f.ppg_threat_detected >= 80 THEN 1 ELSE 0 END) AS threat_count,
    SUM(CASE WHEN f.imu_danger_level >= 4 THEN 1 ELSE 0 END) AS imu_count,
    SUM(CASE WHEN f.hrv >= 120 OR f.hrv <= 40 THEN 1 ELSE 0 END) AS hrv_count,
    SUM(CASE WHEN f.stress >= 80 THEN 1 ELSE 0 END) AS stress_count,
    SUM(CASE WHEN f.zone_type = 'unfamiliar' THEN 1 ELSE 0 END) AS unfamiliar_count,

    msd.max_stress,
    msd.max_stress_time,

    -- 조건별 이벤트 그룹
    GROUP_CONCAT(CASE WHEN f.ppg_threat_detected >= 80 THEN f.timestamp || '|' || f.ppg_threat_detected || '|' || f.zone_type END, ';') AS ppg_event_group,
    GROUP_CONCAT(CASE WHEN f.imu_danger_level >= 4 THEN f.timestamp || '|' || f.imu_danger_level || '|' || f.zone_type END, ';') AS imu_event_group,
    GROUP_CONCAT(CASE WHEN f.hrv >= 120 OR f.hrv<=40 THEN f.timestamp || '|' || f.hrv || '|' || f.zone_type END, ';') AS hrv_event_group,
    GROUP_CONCAT(CASE WHEN f.stress >= 80 THEN f.timestamp || '|' || f.stress || '|' || f.zone_type END, ';') AS stress_event_group,
    GROUP_CONCAT(CASE WHEN f.zone_type = 'unfamiliar' THEN f.timestamp || '|' || f.ppg_threat_detected || '|' || f.imu_danger_level || '|' || f.hrv || '|' || f.stress || '|' || f.zone_type END, ';') AS unfamiliar_event_group,

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

    -- watch 1->0->1 전환 구간
    GROUP_CONCAT(wt.disconnect_time || '->' || wt.reconnect_time, ';') AS watch_connection_transitions

FROM filtered f
JOIN users u ON f.protectee_id = u.id
JOIN max_stress_data msd ON msd.protectee_id = f.protectee_id
JOIN params p  
LEFT JOIN watch_transitions wt ON wt.protectee_id = f.protectee_id
GROUP BY f.protectee_id, u.name, msd.max_stress, msd.max_stress_time
LIMIT 10;

""")

def get_daily_data(name: str, date: str):
     with engine.connect() as conn:
        result = conn.execute(query_template, {"name": name, "date": date})
        row = result.fetchone()
        return row 
