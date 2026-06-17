"""
Emergency Department Operational Analysis — Full Pipeline
Author: Siri Namala

Cleans raw ED patient flow data, loads into SQLite,
runs 10 analysis queries, and generates 5 Matplotlib charts.

Usage:
    python 03_eda_pipeline.py
"""

import pandas as pd
import sqlite3
import shutil
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# ── PATHS ─────────────────────────────────────────────────────────────────────
ROOT   = os.path.dirname(os.path.abspath(__file__))
RAW    = os.path.join(ROOT, 'healthcare_analytics_patient_flow_data.csv')
CLEAN  = os.path.join(ROOT, 'ed_patient_flow_clean.csv')
DB_TMP = '/tmp/ed_analysis.db'
DB_OUT = os.path.join(ROOT, 'ed_analysis.db')

# ── STEP 1: DATA CLEANING ─────────────────────────────────────────────────────
print("Step 1: Cleaning data...")
df = pd.read_csv(RAW)

# Fix gender typo
df['Patient Gender'] = df['Patient Gender'].replace('Femaleemale', 'Female')

# Parse datetime (mixed format in source data)
df['Admission DateTime'] = pd.to_datetime(
    df['Patient Admission Date'] + ' ' + df['Patient Admission Time'],
    format='mixed', dayfirst=False
)

# Derived time features
df['Hour']       = df['Admission DateTime'].dt.hour
df['Day of Week']= df['Admission DateTime'].dt.day_name()
df['Month']      = df['Admission DateTime'].dt.month_name()
df['Shift']      = pd.cut(df['Hour'], bins=[-1, 7, 15, 23],
                       labels=['Night (00-07)', 'Day (08-15)', 'Evening (16-23)'])

# Fill nulls
df['Department Referral']     = df['Department Referral'].fillna('No Referral')
df['Patient Satisfaction Score'] = df['Patient Satisfaction Score'].fillna(
    round(df['Patient Satisfaction Score'].median(), 1))

# Triage proxy from wait time
df['Triage Category'] = pd.cut(df['Patient Waittime'], bins=[0, 20, 35, 50, 60],
    labels=['Critical', 'Urgent', 'Semi-Urgent', 'Non-Urgent'])

# Age groups
df['Age Group'] = pd.cut(df['Patient Age'], bins=[0, 17, 35, 55, 75, 120],
    labels=['Pediatric (0-17)', 'Young Adult (18-35)', 'Adult (36-55)',
            'Senior (56-75)', 'Elderly (76+)'])

df.to_csv(CLEAN, index=False)
print(f"  Cleaned: {df.shape[0]} rows, {df.shape[1]} columns → {CLEAN}")

# ── STEP 2: LOAD INTO SQLITE ──────────────────────────────────────────────────
print("\nStep 2: Loading into SQLite...")
df_db = df.rename(columns={
    'Patient Id': 'patient_id', 'Patient Admission Date': 'admission_date',
    'Patient Admission Time': 'admission_time', 'Merged': 'assigned_staff',
    'Patient Gender': 'gender', 'Patient Age': 'age', 'Patient Race': 'race',
    'Department Referral': 'department_referral',
    'Patient Admission Flag': 'admission_flag',
    'Patient Satisfaction Score': 'satisfaction_score',
    'Patient Waittime': 'wait_time_min', 'Admission DateTime': 'admission_datetime',
    'Hour': 'hour_of_day', 'Day of Week': 'day_of_week', 'Shift': 'shift',
    'Triage Category': 'triage_category', 'Age Group': 'age_group'
})

conn = sqlite3.connect(DB_TMP)
df_db.to_sql('ed_visits', conn, if_exists='replace', index=False)
conn.commit()
print(f"  Loaded {len(df_db)} records into SQLite.")

# ── STEP 3: RUN ANALYSIS QUERIES ──────────────────────────────────────────────
print("\nStep 3: Running analysis queries...")

