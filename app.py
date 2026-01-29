import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import io

# Dependency check for Excel export
try:
    import xlsxwriter
    EXCEL_SUPPORT = True
except ImportError:
    EXCEL_SUPPORT = False

st.set_page_config(page_title="Jarvis Multi-Sprint Architect", layout="wide")

# --- 1. Persistent Memory ---
if 'master_plan' not in st.session_state:
    st.session_state.master_plan = None
if 'sprint_caps' not in st.session_state:
    st.session_state.sprint_caps = {}
if 'project_dates' not in st.session_state:
    st.session_state.project_dates = {"Start": None, "End": None}

# --- 2. Corrected Distribution Logic ---
def run_sequential_allocation(dev_names, qa_names, lead_names, data, base_cap, num_sprints, start_date, sprint_days, daily_hrs, buffer_pct):
    generated_plan = []
    sprint_metadata = {}

    for i in range(num_sprints):
        s_start = start_date + timedelta(days=i * sprint_days)
        s_end = s_start + timedelta(days=sprint_days - 1)
        s_label = f"Sprint {i}"
        sprint_metadata[s_label] = {"Start": s_start.strftime('%Y-%m-%d'), "End": s_end.strftime('%Y-%m-%d')}

        def assign_balanced(sprint, names, task, role, total_hrs):
            """Distributes hours across all category members for the task."""
            split_hrs = float(total_hrs) / len(names)
            for name in names:
                generated_plan.append({
                    "Sprint": sprint, 
                    "Start Date": sprint_metadata[sprint]["Start"],
                    "End Date": sprint_metadata[sprint]["End"], 
                    "Status": "Not Started",
                    "Task": task, 
                    "Owner": name, 
                    "Role": role, 
                    "Hours": round(split_hrs, 1)
                })

        # Logic Fix: Ensuring distribution across ALL available middle/execution sprints
        # Sprint 0: Kickoff & Setup
        if i == 0:
            assign_balanced(s_label, lead_names, "Analysis Phase", "Lead", data["Analysis"])
            assign_balanced(s_label, qa_names, "TC preparation", "QA", data["TC_Prep"])
        
        # Sprint 1 to Penultimate: Execution (Works even if only 3 sprints total)
        if 0 < i < (num_sprints - 1) or (num_sprints == 2 and i == 1):
            # Calculate how many sprints are in the "execution" phase
            exec_sprints = max(1, num_sprints - 2) if num_sprints > 2 else 1
            assign_balanced(s_label, dev_names, "Development Phase", "Dev", data["Dev"]/exec_sprints)
            assign_balanced(s_label, lead_names, "Code Review", "Lead", data["Review"]/exec_sprints)
            assign_balanced(s_label, qa_names, "QA testing", "QA", data["QA_Test"]/exec_sprints)
            assign_balanced(s_label, qa_names, "Integration Testing", "QA", data["Integ"]/exec_sprints)
        
        # Final Sprint: Hardening & Release
        if i == (num_sprints - 1) and i > 0:
            assign_balanced(s_label, dev_names, "Bug Fixes", "Dev", data["Fixes"])
            assign_balanced(s_label, qa_names, "Bug retest", "QA", data["Retest"])
            assign_balanced(s_label, qa_names, "Smoke test", "QA", data["Smoke"])
            assign_balanced(s_label, ["DevOps"], "Merge and Deploy", "Ops", data["Deploy"])

    sprint_caps = {f"Sprint {i}": max((base_cap) * (1 - (buffer_pct / 100)), 0.1) for i in range(num_sprints)}
    return pd.DataFrame(generated_plan), sprint_caps, sprint_metadata, start_date, start_date + timedelta(days=num_sprints * sprint_days - 1)

