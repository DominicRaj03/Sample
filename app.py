import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import io

# Config
st.set_page_config(page_title="Jarvis - Sprint planning", layout="wide")

# --- 1. Persistent State Initialization ---
if 'master_plan' not in st.session_state:
    st.session_state.master_plan = None
if 'release_quality' not in st.session_state:
    st.session_state.release_quality = pd.DataFrame()
if 'team_setup' not in st.session_state:
    st.session_state.team_setup = {
        'devs': ["Solaimalai", "Ananth", "Surya"], 
        'qas': ["Noah"], 
        'leads': ["Narmadha"], 
        'num_sp': 4, 
        'sp_days': 10, 
        'start_dt': datetime(2026, 2, 9),
        'buffer': 10,
        'role_caps': {'Dev': 8, 'QA': 8, 'Lead': 8}
    }
if 'planning_inputs' not in st.session_state:
    st.session_state.planning_inputs = {
        "Analysis Phase": 0.0, "Development Phase": 0.0, "Bug Fixes": 0.0,
        "Code Review": 0.0, "QA testing": 0.0, "TC preparation": 0.0,
        "Bug retest": 0.0, "Integration Testing": 0.0, "Smoke test": 0.0,
        "Merge and Deploy": 0.0
    }

# --- 2. Logic Engine ---
def run_allocation(devs, qas, leads, planning_data, num_sprints, start_date, sprint_days, buffer_pct):
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
    st.session_state.master_plan = run_allocation(
        st.session_state.team_setup['devs'], st.session_state.team_setup['qas'],
        st.session_state.team_setup['leads'], st.session_state.planning_inputs,
        st.session_state.team_setup['num_sp'], st.session_state.team_setup['start_dt'],
        st.session_state.team_setup['sp_days'], st.session_state.team_setup['buffer']
    )
    st.session_state.release_quality = pd.DataFrame([
        {"Sprint": f"Sprint {i}", "TCs Created": 0, "TCs Executed": 0, "Bugs Found": 0} 
        for i in range(st.session_state.team_setup['num_sp'])
    ])
    st.sidebar.success("Global State Synced!")

# --- PAGE: ROADMAP EDITOR ---
if page == "Roadmap Editor":
    st.title("🗺️ Roadmap & Gantt Timeline")
    if st.session_state.master_plan is not None:
        st.subheader("🗓️ Calendar Timeline with Sprint Markers")
        
        # Gantt Chart Base
        fig = px.timeline(
            st.session_state.master_plan, 
            x_start="Start", 
            x_end="Finish", 
            y="Task", 
            color="Owner",
            hover_data=["Sprint", "Hours", "Role"],
            title="Day-to-Day Task Distribution"
        )
        
        # Adding Vertical Sprint Phase Markers
        sprint_count = st.session_state.team_setup['num_sp']
        start_date = pd.to_datetime(st.session_state.team_setup['start_dt'])
        sprint_days = st.session_state.team_setup['sp_days']
        
        for i in range(sprint_count + 1):
            marker_date = start_date + timedelta(days=i * sprint_days)
            fig.add_vline(x=marker_date.timestamp() * 1000, line_dash="dash", line_color="gray", 
                          annotation_text=f"S{i}" if i < sprint_count else "End")

        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)

        # Remaining logic for validation and data editor
        st.divider()
        st.subheader("📝 Live Roadmap Data Editor")
        st.session_state.master_plan = st.data_editor(st.session_state.master_plan, use_container_width=True)
    else:
        st.info("Sync Data in Sidebar to load the Roadmap.")

# --- PAGE: MASTER SETUP ---
elif page == "Master Setup":
    st.title("⚙️ Project & Team Configuration")
    # (Setup logic remains identical to preserve persistent values)
    with st.expander("🛡️ Role-Based Capacity & Buffer", expanded=True):
        bc1, bc2 = st.columns(2)
        with bc1:
            st.session_state.team_setup['buffer'] = st.slider("Sprint Buffer (%)", 0, 50, st.session_state.team_setup.get('buffer', 10))
        with bc2:
            rc1, rc2, rc3 = st.columns(3)
            st.session_state.team_setup['role_caps']['Dev'] = rc1.number_input("Dev Cap", 1, 24, st.session_state.team_setup['role_caps']['Dev'])
            st.session_state.team_setup['role_caps']['QA'] = rc2.number_input("QA Cap", 1, 24, st.session_state.team_setup['role_caps']['QA'])
            st.session_state.team_setup['role_caps']['Lead'] = rc3.number_input("Lead Cap", 1, 24, st.session_state.team_setup['role_caps']['Lead'])
    
    with st.expander("📅 Sprint Schedule & Effort", expanded=True):
        c1, c2, c3 = st.columns(3)
        st.session_state.team_setup['start_dt'] = c1.date_input("Project Start", st.session_state.team_setup['start_dt'])
        st.session_state.team_setup['num_sp'] = c2.number_input("Total Sprints", 2, 24, st.session_state.team_setup['num_sp'])
        st.session_state.team_setup['sp_days'] = c3.number_input("Working Days/Sprint", 1, 60, st.session_state.team_setup['sp_days'])
