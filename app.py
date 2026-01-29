import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# Config
st.set_page_config(page_title="Jarvis - Sprint planning", layout="wide")

# --- 1. Persistent State Management ---
if 'master_plan' not in st.session_state:
    st.session_state.master_plan = None
if 'team_setup' not in st.session_state:
    st.session_state.team_setup = {
        'devs': ["Solaimalai", "Ananth", "Surya"], 
        'qas': ["Noah"], 
        'leads': ["Narmadha"], 
        'num_sp': 4, 
        'sp_days': 10, 
        'start_dt': datetime(2026, 2, 9),
        'daily_limit': 8.0
    }
if 'planning_inputs' not in st.session_state:
    st.session_state.planning_inputs = {
        "Analysis Phase": 0.0, "Development Phase": 0.0, "Bug Fixes": 0.0,
        "Code Review": 0.0, "QA testing": 0.0, "TC preparation": 0.0,
        "Bug retest": 0.0, "Integration Testing": 0.0, "Smoke test": 0.0,
        "Merge and Deploy": 0.0
    }

# --- 2. Logic Engine: Calendar-Aware Allocation ---
def run_sync():
    plan = []
    curr_dt = pd.to_datetime(st.session_state.team_setup['start_dt'])
    sprint_days = st.session_state.team_setup['sp_days']
    num_sprints = st.session_state.team_setup['num_sp']

    for i in range(num_sprints):
        # Calculate actual calendar dates per sprint
        s_start = curr_dt + timedelta(days=i * sprint_days)
        s_end = s_start + timedelta(days=sprint_days - 1)
        s_label = f"Sprint {i}"

        def assign(task, role, names, total_hrs):
            if total_hrs <= 0 or not names: return
            split = float(total_hrs) / len(names)
            for name in names:
                plan.append({
                    "Sprint": s_label, "Start": s_start, "Finish": s_end, 
                    "Task": task, "Resource": name, "Role": role, "Hours": round(split, 1)
                })

        # Role Mapping
        if i == 0:
            assign("Analysis Phase", "Lead", st.session_state.team_setup['leads'], st.session_state.planning_inputs["Analysis Phase"])
            assign("TC preparation", "QA", st.session_state.team_setup['qas'], st.session_state.planning_inputs["TC preparation"])
        elif 0 < i < (num_sprints - 1):
            mid = max(1, num_sprints - 2)
            assign("Development Phase", "Dev", st.session_state.team_setup['devs'], st.session_state.planning_inputs["Development Phase"]/mid)
            assign("Code Review", "Lead", st.session_state.team_setup['leads'], st.session_state.planning_inputs["Code Review"]/mid)
            assign("QA testing", "QA", st.session_state.team_setup['qas'], st.session_state.planning_inputs["QA testing"]/mid)
            assign("Bug Fixes", "Dev", st.session_state.team_setup['devs'], st.session_state.planning_inputs["Bug Fixes"]/mid)
        elif i == (num_sprints - 1):
            assign("Integration Testing", "QA", st.session_state.team_setup['qas'], st.session_state.planning_inputs["Integration Testing"])
            assign("Smoke test", "QA", st.session_state.team_setup['qas'], st.session_state.planning_inputs["Smoke test"])
            assign("Merge and Deploy", "Ops", ["DevOps"], st.session_state.planning_inputs["Merge and Deploy"])
    
    st.session_state.master_plan = pd.DataFrame(plan)

# --- 3. Sidebar Navigation ---
st.sidebar.title("💠 Jarvis Navigation")
page = st.sidebar.radio("Go to:", ["Master Setup", "Roadmap Editor", "Resource Split-up", "Quality Metrics"])

st.sidebar.divider()
if st.sidebar.button("🔃 Sync & Load Data", type="primary", use_container_width=True):
    run_sync()
    st.sidebar.success("Roadmap Updated!")

# --- PAGE: ROADMAP EDITOR ---
if page == "Roadmap Editor":
    st.title("🗺️ Roadmap Intelligence Dashboard")
    
    if st.session_state.master_plan is not None:
        # --- CALENDAR GANTT CHART ---
        st.subheader("🗓️ Project Timeline (Calendar Gantt)")
        fig_gantt = px.timeline(
            st.session_state.master_plan, 
            x_start="Start", 
            x_end="Finish", 
            y="Task", 
            color="Resource",
            hover_data=["Sprint", "Hours"],
            title="Day-to-Day Task Distribution",
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_gantt.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_gantt, use_container_width=True)

        st.divider()

        # --- SPRINT-WISE EFFORT SPLITUP ---
        st.subheader("📊 Sprint-wise Effort Split-up")
        # Group by Sprint and Task for a stacked bar view
        effort_df = st.session_state.master_plan.groupby(['Sprint', 'Task'])['Hours'].sum().reset_index()
        fig_bars = px.bar(
            effort_df, 
            x="Sprint", 
            y="Hours", 
            color="Task", 
            barmode="group",
            title="Hours Distribution per Sprint",
            text_auto=True
        )
        st.plotly_chart(fig_bars, use_container_width=True)

        st.divider()
        st.subheader("📝 Roadmap Raw Data")
        st.session_state.master_plan = st.data_editor(st.session_state.master_plan, use_container_width=True)
    else:
        st.info("Please Sync Data from the Master Setup page.")

# --- OTHER PAGES (Master Setup, etc.) ---
elif page == "Master Setup":
    st.title("⚙️ Project Setup")
    # Ensuring all fields from user upload are available
    with st.expander("📅 Sprint Schedule", expanded=True):
        c1, c2, c3 = st.columns(3)
        st.session_state.team_setup['start_dt'] = c1.date_input("Start", st.session_state.team_setup['start_dt'])
        st.session_state.team_setup['num_sp'] = c2.number_input("Total Sprints", value=st.session_state.team_setup['num_sp'])
        st.session_state.team_setup['sp_days'] = c3.number_input("Days per Sprint", value=st.session_state.team_setup['sp_days'])
    
    st.subheader("Planning Inputs")
    cols = st.columns(2)
    for i, field in enumerate(st.session_state.planning_inputs.keys()):
        st.session_state.planning_inputs[field] = cols[i%2].number_input(field, value=st.session_state.planning_inputs[field])
