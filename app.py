import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import io

st.set_page_config(page_title="Jarvis Executive Architect", layout="wide")

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
        cap = max((base_cap) * (1 - (buffer_pct / 100)), 0.1)
        sprint_caps[f"Sprint {i}"] = cap

        def assign(sprint, names, task, role, hrs):
            owner = min(names, key=lambda x: resource_load[sprint][x])
            resource_load[sprint][owner] += hrs
            return {
                "Sprint": sprint, "Start_Date": s_start, "End_Date": s_end,
                "Status": "Not Started", "Task": task, "Owner": owner, 
                "Role": role, "Hours": float(hrs)
            }

        if i == 0:
            generated_plan.append(assign(f"Sprint {i}", lead_names, "Analysis Phase", "Lead", data["Analysis"]))
            generated_plan.append(assign(f"Sprint {i}", qa_names, "TC preparation", "QA", data["TC_Prep"]))
        elif 0 < i < (num_sprints - 1):
            div = max(1, num_sprints - 2)
            generated_plan.append(assign(f"Sprint {i}", dev_names, "Development Phase", "Dev", data["Dev"]/div))
            generated_plan.append(assign(f"Sprint {i}", lead_names, "Code Review", "Lead", data["Review"]/div))
            generated_plan.append(assign(f"Sprint {i}", qa_names, "QA testing", "QA", data["QA_Test"]/div))
            generated_plan.append(assign(f"Sprint {i}", qa_names, "Integration Testing", "QA", data["Integ"]/div))
        elif i == (num_sprints - 1):
            generated_plan.append(assign(f"Sprint {i}", dev_names, "Bug Fixes", "Dev", data["Fixes"]))
            generated_plan.append(assign(f"Sprint {i}", qa_names, "Bug retest", "QA", data["Retest"]))
            generated_plan.append(assign(f"Sprint {i}", qa_names, "Smoke test", "QA", data["Smoke"]))
            generated_plan.append(assign(f"Sprint {i}", ["DevOps"], "Merge and Deploy", "Ops", data["Deploy"]))

    return pd.DataFrame(generated_plan), sprint_caps

# --- 3. Sidebar ---
with st.sidebar:
    st.header("👥 Team List")
    d_names = [st.text_input(f"Dev {i+1}", f"D{i+1}", key=f"d_{i}") for i in range(3)]
    q_names = [st.text_input(f"QA {i+1}", f"Q{i+1}", key=f"q_{i}") for i in range(1)]
    l_names = [st.text_input(f"Lead {i+1}", f"L{i+1}", key=f"l_{i}") for i in range(1)]
    
    st.divider()
    daily_hrs = st.slider("Individual Daily Hrs", 4, 12, 8)
    buffer_pct = st.slider("Capacity Buffer (%)", 0, 50, 10)
    num_sprints = st.selectbox("Total Sprints", range(2, 11), index=3)
    start_date_input = st.date_input("Start Date", datetime(2026, 2, 9))

# --- 4. Main UI ---
st.title("Jarvis Phase-Gate Manager")

if st.session_state.project_dates["Start"]:
    c1, c2, c3 = st.columns([1, 1, 2])
    c1.metric("Start Date", st.session_state.project_dates["Start"].strftime('%Y-%m-%d'))
    c2.metric("End Date", st.session_state.project_dates["End"].strftime('%Y-%m-%d'))
    with c3:
        done = st.session_state.master_plan[st.session_state.master_plan['Status'] == 'Completed']['Hours'].sum()
        total = st.session_state.master_plan['Hours'].sum()
        st.progress((done/total) if total > 0 else 0, text=f"Overall Project Completion: {(done/total*100):.1f}%")

with st.expander("📥 Effort Baseline", expanded=True):
    col_a, col_b = st.columns(2)
    with col_a:
        analysis = st.number_input("Analysis Phase", 25.0); dev = st.number_input("Development Phase", 150.0)
        fixes = st.number_input("Bug Fixes", 30.0); review = st.number_input("Code Review", 20.0)
    with col_b:
        qa_t = st.number_input("QA testing", 80.0); tc_p = st.number_input("TC preparation", 40.0)
        retest = st.number_input("Bug retest", 15.0); integ = st.number_input("Integration Testing", 20.0)
        smoke = st.number_input("Smoke test", 8.0); deploy = st.number_input("Merge and Deploy", 6.0)

if st.button("🚀 GENERATE INITIAL PLAN", type="primary", use_container_width=True):
    inputs = {"Analysis": analysis, "Dev": dev, "Fixes": fixes, "Review": review, "QA_Test": qa_t, 
              "TC_Prep": tc_p, "Retest": retest, "Integ": integ, "Smoke": smoke, "Deploy": deploy}
    plan, caps = run_sequential_allocation(d_names, q_names, l_names, inputs, 14*daily_hrs, num_sprints, start_date_input, 14, daily_hrs, buffer_pct)
    st.session_state.master_plan = plan
    st.session_state.sprint_caps = caps
    st.session_state.project_dates = {"Start": start_date_input, "End": start_date_input + timedelta(days=num_sprints*14-1)}
    st.rerun()

# --- 5. Summary & Editor Section ---
if st.session_state.master_plan is not None:
    st.subheader("📋 Sprint Overview Summary")
    summary = st.session_state.master_plan.groupby('Sprint').agg({'Hours': 'sum'}).reset_index()
    summary['Capacity'] = summary['Sprint'].map(st.session_state.sprint_caps)
    summary['Utilization %'] = (summary['Hours'] / summary['Capacity'] * 100).round(1).astype(str) + '%'
    st.table(summary)

    st.subheader("🔍 Roadmap Editor")
    role_filter = st.multiselect("Filter by Role", options=st.session_state.master_plan['Role'].unique(), default=st.session_state.master_plan['Role'].unique())
    display_df = st.session_state.master_plan[st.session_state.master_plan['Role'].isin(role_filter)].copy()
    
    st.session_state.master_plan = st.data_editor(
        display_df, use_container_width=True, key="main_editor",
        column_config={
            "Status": st.column_config.SelectboxColumn("Status", options=["Not Started", "In Progress", "Completed"]),
            "Hours": st.column_config.NumberColumn("Hours", format="%.2f"),
            "Start_Date": None, "End_Date": None
        }
    )

if st.button("🗑️ Reset All"):
    st.session_state.master_plan = None
    st.rerun()
