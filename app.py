import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import io

# Config
st.set_page_config(page_title="Jarvis - Sprint planning", layout="wide")

# --- 1. Persistent Data Management ---
if 'master_plan' not in st.session_state:
    st.session_state.master_plan = None
if 'release_quality' not in st.session_state:
    st.session_state.release_quality = pd.DataFrame()
if 'team_setup' not in st.session_state:
    st.session_state.team_setup = {"devs": [], "qas": [], "leads": [], "capacity": 0}
if 'planning_inputs' not in st.session_state:
    st.session_state.planning_inputs = {}

# --- 2. Logic Engine ---
def run_allocation(devs, qas, leads, planning_data, num_sprints, start_date, sprint_days):
    plan = []
    curr_dt = pd.to_datetime(start_date)
    for i in range(num_sprints):
        s_start = curr_dt + timedelta(days=i * sprint_days)
        s_end = s_start + timedelta(days=sprint_days - 1)
        s_label = f"Sprint {i}"

        def assign(task, role, names, total_hrs):
            if total_hrs <= 0 or not names: return
            split = float(total_hrs) / len(names)
            for name in names:
                plan.append({"Sprint": s_label, "Start": s_start, "Finish": s_end, 
                             "Task": task, "Owner": name, "Role": role, "Hours": round(split, 1)})

        if i == 0:
            assign("Analysis Phase", "Lead", leads, planning_data["Analysis Phase"])
            assign("TC preparation", "QA", qas, planning_data["TC preparation"])
        elif 0 < i < (num_sprints - 1):
            mid = max(1, num_sprints - 2)
            assign("Development Phase", "Dev", devs, planning_data["Development Phase"]/mid)
            assign("Code Review", "Lead", leads, planning_data["Code Review"]/mid)
            assign("QA testing", "QA", qas, planning_data["QA testing"]/mid)
            assign("Bug retest", "QA", qas, planning_data["Bug retest"]/mid)
            assign("Bug Fixes", "Dev", devs, planning_data["Bug Fixes"]/mid)
        elif i == (num_sprints - 1):
            assign("Integration Testing", "QA", qas, planning_data["Integration Testing"])
            assign("Smoke test", "QA", qas, planning_data["Smoke test"])
            assign("Merge and Deploy", "Ops", ["DevOps"], planning_data["Merge and Deploy"])
    return pd.DataFrame(plan)

# --- 3. Sidebar Navigation & Central Controls ---
st.sidebar.title("💠 Jarvis Navigation")
page = st.sidebar.radio("Go to:", ["Master Setup", "Roadmap Editor", "Resource Split-up", "Quality Metrics"])

st.sidebar.divider()
st.sidebar.subheader("🔄 Central Control")

if st.sidebar.button("🔃 Sync & Load Data", use_container_width=True, type="primary"):
    if st.session_state.team_setup.get('devs'):
        st.session_state.master_plan = run_allocation(
            st.session_state.team_setup['devs'], st.session_state.team_setup['qas'],
            st.session_state.team_setup['leads'], st.session_state.planning_inputs,
            st.session_state.team_setup['num_sp'], st.session_state.team_setup['start_dt'],
            st.session_state.team_setup['sp_days']
        )
        st.session_state.release_quality = pd.DataFrame([
            {"Sprint": f"Sprint {i}", "TCs Created": 0, "TCs Executed": 0, "Bugs Found": 0} 
            for i in range(st.session_state.team_setup['num_sp'])
        ])
        st.sidebar.success("Environment Synced!")

# EXPORT TO EXCEL (Mocking PDF/Excel Export for Executive Summary)
if st.session_state.master_plan is not None:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        st.session_state.master_plan.to_excel(writer, sheet_name='Roadmap')
        if not st.session_state.release_quality.empty:
            st.session_state.release_quality.to_excel(writer, sheet_name='Quality_Metrics')
    st.sidebar.download_button("📥 Export Executive Report", buffer.getvalue(), "Jarvis_Sprint_Report.xlsx", use_container_width=True)

if st.sidebar.button("🗑️ Reset All Data", use_container_width=True):
    for key in ['master_plan', 'release_quality', 'team_setup', 'planning_inputs']:
        st.session_state[key] = None if key == 'master_plan' else (pd.DataFrame() if key == 'release_quality' else {})
    st.rerun()