queries = {
    "Overall KPIs": """
        SELECT COUNT(*) AS total_patients,
               ROUND(AVG(wait_time_min),1) AS avg_wait_min,
               ROUND(AVG(satisfaction_score),2) AS avg_satisfaction,
               SUM(CASE WHEN admission_flag='Admission' THEN 1 ELSE 0 END) AS admitted,
               SUM(CASE WHEN admission_flag='Not Admission' THEN 1 ELSE 0 END) AS discharged
        FROM ed_visits
    """,
    "Volume by Hour": """
        SELECT hour_of_day, COUNT(*) AS patient_count, ROUND(AVG(wait_time_min),1) AS avg_wait
        FROM ed_visits GROUP BY hour_of_day ORDER BY hour_of_day
    """,
    "Wait Time by Shift": """
        SELECT shift, COUNT(*) AS patient_count, ROUND(AVG(wait_time_min),1) AS avg_wait,
               ROUND(AVG(satisfaction_score),2) AS avg_satisfaction
        FROM ed_visits GROUP BY shift ORDER BY avg_wait DESC
    """,
    "Volume by Day of Week": """
        SELECT day_of_week, COUNT(*) AS patient_count, ROUND(AVG(wait_time_min),1) AS avg_wait
        FROM ed_visits GROUP BY day_of_week ORDER BY patient_count DESC
    """,
    "Triage Category Analysis": """
        SELECT triage_category, COUNT(*) AS patient_count,
               ROUND(COUNT(*)*100.0/(SELECT COUNT(*) FROM ed_visits),1) AS pct,
               ROUND(AVG(wait_time_min),1) AS avg_wait,
               ROUND(AVG(satisfaction_score),2) AS avg_satisfaction
        FROM ed_visits GROUP BY triage_category ORDER BY avg_wait
    """,
    "Department Referrals": """
        SELECT department_referral, COUNT(*) AS patient_count,
               ROUND(AVG(wait_time_min),1) AS avg_wait,
               ROUND(AVG(satisfaction_score),2) AS avg_satisfaction
        FROM ed_visits GROUP BY department_referral ORDER BY patient_count DESC
    """,
    "Demographics": """
        SELECT age_group, gender, COUNT(*) AS patient_count,
               ROUND(AVG(wait_time_min),1) AS avg_wait
        FROM ed_visits GROUP BY age_group, gender ORDER BY age_group, gender
    """,
    "Satisfaction vs Wait": """
        SELECT CASE WHEN wait_time_min<=20 THEN 'Very Short (≤20 min)'
                    WHEN wait_time_min<=35 THEN 'Short (21-35 min)'
                    WHEN wait_time_min<=50 THEN 'Long (36-50 min)'
                    ELSE 'Very Long (>50 min)' END AS wait_bucket,
               ROUND(AVG(satisfaction_score),2) AS avg_satisfaction,
               COUNT(*) AS patient_count
        FROM ed_visits WHERE satisfaction_score IS NOT NULL
        GROUP BY wait_bucket ORDER BY avg_satisfaction DESC
    """,
    "Race-Based Wait Equity": """
        SELECT race, COUNT(*) AS patient_count,
               ROUND(AVG(wait_time_min),1) AS avg_wait,
               ROUND(AVG(satisfaction_score),2) AS avg_satisfaction
        FROM ed_visits GROUP BY race ORDER BY avg_wait DESC
    """,
    "Monthly Throughput": """
        SELECT month, COUNT(*) AS total_visits, ROUND(AVG(wait_time_min),1) AS avg_wait,
               SUM(CASE WHEN admission_flag='Admission' THEN 1 ELSE 0 END) AS admitted
        FROM ed_visits GROUP BY month ORDER BY total_visits DESC
    """,
}

for name, q in queries.items():
    result = pd.read_sql(q, conn)
    print(f"\n{'='*55}\n  {name}\n{'='*55}")
    print(result.to_string(index=False))

conn.close()
shutil.copy(DB_TMP, DB_OUT)

# ── STEP 4: GENERATE CHARTS ───────────────────────────────────────────────────
print("\n\nStep 4: Generating charts...")
TEAL, BLUE, ORANGE = '#2E86AB', '#1F4E79', '#E07B39'
GRID = '#f0f4f8'

df = pd.read_csv(CLEAN)

# Chart 1: Volume by Hour
fig, ax = plt.subplots(figsize=(12, 5))
hourly = df.groupby('Hour').size().reset_index(name='count')
colors = [ORANGE if v == hourly['count'].max() else TEAL for v in hourly['count']]
ax.bar(hourly['Hour'], hourly['count'], color=colors, width=0.7, edgecolor='white')
ax.set_facecolor(GRID); fig.patch.set_facecolor('white')
ax.set_xlabel('Hour of Day', fontsize=11); ax.set_ylabel('Patient Arrivals', fontsize=11)
ax.set_title('Patient Volume by Hour of Day\n(9,216 ED Visits)', fontsize=13, fontweight='bold', pad=12)
ax.set_xticks(range(0, 24))
ax.set_xticklabels([f'{h:02d}:00' for h in range(24)], rotation=45, fontsize=8)
ax.yaxis.grid(True, linestyle='--', alpha=0.5); ax.set_axisbelow(True)
ax.spines[['top','right']].set_visible(False)
plt.tight_layout(); plt.savefig(os.path.join(ROOT, 'chart1_volume_by_hour.png'), dpi=150, bbox_inches='tight')
plt.close(); print("  Chart 1 saved.")

# Chart 2: Wait by Triage
fig, ax = plt.subplots(figsize=(9, 5))
triage_order = ['Critical', 'Urgent', 'Semi-Urgent', 'Non-Urgent']
triage = df.groupby('Triage Category')['Patient Waittime'].mean().reindex(triage_order)
bar_colors = ['#27AE60','#F39C12','#E67E22','#E74C3C']
bars = ax.barh(triage.index, triage.values, color=bar_colors, height=0.5, edgecolor='white')
for bar, val in zip(bars, triage.values):
    ax.text(val + 0.5, bar.get_y() + bar.get_height()/2, f'{val:.1f} min', va='center', fontsize=10, fontweight='bold')
