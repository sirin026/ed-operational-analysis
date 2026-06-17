-- ============================================================
-- Emergency Department Operational Analysis
-- Key SQL Queries
-- Author: Siri Namala
-- ============================================================

-- Q1: Overall KPIs
SELECT
    COUNT(*)                             AS total_patients,
    ROUND(AVG(wait_time_min), 1)         AS avg_wait_time_min,
    ROUND(MIN(wait_time_min), 1)         AS min_wait_time_min,
    ROUND(MAX(wait_time_min), 1)         AS max_wait_time_min,
    SUM(CASE WHEN admission_flag = 'Admission' THEN 1 ELSE 0 END)     AS total_admitted,
    SUM(CASE WHEN admission_flag = 'Not Admission' THEN 1 ELSE 0 END) AS total_discharged,
    ROUND(AVG(satisfaction_score), 2)    AS avg_satisfaction_score
FROM ed_visits;

-- Q2: Patient Volume by Hour of Day (peak identification)
SELECT
    hour_of_day,
    COUNT(*)                        AS patient_count,
    ROUND(AVG(wait_time_min), 1)    AS avg_wait_min,
    ROUND(AVG(satisfaction_score), 2) AS avg_satisfaction
FROM ed_visits
GROUP BY hour_of_day
ORDER BY hour_of_day;

-- Q3: Wait Time by Shift
SELECT
    shift,
    COUNT(*)                        AS patient_count,
    ROUND(AVG(wait_time_min), 1)    AS avg_wait_min,
    ROUND(AVG(satisfaction_score), 2) AS avg_satisfaction
FROM ed_visits
GROUP BY shift
ORDER BY avg_wait_min DESC;

-- Q4: Wait Time by Day of Week
SELECT
    day_of_week,
    COUNT(*)                        AS patient_count,
    ROUND(AVG(wait_time_min), 1)    AS avg_wait_min
FROM ed_visits
GROUP BY day_of_week
ORDER BY avg_wait_min DESC;

-- Q5: Admission Rate by Triage Category
SELECT
    triage_category,
    COUNT(*)                        AS patient_count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM ed_visits), 1) AS pct_of_total,
    SUM(CASE WHEN admission_flag = 'Admission' THEN 1 ELSE 0 END) AS admitted,
    ROUND(AVG(wait_time_min), 1)    AS avg_wait_min,
    ROUND(AVG(satisfaction_score), 2) AS avg_satisfaction
FROM ed_visits
GROUP BY triage_category
ORDER BY avg_wait_min;

-- Q6: Department Referral Analysis
SELECT
    department_referral,
    COUNT(*)                        AS patient_count,
    ROUND(AVG(wait_time_min), 1)    AS avg_wait_min,
    ROUND(AVG(satisfaction_score), 2) AS avg_satisfaction,
    SUM(CASE WHEN admission_flag = 'Admission' THEN 1 ELSE 0 END) AS admitted
FROM ed_visits
GROUP BY department_referral
ORDER BY patient_count DESC;

-- Q7: Patient Demographics Breakdown
SELECT
    age_group,
    gender,
    COUNT(*)                        AS patient_count,
    ROUND(AVG(wait_time_min), 1)    AS avg_wait_min,
    ROUND(AVG(satisfaction_score), 2) AS avg_satisfaction
FROM ed_visits
GROUP BY age_group, gender
ORDER BY age_group, gender;

-- Q8: Satisfaction Score vs Wait Time Correlation Proxy
SELECT
    CASE
        WHEN wait_time_min <= 20 THEN 'Very Short (<= 20 min)'
        WHEN wait_time_min <= 35 THEN 'Short (21-35 min)'
        WHEN wait_time_min <= 50 THEN 'Long (36-50 min)'
        ELSE 'Very Long (> 50 min)'
    END AS wait_bucket,
    COUNT(*)                            AS patient_count,
    ROUND(AVG(satisfaction_score), 2)   AS avg_satisfaction,
    ROUND(AVG(wait_time_min), 1)        AS avg_wait_min
FROM ed_visits
WHERE satisfaction_score IS NOT NULL
GROUP BY wait_bucket
ORDER BY avg_wait_min;

-- Q9: Race-Based Wait Time Equity Analysis
SELECT
    race,
    COUNT(*)                        AS patient_count,
    ROUND(AVG(wait_time_min), 1)    AS avg_wait_min,
    ROUND(AVG(satisfaction_score), 2) AS avg_satisfaction
FROM ed_visits
GROUP BY race
ORDER BY avg_wait_min DESC;

-- Q10: Monthly Throughput Trend
SELECT
    month,
    COUNT(*)                        AS total_visits,
    ROUND(AVG(wait_time_min), 1)    AS avg_wait_min,
    SUM(CASE WHEN admission_flag = 'Admission' THEN 1 ELSE 0 END) AS admitted
FROM ed_visits
GROUP BY month
ORDER BY total_visits DESC;
