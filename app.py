import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# Config
st.set_page_config(page_title="Jarvis - Sprint planning", layout="wide")

# --- 1. Robust State Persistence ---
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

# --- 2. Allocation Logic ---
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
                plan.append({
                    "Sprint": s_label, "Start": s_start, "Finish": s_end, 
                    "Task": task, "Resource": name, "Role": role, "Hours": round(split, 1)
                })

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

# --- 3. Navigation & Controls ---
st.sidebar.title("💠 Jarvis Navigation")
page = st.sidebar.radio("Go to:", ["Master Setup", "Roadmap Editor", "Resource Split-up", "Quality Metrics"])

st.sidebar.divider()
st.sidebar.subheader("🔄 Central Control")

if st.sidebar.button("🔃 Sync & Load Data", use_container_width=True, type="primary"):
    st.session_state.master_plan = run_allocation(
        st.session_state.team_setup['devs'], st.session_state.team_setup['qas'],
        st.session_state.team_setup['leads'], st.session_state.planning_inputs,
        st.session_state.team_setup['num_sp'], st.session_state.team_setup['start_dt'],
        st.session_state.team_setup['sp_days']
    )
    st.sidebar.success("Roadmap Generated!")

if st.sidebar.button("🗑️ Reset All Data", use_container_width=True):
    for key in ['master_plan', 'release_quality']: st.session_state[key] = None
    st.rerun()

# --- PAGE: ROADMAP EDITOR ---
if page == "Roadmap Editor":
    st.title("🗺️ Roadmap & Trend Dashboard")
    
    if st.session_state.master_plan is not None:
        # 1. Overall Gantt Chart
        st.subheader("🗓️ Project Timeline (Gantt)")
        fig_gantt = px.timeline(
            st.session_state.master_plan, 
            x_start="Start", x_end="Finish", y="Task", color="Sprint",
            hover_data=["Resource", "Hours"], title="Overall Sprint Schedule"
        )
        fig_gantt.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_gantt, use_container_width=True)

        st.divider()

        # 2. Sprint Hours Split-up
        st.subheader("⏳ Effort Distribution by Sprint")
        split_df = st.session_state.master_plan.groupby(['Sprint', 'Task'])['Hours'].sum().reset_index()
        fig_split = px.bar(
            split_df, x="Sprint", y="Hours", color="Task", 
            title="Total Working Hours per Sprint", text_auto=True
        )
        st.plotly_chart(fig_split, use_container_width=True)

        st.divider()
        st.subheader("📝 Edit Roadmap Details")
        st.session_state.master_plan = st.data_editor(st.session_state.master_plan, use_container_width=True)
    else:
        st.info("Please Sync Data from the sidebar.")

# --- PAGE: QUALITY METRICS ---
elif page == "Quality Metrics":
    st.title("🛡️ Quality Intelligence")
    # Persistent Metrics Table
    if st.session_state.master_plan is not None and st.session_state.release_quality is None:
        st.session_state.release_quality = pd.DataFrame([
            {"Sprint": f"Sprint {i}", "TCs Created": 0, "TCs Executed": 0, "Bugs Found": 0} 
            for i in range(st.session_state.team_setup['num_sp'])
        ])
    
    if st.session_state.release_quality is not None:
        st.session_state.release_quality = st.data_editor(st.session_state.release_quality, use_container_width=True)
        q_df = st.session_state.release_quality
        if not q_df.empty:
            st.plotly_chart(px.line(q_df, x="Sprint", y="Bugs Found", markers=True, title="Bug Discovery Trend"))

# --- PAGE: MASTER SETUP ---
elif page == "Master Setup":
    st.title("⚙️ Project Configuration")
    # Retaining all lifecycle fields
    with st.expander("📅 Project Schedule", expanded=True):
        st.session_state.team_setup['num_sp'] = st.number_input("Total Sprints", value=st.session_state.team_setup['num_sp'])
        st.session_state.team_setup['sp_days'] = st.number_input("Days/Sprint", value=st.session_state.team_setup['sp_days'])

    with st.expander("📝 Planning Inputs", expanded=True):
        pc1, pc2 = st.columns(2)
        fields = list(st.session_state.planning_inputs.keys())
        for i, f in enumerate(fields):
            with (pc1 if i < 5 else pc2):
                st.session_state.planning_inputs[f] = st.number_input(f, value=st.session_state.planning_inputs[f])
