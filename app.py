import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="Jarvis Resource Planner", layout="wide")

# --- Inputs ---
with st.sidebar:
    st.header("⚙️ Configuration")
    start_date = st.date_input("Kick-off Date", datetime(2026, 1, 27))
    num_sprints = st.number_input("Number of Sprints", min_value=2, value=3)
    
    st.subheader("Team Size")
    dev_count = st.number_input("Dev Team (Resources)", value=3)
    qa_count = st.number_input("QA Team (Resources)", value=2)
    
    st.subheader("Capacity")
    hrs_per_person = st.number_input("Hrs per Person (e.g., 8 days)", value=64)
    
    uploaded_file = st.file_uploader("Upload MPESA Enhancement Excel", type=['xlsx', 'csv'])

# --- Logic: Staggered Resource Allocation ---
def allocate_resources(df, n_sprints, d_count, q_count, limit):
    # 1. Prepare Data
    df = df[~df['Task Description'].str.contains("Analysis|SRS", case=False, na=False)].copy()
    df['Hours'] = pd.to_numeric(df['Hours'], errors='coerce').fillna(0)
    
    # 2. Separate Dev and QA specific tasks from the file
    dev_tasks = df[~df['Task Description'].str.contains("QA|Testing|Test Case", case=False)].copy()
    qa_tasks = df[df['Task Description'].str.contains("QA|Testing|Test Case", case=False)].copy()

    # 3. Initialize Resource Clocks
    # Structure: { "Sprint 1": { "Dev 1": 0, "QA 1": 0 ... }, "Sprint 2": ... }
    plan = []
    res_clocks = {}
    for s in range(1, n_sprints + 1):
        res_clocks[f"Sprint {s}"] = {
            **{f"Dev {i+1}": 0 for i in range(d_count)},
            **{f"QA {i+1}": 0 for i in range(q_count)}
        }

    # 4. Dev Allocation Logic (Equal Weightage)
    for _, row in dev_tasks.iterrows():
        assigned = False
        for s in range(1, n_sprints + 1):
            s_name = f"Sprint {s}"
            # Find dev with least load in this sprint
            devs_in_sprint = {k: v for k, v in res_clocks[s_name].items() if "Dev" in k}
            best_dev = min(devs_in_sprint, key=devs_in_sprint.get)
            
            if res_clocks[s_name][best_dev] + row['Hours'] <= limit:
                res_clocks[s_name][best_dev] += row['Hours']
                plan.append({**row, "Sprint": s_name, "Resource": best_dev, "Phase": "Development"})
                assigned = True
                break
        if not assigned:
            plan.append({**row, "Sprint": "Backlog", "Resource": "None", "Phase": "Over Capacity"})

    # 5. QA Staggered Logic
    # Sprint N: Writing TC (80% cap) | Sprint N+1: Testing work from Sprint N
    for _, row in qa_tasks.iterrows():
        is_tc = "Case" in row['Task Description'] or "Preparation" in row['Task Description']
        
        for s in range(1, n_sprints + 1):
            s_num = s if is_tc else s + 1 # TC in current, Testing in next
            s_name = f"Sprint {s_num}"
            
            if s_name not in res_clocks: continue
            
            qas_in_sprint = {k: v for k, v in res_clocks[s_name].items() if "QA" in k}
            best_qa = min(qas_in_sprint, key=qas_in_sprint.get)
            
            # Apply 80% rule for TC Writing in Sprint 1
            current_limit = limit * 0.8 if (is_tc and s == 1) else limit
            
            if res_clocks[s_name][best_qa] + row['Hours'] <= current_limit:
                res_clocks[s_name][best_qa] += row['Hours']
                plan.append({**row, "Sprint": s_name, "Resource": best_qa, "Phase
