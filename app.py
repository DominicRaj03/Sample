import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import io

# Dependency check for Excel
try:
    import xlsxwriter
    EXCEL_SUPPORT = True
except ImportError:
    EXCEL_SUPPORT = False

st.set_page_config(page_title="Jarvis Resource Architect", layout="wide")

# --- 1. Persistent Memory ---
if 'master_plan' not in st.session_state:
    st.session_state.master_plan = None
if 'sprint_caps' not in st.session_state:
    st.session_state.sprint_caps = {}
if 'project_dates' not in st.session_state:
    st.session_state.project_dates = {"Start": None, "End": None}

# --- 2. Allocation Logic ---
def run_sequential_allocation(dev_names, qa_names, lead_names, data, base_cap, num_sprints, start_date, sprint_days, daily_hrs, buffer_pct):
    generated_plan = []
    sprint_list = [f"Sprint {i}" for i in range(num_sprints)]
    all_staff = dev_names + qa_names + lead_names + ["DevOps"]
    resource_load = {s: {name: 0 for name in all_staff} for s in sprint_list}
    sprint_caps = {}
    
    for i in range(num_sprints):
        s_start = start_date + timedelta(days=i * sprint_days)
        s_end = s_start + timedelta(days=sprint_days - 1)
        sprint_caps[f"Sprint {i}"] = max((base_cap) * (1 - (buffer_pct / 100)), 0.1)

        def assign(sprint, names, task, role, hrs):
            owner = min(names, key=lambda x: resource_load[sprint][x])
            resource_load[sprint][owner] += hrs
            return {
                "Sprint": sprint, 
                "Start_Date": s_start,
                "End_Date": s_end,
                "Status": "Not Started",
                "Task": task, 
                "Owner": owner, 
                "Hours": float(hrs)
            }

        if i == 0:
            generated_plan.append(assign(f"Sprint {i}", lead_names, "Analysis Phase", "Lead", data["Analysis"]))
            generated_plan.append(assign(f"Sprint {i}", qa_names, "TC Prep (60%)", "QA", data["TC_Prep"] * 0.6))
        elif 0 < i < (num_sprints - 1):
            div = max(1, num_sprints-2)
            generated_plan.append(assign(f"Sprint {i}", dev_names, "Development Work", "Dev", data["Dev"]/div))
        elif i == (num_sprints - 1):
            generated_plan.append(assign(f"Sprint {i}", ["DevOps"], "Deployment", "Ops", data["Deploy"]))
            generated_plan.append(assign(f"Sprint {i}", qa_names, "Smoke Test", "QA", data["Smoke"]))

    return pd.DataFrame(generated_plan), sprint_caps, start_date, start_date + timedelta(days=num_sprints * sprint_days - 1)

# --- 3. Sidebar ---
with st.sidebar:
    st.header("👥 Team Setup")
    d_count = st.number_input("Devs", 1, 10, 3); q_count = st.number_input("QA", 1, 10, 1); l_count = st.number_input("Leads", 1, 5, 1)
    dev_names = [st.text_input(f"Dev {i+1}", f"D{i+1}", key=f"dn_{i}") for i in range(d_count)]
    qa_names = [st.text_input(f"QA {i+1}", f"Q{i+1}", key=f"qn_{i}") for i in range(q_count)]
    lead_names = [st.text_input(f"Lead {i+1}", f"L{i+1}", key=f"ln_{i}") for i in range(l_count)]
    st.header("📅 Timeline Settings")
    start_date_input = st.date_input("Project Start Date", datetime.now())
    num_sprints = st.selectbox("Total Sprints", range(2, 11), index=3)
    sprint_days = 14; daily_hrs = 8; buffer_pct = 10
    max_cap_base = sprint_days * daily_hrs

# --- 4. Main UI ---
st.title("Jarvis Phase-Gate Manager")

if st.session_state.master_plan is not None:
    # Top Level Overview
    st.subheader("📊 Project Vital Signs")
    completed_total = st.session_state.master_plan[st.session_state.master_plan['Status'] == 'Completed']['Hours'].sum()
    total_h = st.session_state.master_plan['Hours'].sum()
    pct_total = (completed_total / total_h * 100) if total_h > 0 else 0
    
    o1, o2, o3 = st.columns([1, 1, 2])
    o1.metric("Start Date", st.session_state.project_dates["Start"].strftime('%Y-%m-%d'))
    o2.metric("End Date", st.session_state.project_dates["End"].strftime('%Y-%m-%d'))
    with o3:
        st.progress(pct_total / 100, text=f"Overall Project Completion: {pct_total:.1f}%")

with st.expander("📥 Effort Baseline"):
    inputs = {"Analysis": st.number_input("Analysis", 25.0), "Dev": 150.0, "TC_Prep": 40.0, "Smoke": 8.0, "Deploy": 6.0}

if st.button("🚀 GENERATE INITIAL PLAN", type="primary", use_container_width=True):
    plan, caps, p_start, p_end = run_sequential_allocation(dev_names, qa_names, lead_names, inputs, max_cap_base, num_sprints, start_date_input, sprint_days, daily_hrs, buffer_pct)
    st.session_state.master_plan = plan
    st.session_state.sprint_caps = caps
    st.session_state.project_dates = {"Start": p_start, "End": p_end}
    st.rerun()

# --- 5. Execution Section ---
if st.session_state.master_plan is not None:
    # Resource Specific Gauges
    st.subheader("👤 Individual Resource Performance")
    resources = st.session_state.master_plan['Owner'].unique()
    cols = st.columns(len(resources))
    
    for idx, member in enumerate(resources):
        member_data = st.session_state.master_plan[st.session_state.master_plan['Owner'] == member]
        m_total = member_data['Hours'].sum()
        m_done = member_data[member_data['Status'] == 'Completed']['Hours'].sum()
        m_pct = (m_done / m_total * 100) if m_total > 0 else 0
        
        with cols[idx]:
            fig = go.Figure(go.Indicator(
                mode = "gauge+number", value = m_pct,
                title = {'text': f"{member}", 'font': {'size': 14}},
                gauge = {'axis': {'range': [0, 100]}, 'bar': {'color': "#636efa"}}
            ))
            fig.update_layout(height=180, margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("📝 Roadmap Editor")
    st.session_state.master_plan = st.data_editor(
        st.session_state.master_plan, use_container_width=True, key="main_editor",
        column_config={
            "Status": st.column_config.SelectboxColumn("Status", options=["Not Started", "In Progress", "Completed"], required=True),
            "Hours": st.column_config.NumberColumn("Hours", format="%.1f"),
            "Start_Date": None, "End_Date": None
        }
    )

if st.button("🗑️ Reset All"):
    st.session_state.master_plan = None
    st.rerun()