# --- PAGE: MASTER SETUP ---
if page == "Master Setup":
    st.title("⚙️ Project & Team Configuration")
    with st.expander("👥 Team Definition", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            d_sz = st.number_input("Dev Team Size", 1, 10, 3)
            st.session_state.team_setup['devs'] = [st.text_input(f"Dev {j+1}", f"Dev_{j+1}", key=f"d{j}") for j in range(d_sz)]
        with col2:
            q_sz = st.number_input("QA Team Size", 1, 5, 1)
            st.session_state.team_setup['qas'] = [st.text_input(f"QA {j+1}", f"QA_{j+1}", key=f"q{j}") for j in range(q_sz)]
        with col3:
            l_sz = st.number_input("Lead Team Size", 1, 5, 1)
            st.session_state.team_setup['leads'] = [st.text_input(f"Lead {j+1}", f"Lead_{j+1}", key=f"l{j}") for j in range(l_sz)]

    with st.expander("📅 Sprint Schedule & Effort", expanded=True):
        c1, c2, c3 = st.columns(3)
        st.session_state.team_setup['start_dt'] = c1.date_input("Project Start", datetime(2026, 2, 9))
        st.session_state.team_setup['num_sp'] = c2.number_input("Total Sprints", 2, 24, 4)
        st.session_state.team_setup['sp_days'] = c3.number_input("Working Days/Sprint", 1, 60, 10)
        daily_h = st.slider("Daily Max Hours", 1, 24, 8)
        st.session_state.team_setup['capacity'] = st.session_state.team_setup['sp_days'] * daily_h

        st.subheader("Planning Inputs")
        pc1, pc2 = st.columns(2)
        with pc1:
            h_ap = st.number_input("Analysis Phase", 0.0); h_dp = st.number_input("Development Phase", 0.0)
            h_bf = st.number_input("Bug Fixes", 0.0); h_cr = st.number_input("Code Review", 0.0); h_qt = st.number_input("QA testing", 0.0)
        with pc2:
            h_tc = st.number_input("TC preparation", 0.0); h_br = st.number_input("Bug retest", 0.0)
            h_it = st.number_input("Integration Testing", 0.0); h_st = st.number_input("Smoke test", 0.0); h_md = st.number_input("Merge and Deploy", 0.0)
        st.session_state.planning_inputs = {"Analysis Phase": h_ap, "Development Phase": h_dp, "Bug Fixes": h_bf, "Code Review": h_cr, "QA testing": h_qt, "TC preparation": h_tc, "Bug retest": h_br, "Integration Testing": h_it, "Smoke test": h_st, "Merge and Deploy": h_md}

# --- PAGE: ROADMAP EDITOR ---
elif page == "Roadmap Editor":
    st.title("🗺️ Roadmap Editor")
    if st.session_state.master_plan is not None:
        st.session_state.master_plan = st.data_editor(st.session_state.master_plan, use_container_width=True)
    else:
        st.info("Sync data in sidebar to start.")

# --- PAGE: RESOURCE SPLIT-UP ---
elif page == "Resource Split-up":
    st.title("📊 Resource Intelligence")
    if st.session_state.master_plan is not None:
        cap = st.session_state.team_setup['capacity']
        util = st.session_state.master_plan.groupby(['Owner', 'Sprint'])['Hours'].sum().reset_index()
        util['Utilization %'] = (util['Hours'] / cap * 100).round(1)
        st.plotly_chart(px.bar(util, x='Sprint', y='Utilization %', color='Owner', barmode='group', title="Sprint Utilization vs Capacity"), use_container_width=True)
        
        st.divider()
        owners = st.session_state.master_plan["Owner"].unique()
        sel = st.selectbox("Detailed Resource View", owners)
        res_data = st.session_state.master_plan[st.session_state.master_plan["Owner"] == sel]
        c1, c2 = st.columns(2)
        with c1: st.dataframe(res_data[["Sprint", "Task", "Hours"]], use_container_width=True, hide_index=True)
        with c2: st.plotly_chart(px.pie(res_data, values='Hours', names='Task', hole=0.3), use_container_width=True)

# --- PAGE: QUALITY METRICS ---
elif page == "Quality Metrics":
    st.title("🛡️ Quality Intelligence")
    if not st.session_state.release_quality.empty:
        st.session_state.release_quality = st.data_editor(st.session_state.release_quality, use_container_width=True)
        q = st.session_state.release_quality
        st.plotly_chart(px.line(q, x="Sprint", y="Bugs Found", title="Defect Trend Line", markers=True))
