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
                plan.append({"Sprint": s_label, "Start": s_start, "Finish": s_end, "Task": task, "Resource": name, "Role": role, "Hours": round(split, 1)})
        
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

# --- 3. Sidebar Navigation ---
st.sidebar.title("💠 Jarvis Navigation")
page = st.sidebar.radio("Go to:", ["Master Setup", "Roadmap Editor", "Resource Split-up", "Quality Metrics"])

# --- PAGE: MASTER SETUP ---
if page == "Master Setup":
    st.title("⚙️ Master Setup & Validation")
    
    # 1. Team & Capacity Inputs
    with st.expander("👥 Team Definition & Daily Limits", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        d_size = c1.number_input("Devs", 1, 10, len(st.session_state.team_setup['devs']))
        q_size = c2.number_input("QAs", 1, 10, len(st.session_state.team_setup['qas']))
        l_size = c3.number_input("Leads", 1, 10, len(st.session_state.team_setup['leads']))
        st.session_state.team_setup['daily_limit'] = c4.slider("Daily Limit (Hrs)", 1.0, 12.0, st.session_state.team_setup['daily_limit'])

    # 2. Planning Inputs
    st.subheader("📝 Planning Inputs (Total Hours)")
    pc1, pc2 = st.columns(2)
    fields = list(st.session_state.planning_inputs.keys())
    for i, f in enumerate(fields):
        with (pc1 if i < 5 else pc2):
            st.session_state.planning_inputs[f] = st.number_input(f, value=st.session_state.planning_inputs[f], step=0.5)

    # 3. Validation Logic [New Addon]
    # Calculate Total Capacity: (People * Daily Limit * Total Working Days)
    total_days = st.session_state.team_setup['num_sp'] * st.session_state.team_setup['sp_days']
    dev_cap = d_size * st.session_state.team_setup['daily_limit'] * total_days
    qa_cap = q_size * st.session_state.team_setup['daily_limit'] * total_days
    lead_cap = l_size * st.session_state.team_setup['daily_limit'] * total_days

    # Calculate Total Load per Role
    dev_load = st.session_state.planning_inputs["Development Phase"] + st.session_state.planning_inputs["Bug Fixes"]
    qa_load = st.session_state.planning_inputs["QA testing"] + st.session_state.planning_inputs["TC preparation"] + \
              st.session_state.planning_inputs["Bug retest"] + st.session_state.planning_inputs["Integration Testing"] + \
              st.session_state.planning_inputs["Smoke test"]
    lead_load = st.session_state.planning_inputs["Analysis Phase"] + st.session_state.planning_inputs["Code Review"]

    # Warnings Display
    error_found = False
    if dev_load > dev_cap:
        st.error(f"⚠️ **Dev Overload:** {dev_load}h assigned vs {dev_cap}h capacity.")
        error_found = True
    if qa_load > qa_cap:
        st.error(f"⚠️ **QA Overload:** {qa_load}h assigned vs {qa_cap}h capacity.")
        error_found = True
    if lead_load > lead_cap:
        st.error(f"⚠️ **Lead Overload:** {lead_load}h assigned vs {lead_cap}h capacity.")
        error_found = True

    st.sidebar.divider()
    if st.sidebar.button("🔃 Sync & Load Data", use_container_width=True, type="primary", disabled=error_found):
        st.session_state.master_plan = run_allocation(
            st.session_state.team_setup['devs'], st.session_state.team_setup['qas'],
            st.session_state.team_setup['leads'], st.session_state.planning_inputs,
            st.session_state.team_setup['num_sp'], st.session_state.team_setup['start_dt'],
            st.session_state.team_setup['sp_days']
        )
        st.sidebar.success("Success! Data Balanced.")
    elif error_found:
        st.sidebar.warning("Fix Capacity Errors to Sync")

# --- PAGE: ROADMAP EDITOR ---
elif page == "Roadmap Editor":
    st.title("🗺️ Roadmap & Timeline")
    if st.session_state.master_plan is not None:
        # Gantt Chart
        fig_gantt = px.timeline(st.session_state.master_plan, x_start="Start", x_end="Finish", y="Task", color="Sprint")
        fig_gantt.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_gantt, use_container_width=True)
        
        # Sprint Split-up
        split_df = st.session_state.master_plan.groupby(['Sprint', 'Task'])['Hours'].sum().reset_index()
        st.plotly_chart(px.bar(split_df, x="Sprint", y="Hours", color="Task", text_auto=True), use_container_width=True)
    else:
        st.info("Balanced data required in Master Setup.")