# --- 3. Sidebar ---
with st.sidebar:
    st.header("👥 Team Setup")
    c_d, c_q, c_l = st.columns(3)
    d_count = c_d.number_input("Devs", 1, 20, 3)
    q_count = c_q.number_input("QA", 1, 20, 1)
    l_count = c_l.number_input("Leads", 1, 10, 1)
    
    st.divider()
    dev_names = [st.text_input(f"Dev {i+1}", f"Dev_{i+1}", key=f"d_{i}") for i in range(d_count)]
    qa_names = [st.text_input(f"QA {i+1}", f"QA_{i+1}", key=f"q_{i}") for i in range(q_count)]
    lead_names = [st.text_input(f"Lead {i+1}", f"Lead_{i+1}", key=f"l_{i}") for i in range(l_count)]
    
    # Resource Swap
    if st.session_state.master_plan is not None:
        st.divider()
        st.header("🔄 Swap Resource")
        original = st.selectbox("Replace", st.session_state.master_plan['Owner'].unique())
        replacement = st.text_input("New Name")
        if st.button("Apply Swap"):
            st.session_state.master_plan['Owner'] = st.session_state.master_plan['Owner'].replace(original, replacement)
            st.rerun()

    st.divider()
    st.header("📅 Timeline Settings")
    start_date_input = st.date_input("Start Date", datetime(2026, 2, 9))
    num_sprints_input = st.selectbox("Total Sprints", range(2, 11), index=1) # Defaulting to 3
    sprint_days_input = st.number_input("Sprint Days", 1, 30, 14)
    daily_hrs_input = st.slider("Daily Hrs/Person", 4, 12, 8)
    buffer_pct_input = st.slider("Buffer (%)", 0, 50, 10)

# --- 4. Main UI ---
st.title("Jarvis Phase-Gate Manager")

with st.expander("📥 Effort Baseline (Unrestricted)", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        analysis = st.number_input("Analysis Phase", value=25.0); dev_h = st.number_input("Development Phase", value=150.0)
        fixes = st.number_input("Bug Fixes", value=30.0); review = st.number_input("Code Review", value=20.0)
    with col2:
        qa_h = st.number_input("QA testing", value=80.0); tc_p = st.number_input("TC preparation", value=40.0)
        retest = st.number_input("Bug retest", value=15.0); integ = st.number_input("Integration Testing", value=20.0)
        smoke = st.number_input("Smoke test", value=8.0); deploy = st.number_input("Merge and Deploy", value=6.0)

if st.button("🚀 GENERATE INITIAL PLAN", type="primary", use_container_width=True):
    inputs = {"Analysis": analysis, "Dev": dev_h, "Fixes": fixes, "Review": review, "QA_Test": qa_h, 
              "TC_Prep": tc_p, "Retest": retest, "Integ": integ, "Smoke": smoke, "Deploy": deploy}
    plan, caps, meta, p_start, p_end = run_sequential_allocation(dev_names, qa_names, lead_names, inputs, sprint_days_input*daily_hrs_input, num_sprints_input, start_date_input, sprint_days_input, daily_hrs_input, buffer_pct_input)
    st.session_state.master_plan = plan
    st.session_state.sprint_caps = caps; st.session_state.sprint_meta = meta; st.session_state.project_dates = {"Start": p_start, "End": p_end}
    st.rerun()

# --- 5. Visual Analytics ---
if st.session_state.master_plan is not None:
    # Utilization Gauge
    total_hours = st.session_state.master_plan['Hours'].sum()
    total_cap = sum(st.session_state.sprint_caps.values()) * (d_count + q_count + l_count)
    util_pct = (total_hours / total_cap) * 100
    gauge_fig = go.Figure(go.Indicator(mode="gauge+number", value=util_pct, title={'text': "Project Capacity Utilization (%)"},
                                      gauge={'axis': {'range': [None, 120]}, 'bar': {'color': "red" if util_pct > 100 else "green"}}))
    st.plotly_chart(gauge_fig, use_container_width=True)

    st.subheader("📊 Sprint Workload Balance")
    util_fig = px.bar(st.session_state.master_plan, x="Sprint", y="Hours", color="Owner", barmode="group", text_auto='.1f')
    st.plotly_chart(util_fig, use_container_width=True)

    st.subheader("📝 Roadmap Editor")
    st.session_state.master_plan = st.data_editor(st.session_state.master_plan, use_container_width=True, key="master_edit")

    if EXCEL_SUPPORT:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
            st.session_state.master_plan.to_excel(writer, index=False, sheet_name="FullRoadmap")
        st.download_button("📥 EXPORT TO EXCEL", data=buf.getvalue(), file_name="Jarvis_Roadmap.xlsx")

if st.button("🗑️ Reset All"):
    st.session_state.master_plan = None
    st.rerun()
