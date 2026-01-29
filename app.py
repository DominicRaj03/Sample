import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
from datetime import datetime, timedelta

st.set_page_config(page_title="Jarvis Intelligence Suite", layout="wide")

if 'task_completion' not in st.session_state:
    st.session_state.task_completion = {}
if 'original_config' not in st.session_state:
    st.session_state.original_config = None

# --- Logic Core ---
def run_allocation(df, n_sprints, d_count, q_count, limit, d_rate, q_rate):
    df.columns = df.columns.str.strip()
    task_col = next((c for c in df.columns if "Task" in c), df.columns[1])
    hour_col = next((c for c in df.columns if "Hours" in c or "Effort" in c), df.columns[-1])
    df[task_col], df[hour_col] = df[task_col].astype(str), pd.to_numeric(df[hour_col], errors='coerce').fillna(0)
    
    qa_kw = ['QA', 'TESTING', 'TC', 'BUG', 'UAT']
    df['Is_QA'] = df[task_col].apply(lambda x: any(k in x.upper() for k in qa_kw))
    
    clocks = {f"Sprint {s}": {**{f"Dev {i+1}": 0 for i in range(d_count)}, **{f"QA {j+1}": 0 for i in range(q_count)}} for s in range(1, n_sprints + 1)}
    plan, overflows = [], 0

    for _, row in df[~df['Is_QA']].iterrows():
        assigned = False
        for s in range(1, n_sprints + 1):
            devs = sorted([(k, v) for k, v in clocks[f"Sprint {s}"].items() if "Dev" in k], key=lambda x: x[1])
            for d_id, cur_h in devs:
                if cur_h + row[hour_col] <= limit:
                    clocks[f"Sprint {s}"][d_id] += row[hour_col]
                    plan.append({"Sprint": f"Sprint {s}", "Hours": row[hour_col], "Role": "Dev"})
                    assigned = True; break
            if assigned: break
        if not assigned: overflows += 1

    total_est = (df[~df['Is_QA']][hour_col].sum() * d_rate) + (df[df['Is_QA']][hour_col].sum() * q_rate)
    res_health = 1 - (overflows / max(len(df), 1))
    score = (1.0 * 0.4) + (1.0 * 0.3) + (res_health * 0.3) 
    
    return {"score": score, "overflows": overflows, "cost": total_est, "sprints": n_sprints}

# --- Sidebar ---
with st.sidebar:
    st.header("⚙️ Project Setup")
    uploaded_file = st.file_uploader("Upload Work Items", type=['xlsx', 'csv'])
    
    if uploaded_file:
        df_raw = pd.read_excel(uploaded_file) if "xlsx" in uploaded_file.name else pd.read_csv(uploaded_file)
        dev_rate = st.number_input("Dev Rate ($/h)", value=50)
        qa_rate = st.number_input("QA Rate ($/h)", value=40)
        dev_count = st.number_input("Dev Team", 1, 10, 3)
        qa_count = st.number_input("QA Team", 1, 10, 2)
        hrs_limit = st.slider("Max Capacity (hrs)", 20, 100, 64)
        
        if st.button("📌 Lock as 'Original'"):
            st.session_state.original_config = {
                "sprints": st.session_state.get('num_sprints', 4),
                "data": run_allocation(df_raw, st.session_state.get('num_sprints', 4), dev_count, qa_count, hrs_limit, dev_rate, qa_rate)
            }

        st.subheader("🚀 Jarvis AI Optimizer")
        if st.button("Optimize for Grade A"):
            opt_sprints = 2
            while opt_sprints < 20:
                res = run_allocation(df_raw, opt_sprints, dev_count, qa_count, hrs_limit, dev_rate, qa_rate)
                if res['score'] >= 0.9 and res['overflows'] == 0:
                    st.session_state.num_sprints = opt_sprints
                    break
                opt_sprints += 1

        num_sprints = st.slider("Current Sprints", 2, 20, st.session_state.get('num_sprints', 4))

# --- Dashboard ---
if uploaded_file:
    current_res = run_allocation(df_raw, num_sprints, dev_count, qa_count, hrs_limit, dev_rate, qa_rate)
    
    tabs = st.tabs(["🚀 Roadmap", "📊 Comparative Analysis", "📜 Project Charter"])
    
    with tabs[1]:
        st.header("What-If Comparison")
        if st.session_state.original_config:
            orig = st.session_state.original_config['data']
            col_orig, col_opt = st.columns(2)
            
            with col_orig:
                st.subheader("Original Plan")
                st.metric("Sprints", st.session_state.original_config['sprints'])
                st.metric("Health Score", f"{int(orig['score']*100)}%")
                st.metric("Overflow Tasks", orig['overflows'])
                
            with col_opt:
                st.subheader("Jarvis Optimized")
                st.metric("Sprints", current_res['sprints'], delta=int(current_res['sprints'] - st.session_state.original_config['sprints']))
                st.metric("Health Score", f"{int(current_res['score']*100)}%", delta=f"{int((current_res['score'] - orig['score'])*100)}%")
                st.metric("Overflow Tasks", current_res['overflows'], delta=int(current_res['overflows'] - orig['overflows']), delta_color="inverse")
        else:
            st.info("Lock a configuration in the sidebar to enable side-by-side comparison.")

    with tabs[0]:
        st.header("Current Roadmap")
        st.write(f"Grade: {'A' if current_res['score'] >= 0.9 else 'B'}")
        # Standard tracking logic
else:
    st.info("Jarvis: Upload data to access the Comparative Engine.")
