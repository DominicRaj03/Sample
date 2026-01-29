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

# --- 3. Sidebar Navigation ---
st.sidebar.title("💠 Jarvis Navigation")
page = st.sidebar.radio("Go to:", ["Master Setup", "Roadmap Editor", "Resource Split-up"])

if st.sidebar.button("🔃 Sync & Load Data", use_container_width=True, type="primary"):
    st.session_state.master_plan = run_allocation(
        st.session_state.team_setup['devs'], st.session_state.team_setup['qas'],
        st.session_state.team_setup['leads'], st.session_state.planning_inputs,
        st.session_state.team_setup['num_sp'], st.session_state.team_setup['start_dt'],
        st.session_state.team_setup['sp_days'], st.session_state.team_setup['buffer']
    )

# --- PAGE: ROADMAP EDITOR ---
if page == "Roadmap Editor":
    st.title("🗺️ Roadmap & Utilization Engine")
    if st.session_state.master_plan is not None:
        # 1. Gantt Timeline
        st.subheader("🗓️ Calendar Timeline")
        fig = px.timeline(st.session_state.master_plan, x_start="Start", x_end="Finish", y="Task", color="Owner")
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)

        # 2. Live Data Editor
        st.subheader("📝 Live Roadmap Data Editor")
        st.session_state.master_plan = st.data_editor(st.session_state.master_plan, use_container_width=True)

        st.divider()

        # 3. Analytics Row: Split-up and Role Utilization
        col_bar, col_util = st.columns([2, 1])

        with col_bar:
            st.subheader("📊 Sprint-wise Resource Split-up")
            res_split_df = st.session_state.master_plan.groupby(['Sprint', 'Owner'])['Hours'].sum().reset_index()
            st.plotly_chart(px.bar(res_split_df, x="Sprint", y="Hours", color="Owner", barmode="group", text_auto=True), use_container_width=True)

        with col_util:
            st.subheader("📉 Role Utilization Summary")
            # Calculate Capacity vs Demand
            s_days = st.session_state.team_setup['sp_days']
            buf = (100 - st.session_state.team_setup['buffer']) / 100
            
            # Aggregate current load from the editor
            role_load = st.session_state.master_plan.groupby('Role')['Hours'].sum().reset_index()
            
            # Calculate available capacity per role for the whole project
            role_map = {
                'Dev': len(st.session_state.team_setup['devs']),
                'QA': len(st.session_state.team_setup['qas']),
                'Lead': len(st.session_state.team_setup['leads'])
            }
            
            util_data = []
            for _, row in role_load.iterrows():
                role = row['Role']
                if role in role_map:
                    headcount = role_map[role]
                    daily_cap = st.session_state.team_setup['role_caps'].get(role, 8)
                    total_cap = headcount * daily_cap * s_days * st.session_state.team_setup['num_sp'] * buf
                    util_pct = (row['Hours'] / total_cap) * 100
                    util_data.append({"Role": role, "Load (h)": row['Hours'], "Capacity (h)": round(total_cap, 1), "Util %": f"{round(util_pct, 1)}%"})
            
            st.table(pd.DataFrame(util_data))
    else:
        st.info("Sync Data in Sidebar to load the Roadmap.")

# --- PAGE: MASTER SETUP ---
elif page == "Master Setup":
    st.title("⚙️ Project Configuration")
    # Setup inputs for team and effort (logic continues as established)
    st.session_state.team_setup['sp_days'] = st.number_input("Working Days/Sprint", value=st.session_state.team_setup['sp_days'])
    # (Rest of inputs mapping to st.session_state.planning_inputs)