ax.set_facecolor(GRID); fig.patch.set_facecolor('white')
ax.set_xlabel('Average Wait Time (minutes)', fontsize=11)
ax.set_title('Average Wait Time by Triage Category', fontsize=13, fontweight='bold', pad=12)
ax.spines[['top','right']].set_visible(False); ax.xaxis.grid(True, linestyle='--', alpha=0.5); ax.set_axisbelow(True)
plt.tight_layout(); plt.savefig(os.path.join(ROOT, 'chart2_wait_by_triage.png'), dpi=150, bbox_inches='tight')
plt.close(); print("  Chart 2 saved.")

# Chart 3: Referral Dept
fig, ax = plt.subplots(figsize=(10, 5))
dept = df[df['Department Referral'] != 'No Referral'].groupby('Department Referral').size().sort_values(ascending=True)
colors3 = [TEAL if v < dept.max() else BLUE for v in dept.values]
ax.barh(dept.index, dept.values, color=colors3, height=0.55, edgecolor='white')
for i, v in enumerate(dept.values):
    ax.text(v + 10, i, str(v), va='center', fontsize=9)
ax.set_facecolor(GRID); fig.patch.set_facecolor('white')
ax.set_xlabel('Number of Patients', fontsize=11)
ax.set_title('Patient Volume by Referral Department\n(Referred Patients Only)', fontsize=13, fontweight='bold', pad=12)
ax.spines[['top','right']].set_visible(False); ax.xaxis.grid(True, linestyle='--', alpha=0.5); ax.set_axisbelow(True)
plt.tight_layout(); plt.savefig(os.path.join(ROOT, 'chart3_referral_dept.png'), dpi=150, bbox_inches='tight')
plt.close(); print("  Chart 3 saved.")

# Chart 4: Admission Donut
fig, ax = plt.subplots(figsize=(7, 6))
admit = df['Patient Admission Flag'].value_counts()
wedge_props = dict(width=0.45, edgecolor='white', linewidth=2)
wedges, texts, autotexts = ax.pie(admit.values, labels=admit.index, autopct='%1.1f%%',
    colors=[BLUE, TEAL], wedgeprops=wedge_props, startangle=90, textprops={'fontsize': 11})
for at in autotexts:
    at.set_fontweight('bold'); at.set_color('white'); at.set_fontsize(12)
for i, (v, label) in enumerate(zip(admit.values, admit.index)):
    texts[i].set_text(f'{label}\n({v:,})')
ax.set_title('Admission vs. Discharge Split\n(9,216 Patients)', fontsize=13, fontweight='bold', pad=12)
plt.tight_layout(); plt.savefig(os.path.join(ROOT, 'chart4_admission_split.png'), dpi=150, bbox_inches='tight')
plt.close(); print("  Chart 4 saved.")

# Chart 5: Satisfaction vs Wait
fig, ax = plt.subplots(figsize=(9, 5))
buckets  = ['≤20 min', '21-35 min', '36-50 min', '>50 min']
avg_sats = [df[df['Patient Waittime']<=20]['Patient Satisfaction Score'].mean(),
            df[(df['Patient Waittime']>20)&(df['Patient Waittime']<=35)]['Patient Satisfaction Score'].mean(),
            df[(df['Patient Waittime']>35)&(df['Patient Waittime']<=50)]['Patient Satisfaction Score'].mean(),
            df[df['Patient Waittime']>50]['Patient Satisfaction Score'].mean()]
bars = ax.bar(buckets, avg_sats, color=['#27AE60','#F1C40F','#E67E22','#E74C3C'], width=0.5, edgecolor='white')
for bar, val in zip(bars, avg_sats):
    ax.text(bar.get_x()+bar.get_width()/2, val+0.005, f'{val:.2f}', ha='center', fontsize=10, fontweight='bold')
ax.set_facecolor(GRID); fig.patch.set_facecolor('white')
ax.set_ylabel('Average Satisfaction Score', fontsize=11); ax.set_xlabel('Wait Time Bucket', fontsize=11)
ax.set_title('Patient Satisfaction Score by Wait Time\n(Lower Wait = Higher Satisfaction)', fontsize=13, fontweight='bold', pad=12)
ax.set_ylim(4.9, 5.15); ax.spines[['top','right']].set_visible(False)
ax.yaxis.grid(True, linestyle='--', alpha=0.5); ax.set_axisbelow(True)
plt.tight_layout(); plt.savefig(os.path.join(ROOT, 'chart5_satisfaction_vs_wait.png'), dpi=150, bbox_inches='tight')
plt.close(); print("  Chart 5 saved.")

print("\n✓ All done! Charts and database saved to:", ROOT)
