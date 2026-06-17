-- ============================================================
-- Emergency Department Operational Analysis
-- Schema: SQLite
-- Author: Siri Namala
-- ============================================================

CREATE TABLE IF NOT EXISTS ed_visits (
    patient_id          TEXT,
    admission_date      TEXT,
    admission_time      TEXT,
    assigned_staff      TEXT,
    gender              TEXT,
    age                 INTEGER,
    race                TEXT,
    department_referral TEXT,
    admission_flag      TEXT,
    satisfaction_score  REAL,
    wait_time_min       INTEGER,
    admission_datetime  TEXT,
    hour_of_day         INTEGER,
    day_of_week         TEXT,
    month               TEXT,
    shift               TEXT,
    triage_category     TEXT,
    age_group           TEXT
);

-- KPI Views

-- Average wait time by shift
CREATE VIEW IF NOT EXISTS v_wait_by_shift AS
SELECT
    shift,
    COUNT(*)                        AS patient_count,
    ROUND(AVG(wait_time_min), 1)    AS avg_wait_min,
    ROUND(MIN(wait_time_min), 1)    AS min_wait_min,
    ROUND(MAX(wait_time_min), 1)    AS max_wait_min
FROM ed_visits
GROUP BY shift
ORDER BY avg_wait_min DESC;

-- Patient volume by hour
CREATE VIEW IF NOT EXISTS v_volume_by_hour AS
SELECT
    hour_of_day,
    COUNT(*)                        AS patient_count,
    ROUND(AVG(wait_time_min), 1)    AS avg_wait_min
FROM ed_visits
GROUP BY hour_of_day
ORDER BY hour_of_day;

-- Referral department breakdown
CREATE VIEW IF NOT EXISTS v_referral_breakdown AS
SELECT
    department_referral,
    COUNT(*)                        AS patient_count,
    ROUND(AVG(wait_time_min), 1)    AS avg_wait_min,
    ROUND(AVG(satisfaction_score), 2) AS avg_satisfaction
FROM ed_visits
GROUP BY department_referral
ORDER BY patient_count DESC;
