import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# Config
st.set_page_config(page_title="Jarvis - Sprint planning", layout="wide")

# --- 1. State Persistence ---
if 'master_plan' not in st.session_state:
    st.session_state.master_plan = None
if 'team_setup' not in st.session_state:
    st.session_state.team_setup = {
        'devs': ["Solaimalai", "Ananth", "Surya"], #
        'qas': ["Noah"], 
        'leads': ["Narmadha"], 
        'num_sp': 4, 
        'sp_days': 10, 
        'start_dt': datetime(2026, 2, 9), #
        'daily_limit': 8.0
    }
if 'planning_inputs' not in st.session_state:
    st.session_state.planning_inputs = {
        "Analysis Phase": 0.0, "Development Phase": 0.0, "Bug Fixes": 0.0,
        "Code Review": 0.0, "QA testing": 0.0, "TC preparation": 0.0,
        "Bug retest": 0.0, "Integration Testing": 0.0, "Smoke test": 0.0,
        "Merge and Deploy": 0.0
    }

# --- 2. Navigation ---
st.sidebar.title("💠 Jarvis Navigation")
page = st.sidebar.radio("Go to:", ["Master Setup", "Roadmap Editor", "Resource Split-up", "Quality Metrics"])

# --- 3. Sidebar Synchronization Logic ---
st.sidebar.divider()
def run_sync():
    plan = []
    curr_dt = pd.to_datetime(st.session_state.team_setup['start_dt'])
    sprint_days = st.session_state.team_setup['sp_days']
    num_sprints = st.session_state.team_setup['num_sp']

    for i in range(num_sprints):
        # Calculate actual calendar dates for each sprint
        s_start = curr_dt + timedelta(days=i * sprint_days)
        s_end = s_start + timedelta(days=sprint_days - 1)
        s_label = f"Sprint {i}"

        def assign(task, role, names, total_hrs):
            if total_hrs <= 0 or not names: return
            split = float(total_hrs) / len(names)
            for name in names:
                plan.append({
                    "Sprint": s_label, 
                    "Start": s_start, 
                    "Finish": s_end, 
                    "Task": task, 
                    "Resource": name, 
                    "Role": role, 
                    "Hours": round(split, 1)
                })

        # Mapping Inputs to Roles
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
            assign("Merge and Deploy", "Ops", ["DevOps"], st.session_state.planning_inputs["Merge and Deploy"])
    
    st.session_state.master_plan = pd.DataFrame(plan)

if st.sidebar.button("🔃 Sync & Load Data", type="primary"):
    run_sync()
    st.sidebar.success("Calendar Roadmap Loaded!")

# --- PAGE: ROADMAP EDITOR ---
if page == "Roadmap Editor":
    st.title("🗺️ Day-to-Day Timeline Trend")
    
    if st.session_state.master_plan is not None:
        # Plotly Gantt-style Timeline
        st.subheader("🗓️ Gantt Chart: Project Schedule")
        fig = px.timeline(
            st.session_state.master_plan, 
            x_start="Start", 
            x_end="Finish", 
            y="Task", 
            color="Resource",
            hover_data=["Sprint", "Hours", "Role"],
            title="Calendar Task Distribution",
            color_discrete_sequence=px.colors.qualitative.Bold
        )
        # Improvement: Reverse Y-Axis to show flow from top to bottom
        fig.update_yaxes(autorange="reversed")
        # Format the X-Axis to show daily dates
        fig.update_layout(xaxis_title="Date Timeline", yaxis_title="Project Phases")
        st.plotly_chart(fig, use_container_width=True)

        st.divider()
        st.subheader("📊 Sprint Effort Breakdown")
        split_df = st.session_state.master_plan.groupby(['Sprint', 'Task'])['Hours'].sum().reset_index()
        st.plotly_chart(px.bar(split_df, x="Sprint", y="Hours", color="Task", barmode="group", text_auto=True), use_container_width=True)
        
        st.divider()
        st.subheader("📝 Live Editor")
        st.session_state.master_plan = st.data_editor(st.session_state.master_plan, use_container_width=True)
    else:
        st.info("Sync Data in the sidebar to visualize the timeline.")

# --- OTHER PAGES ---
elif page == "Master Setup":
    st.title("⚙️ Setup & Validation")
    # Mapping to existing fields
    st.session_state.team_setup['start_dt'] = st.date_input("Start Date", st.session_state.team_setup['start_dt'])
    c1, c2 = st.columns(2)
    st.session_state.team_setup['num_sp'] = c1.number_input("Sprints", 1, 10, st.session_state.team_setup['num_sp'])
    st.session_state.team_setup['sp_days'] = c2.number_input("Days per Sprint", 1, 30, st.session_state.team_setup['sp_days'])
    
    st.subheader("Planning Inputs")
    cols = st.columns(2)
    for i, field in enumerate(st.session_state.planning_inputs.keys()):
        st.session_state.planning_inputs[field] = cols[i%2].number_input(field, value=st.session_state.planning_inputs[field])
