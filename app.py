import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="Jarvis Burnup Architect", layout="wide")

# --- Session State ---
if 'manual_overrides' not in st.session_state:
    st.session_state.manual_overrides = {}
if 'resource_away' not in st.session_state:
    st.session_state.resource_away = {}

# --- Logic Core ---
def run_architect_allocation(dev_names, qa_names, splits):
    plan = []
    resource_load = {f"Sprint {i}": {name: 0 for name in dev_names + qa_names + ["Designer", "Lead", "DevOps"]} for i in range(5)}

    def assign_work(sprint, names, task_name, role, hours):
        ov_key = f"{sprint}_{task_name}"
        if ov_key in st.session_state.manual_overrides:
            owner = st.session_state.manual_overrides[ov_key]
        else:
            avail = [n for n in names if not st.session_state.resource_away.get(f"{sprint}_{n}", False)]
            owner = min(avail, key=lambda x: resource_load[sprint][x]) if avail else names[0]
        
        resource_load[sprint][owner] += hours
        return {"Sprint": sprint, "Task": task_name, "Owner": owner, "Role": role, "Hours": hours}

    # Sprint 0: Analysis
    plan.append(assign_work("Sprint 0", ["Lead"], "Requirements Analysis", "Lead", splits['Analysis']))
    plan.append(assign_work("Sprint 0", ["Designer"], "UI/UX & Documentation", "Design", splits['Doc']))

    # Sprint 1 & 2: Development
    dev_per_sprint = splits['TotalDev'] / 2
    for s_idx in ["Sprint 1", "Sprint 2"]:
        hrs_per_dev = dev_per_sprint / len(dev_names)
        for d_name in dev_names:
            plan.append(assign_work(s_idx, [d_name], f"Core Dev: {d_name}", "Dev", hrs_per_dev))

    # Sprint 3: QA & Fixes
    plan.append(assign_work("Sprint 3", qa_names, "QA Execution", "QA", splits['QA']))
    plan.append(assign_work("Sprint 3", dev_names, "Bug Fixing", "Dev", splits['Fixes']))
    plan.append(assign_work("Sprint 3", qa_names, "Bug Retesting", "QA", splits['Retest']))

    # Sprint 4: Deployment
    plan.append(assign_work("Sprint 4", ["DevOps"], "Deployment", "Ops", splits['Deploy']))
    
    return pd.DataFrame(plan)

# --- Sidebar ---
with st.sidebar:
    st.header("⚙️ Project Inputs")
    sprint_days = st.number_input("Sprint Days", 1, 30, 12)
    daily_hrs = st.slider("Daily Hours", 4, 12, 8)
    max_cap = sprint_days * daily_hrs
    
    st.divider()
    s_total_dev = st.number_input("Total Dev Hours", 0, 2000, 160)
    s_analysis = st.number_input("Analysis", 0, 500, 40)
    s_qa = st.number_input("QA Phase", 0, 500, 80)
    s_fixes = st.number_input("Bug Fixes", 0, 500, 40)
    s_retest = st.number_input("Retest", 0, 500, 20)
    s_doc = st.number_input("Documentation", 0, 500, 30)
    s_deploy = st.number_input("Deployment", 0, 500, 16)
    
    splits = {
        'TotalDev': s_total_dev, 'Analysis': s_analysis, 'QA': s_qa, 
        'Fixes': s_fixes, 'Retest': s_retest, 'Doc': s_doc, 'Deploy': s_deploy
    }

    st.header("👥 Team")
    d_size = st.number_input("Dev Size", 1, 10, 2)
    q_size = st.number_input("QA Size", 1, 10, 1)
    dev_names = [st.text_input(f"Dev {i+1}", f"Dev {i+1}", key=f"dn_{i}") for i in range(d_size)]
    qa_names = [st.text_input(f"QA {i+1}", f"Tester {i+1}", key=f"qn_{i}") for i in range(q_size)]

# --- Main App ---
final_plan = run_architect_allocation(dev_names, qa_names, splits)

tabs = st.tabs(["🚀 Burnup Chart", "📋 Sprint Details", "📈 Resource Load"])

with tabs[0]:
    st.header("Project Burnup")
    
    # Calculate cumulative work
    sprints = [f"Sprint {i}" for i in range(5)]
    total_hours_needed = sum(splits.values())
    
    cumulative_work = []
    current_sum = 0
    for s in sprints:
        current_sum += final_plan[final_plan['Sprint'] == s]['Hours'].sum()
        cumulative_work.append(current_sum)
        
    fig = go.Figure()
    # Ideal Total Scope Line
    fig.add_trace(go.Scatter(x=sprints, y=[total_hours_needed]*5, name="Total Scope", line=dict(color='red', dash='dash')))
    # Work Completion Line
    fig.add_trace(go.Scatter(x=sprints, y=cumulative_work, name="Cumulative Work", fill='tozeroy', line=dict(color='green')))
    
    fig.update_layout(title="Project Hours Burnup", xaxis_title="Sprints", yaxis_title="Hours")
    st.plotly_chart(fig, use_container_width=True)

with tabs[1]:
    for i in range(5):
        s_name = f"Sprint {i}"
        s_data = final_plan[final_plan['Sprint'] == s_name]
        res_sum = s_data.groupby('Owner')['Hours'].sum()
        over = res_sum[res_sum > max_cap]
        
        with st.expander(f"{s_name} | Status: {'⚠️' if not over.empty else '✅'}"):
            c1, c2 = st.columns([1, 2])
            with c1:
                for owner, h in res_sum.items():
                    color = "red" if h > max_cap else "green"
                    st.markdown(f"**{owner}:** <span style='color:{color};'>{h}h / {max_cap}h</span>", unsafe_allow_html=True)
            with c2:
                st.dataframe(s_data[['Task', 'Owner', 'Hours']], hide_index=True)

with tabs[2]:
    load_df = final_plan.groupby(['Sprint', 'Owner'])['Hours'].sum().reset_index()
    st.plotly_chart(px.bar(load_df, x="Sprint", y="Hours", color="Owner", barmode="group"))
