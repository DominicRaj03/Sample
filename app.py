import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
from datetime import datetime, timedelta

st.set_page_config(page_title="Jarvis Critical Path Suite", layout="wide")

if 'task_completion' not in st.session_state:
    st.session_state.task_completion = {}
if 'num_sprints' not in st.session_state:
    st.session_state.num_sprints = 4

# --- Logic Core ---
def run_allocation(df, n_sprints, d_count, q_count, limit, d_rate, q_rate):
    df.columns = df.columns.str.strip()
    task_col = next((c for c in df.columns if "Task" in c), df.columns[1])
    hour_col = next((c for c in df.columns if "Hours" in c or "Effort" in c), df.columns[-1])
    
    local_df = df.copy()
    local_df[task_col] = local_df[task_col].astype(str)
    local_df[hour_col] = pd.to_numeric(local_df[hour_col], errors='coerce').fillna(0)
    
    qa_kw = ['QA', 'TESTING', 'TC', 'BUG', 'UAT']
    local_df['Is_QA'] = local_df[task_col].apply(lambda x: any(k in x.upper() for k in qa_kw))
    
    clocks = {f"Sprint {s}": {**{f"Dev {i+1}": 0 for i in range(d_count)}, **{f"QA {j+1}": 0 for j in range(q_count)}} for s in range(1, n_sprints + 1)}
    plan, overflows = [], 0

    for _, row in local_df[~local_df['Is_QA']].iterrows():
        assigned = False
        for s in range(1, n_sprints + 1):
            s_n = f"Sprint {s}"
            devs = sorted([(k, v) for k, v in clocks[s_n].items() if "Dev" in k], key=lambda x: x[1])
            for d_id, cur_h in devs:
                if cur_h + row[hour_col] <= limit:
                    clocks[s_n][d_id] += row[hour_col]
                    # Slack Calc: If remaining capacity is < 10% of limit, mark as Critical
                    is_critical = (limit - (cur_h + row[hour_col])) < (0.1 * limit)
                    plan.append({"Sprint": s_n, "Hours": row[hour_col], "Role": "Dev", "Task": row[task_col], "Critical": is_critical})
                    assigned = True; break
            if assigned: break
        if not assigned: overflows += 1

    total_est = (local_df[~local_df['Is_QA']][hour_col].sum() * d_rate) + (local_df[local_df['Is_QA']][hour_col].sum() * q_rate)
    res_health = 1 - (overflows / max(len(local_df), 1))
    score = (1.0 * 0.4) + (1.0 * 0.3) + (res_health * 0.3) 
    
    return {"score": score, "overflows": overflows, "cost": total_est, "sprints": n_sprints, "plan": pd.DataFrame(plan)}

# --- Sidebar ---
with st.sidebar:
    st.header("⚙️ Project Setup")
    uploaded_file = st.file_uploader("Upload Work Items", type=['xlsx', 'csv'])
    
    if uploaded_file:
        df_input = pd.read_excel(uploaded_file) if "xlsx" in uploaded_file.name else pd.read_csv(uploaded_file)
        dev_rate = st.number_input("Dev Rate ($/h)", value=50)
        qa_rate = st.number_input("QA Rate ($/h)", value=40)
        dev_count = st.number_input("Dev Team", 1, 10, 3)
        qa_count = st.number_input("QA Team", 1, 10, 2)
        hrs_limit = st.slider("Max Capacity (hrs)", 20, 100, 64)
        
        st.subheader("🚀 Jarvis AI Optimizer")
        if st.button("Optimize for Grade A"):
            opt_sprints = 2
            while opt_sprints < 20:
                res = run_allocation(df_input, opt_sprints, dev_count, qa_count, hrs_limit, dev_rate, qa_rate)
                if res['score'] >= 0.9 and res['overflows'] == 0:
                    st.session_state.num_sprints = opt_sprints
                    st.rerun()
                    break
                opt_sprints += 1

        num_sprints = st.slider("Current Sprints", 2, 20, value=st.session_state.num_sprints)
        st.session_state.num_sprints = num_sprints

# --- Dashboard ---
if uploaded_file:
    current_res = run_allocation(df_input, st.session_state.num_sprints, dev_count, qa_count, hrs_limit, dev_rate, qa_rate)
    
    tabs = st.tabs(["🚀 Strategic Roadmap", "📊 Risk Analysis", "💬 Feedback"])
    
    with tabs[0]:
        st.header("Execution Roadmap")
        st.caption("🔴 Red tasks are on the Critical Path (Zero Slack Time)")
        
        for s in range(1, st.session_state.num_sprints + 1):
            s_name = f"Sprint {s}"
            with st.expander(f"📅 {s_name} Schedule"):
                s_plan = current_res['plan'][current_res['plan']['Sprint'] == s_name]
                for _, row in s_plan.iterrows():
                    label = f"**{row['Task']}** (Critical)" if row['Critical'] else row['Task']
                    color = "red" if row['Critical'] else "black"
                    st.markdown(f"<span style='color:{color};'>{label}</span> - {row['Hours']}h", unsafe_allow_html=True)

    with tabs[1]:
        st.header("Project Risk Assessment")
        c1, c2 = st.columns(2)
        critical_count = current_res['plan']['Critical'].sum()
        c1.metric("Critical Tasks", int(critical_count))
        c2.metric("Project Slack Health", f"{int((1 - (critical_count/len(current_res['plan'])))*100)}%")
        
        # Risk Distribution
        fig = px.pie(current_res['plan'], names='Critical', title='Proportion of Critical vs. Flexible Tasks',
                     color='Critical', color_discrete_map={True: '#E74C3C', False: '#2ECC71'})
        st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Jarvis: Please upload a file to view the Critical Path.")
