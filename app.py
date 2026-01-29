import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import io

st.set_page_config(page_title="Jarvis Sequential Architect", layout="wide")

# --- 1. Persistent Memory ---
if 'master_plan' not in st.session_state:
    st.session_state.master_plan = None
if 'sprint_caps' not in st.session_state:
    st.session_state.sprint_caps = {}
if 'project_dates' not in st.session_state:
    st.session_state.project_dates = {"Start": None, "End": None}

# --- 2. New Sequential Logic ---
def run_sequential_allocation(dev_names, qa_names, lead_names, data, base_cap, num_sprints, start_date, sprint_days, daily_hrs, buffer_pct):
    generated_plan = []
    sprint_metadata = {}

    for i in range(num_sprints):
        s_start = start_date + timedelta(days=i * sprint_days)
        s_end = s_start + timedelta(days=sprint_days - 1)
        s_label = f"Sprint {i}"
        sprint_metadata[s_label] = {"Start": s_start.strftime('%Y-%m-%d'), "End": s_end.strftime('%Y-%m-%d')}

        def assign_balanced(sprint, names, task, role, total_hrs):
            split_hrs = float(total_hrs) / len(names)
            for name in names:
                generated_plan.append({
                    "Sprint": sprint, "Start Date": sprint_metadata[sprint]["Start"],
                    "End Date": sprint_metadata[sprint]["End"], "Status": "Not Started",
                    "Task": task, "Owner": name, "Role": role, "Hours": round(split_hrs, 1)
                })

        # --- FLOW IMPLEMENTATION ---
        
        # SPRINT 0: FOUNDATION
        if i == 0:
            assign_balanced(s_label, lead_names, "Requirement/Analysis Phase", "Lead", data["Analysis"])
            assign_balanced(s_label, qa_names, "TC Preparation", "QA", data["TC_Prep"])
        
        # SPRINT 1: CORE EXECUTION
        elif i == 1 or (num_sprints == 2 and i == 1):
            assign_balanced(s_label, dev_names, "Development Phase", "Dev", data["Dev"])
            assign_balanced(s_label, lead_names, "Code Review (Initial)", "Lead", data["Review"])
            assign_balanced(s_label, qa_names, "QA Testing", "QA", data["QA_Test"])
            assign_balanced(s_label, dev_names, "Bug Fixes (Initial)", "Dev", data["Fixes"] * 0.7) # Majority of fixes
            assign_balanced(s_label, lead_names, "Code Review (Bug Fixes)", "Lead", data["Review"] * 0.3)
            assign_balanced(s_label, qa_names, "Bug Retest", "QA", data["Retest"] * 0.7)

        # SPRINT 2+ (or Final Sprint): HARDENING & RELEASE
        if i == (num_sprints - 1) and i > 0:
            assign_balanced(s_label, qa_names, "Integration Testing", "QA", data["Integ"])
            assign_balanced(s_label, dev_names, "Bug Fixes (Integration)", "Dev", data["Fixes"] * 0.3)
            assign_balanced(s_label, qa_names, "Bug Retest (Integration)", "QA", data["Retest"] * 0.3)
            assign_balanced(s_label, ["DevOps"], "Merge and Deploy", "Ops", data["Deploy"])
            assign_balanced(s_label, qa_names, "Smoke Test", "QA", data["Smoke"])

    sprint_caps = {f"Sprint {i}": max((base_cap) * (1 - (buffer_pct / 100)), 0.1) for i in range(num_sprints)}
    return pd.DataFrame(generated_plan), sprint_caps, sprint_metadata, start_date, start_date + timedelta(days=num_sprints * sprint_days - 1)

# --- 3. Sidebar Configuration ---
with st.sidebar:
    st.header("👥 Team Configuration")
    c_d, c_q, c_l = st.columns(3)
    d_count = c_d.number_input("Devs", 1, 10, 3)
    q_count = c_q.number_input("QA", 1, 10, 1)
    l_count = c_l.number_input("Leads", 1, 10, 1)
    
    st.divider()
    dev_names = [st.text_input(f"Dev {j+1}", f"Dev_{j+1}", key=f"d_{j}") for j in range(d_count)]
    qa_names = [st.text_input(f"QA {j+1}", f"QA_{j+1}", key=f"q_{j}") for j in range(q_count)]
    lead_names = [st.text_input(f"Lead {j+1}", f"Lead_{j+1}", key=f"l_{j}") for j in range(l_count)]
    
    st.divider()
    st.header("📅 Timeline Settings")
    start_date_input = st.date_input("Start Date", datetime(2026, 2, 9))
    num_sprints_input = st.selectbox("Total Sprints", range(2, 11), index=1) # Defaults to 3
    sprint_days_input = st.number_input("Sprint Days", 1, 30, 14)
    daily_hrs_input = st.slider("Daily Hrs/Person", 4, 12, 8)
    buffer_pct_input = st.slider("Buffer (%)", 0, 50, 0)

# --- 4. Main UI ---
st.title("Jarvis Phase-Gate Manager")

with st.expander("📥 Effort Baseline (Unrestricted)", expanded=True):
    c1, c2 = st.columns(2)
    with c1:
        analysis = st.number_input("Requirement/Analysis Phase", value=25.0)
        dev_h = st.number_input("Development Phase", value=150.0)
        review = st.number_input("Code Review", value=20.0)
        fixes = st.number_input("Bug Fixes (Total)", value=30.0)
    with c2:
        qa_h = st.number_input("QA Testing", value=80.0)
        tc_p = st.number_input("TC Preparation", value=40.0)
        retest = st.number_input("Bug Retest (Total)", value=15.0)
        integ = st.number_input("Integration Testing", value=20.0)
        smoke = st.number_input("Smoke Test", value=8.0)
        deploy = st.number_input("Merge and Deploy", value=6.0)

if st.button("🚀 GENERATE SEQUENTIAL PLAN", type="primary", use_container_width=True):
    inputs = {"Analysis": analysis, "Dev": dev_h, "Fixes": fixes, "Review": review, "QA_Test": qa_h, 
              "TC_Prep": tc_p, "Retest": retest, "Integ": integ, "Smoke": smoke, "Deploy": deploy}
    plan, caps, meta, p_start, p_end = run_sequential_allocation(dev_names, qa_names, lead_names, inputs, sprint_days_input*daily_hrs_input, num_sprints_input, start_date_input, sprint_days_input, daily_hrs_input, buffer_pct_input)
    st.session_state.master_plan = plan
    st.session_state.sprint_caps = caps; st.session_state.sprint_meta = meta; st.session_state.project_dates = {"Start": p_start, "End": p_end}
    st.rerun()

# --- 5. Roadmap Display ---
if st.session_state.master_plan is not None:
    st.subheader("📊 Balanced Resource Workload")
    util_fig = px.bar(st.session_state.master_plan, x="Sprint", y="Hours", color="Owner", barmode="group", text_auto='.1f', title="Hours Split per Sprint")
    st.plotly_chart(util_fig, use_container_width=True)

    st.subheader("📝 Roadmap Editor (Sequential Flow Applied)")
    st.session_state.master_plan = st.data_editor(st.session_state.master_plan, use_container_width=True, key="master_edit")

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
        st.session_state.master_plan.to_excel(writer, index=False, sheet_name="Sequential_Roadmap")
    st.download_button("📥 EXPORT SEQUENTIAL PLAN", data=buf.getvalue(), file_name="Jarvis_Sequential_Flow.xlsx")

if st.button("🗑️ Reset All"):
    st.session_state.master_plan = None
    st.rerun()
