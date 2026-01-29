import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.figure_factory as ff
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
    st.sidebar.success("Global State Synced!")

if st.sidebar.button("🗑️ Reset All Data", use_container_width=True):
    st.session_state.master_plan = None
    st.session_state.release_quality = pd.DataFrame()
    st.rerun()

# --- PAGE: MASTER SETUP ---
if page == "Master Setup":
    st.title("⚙️ Project & Team Configuration")
    # Persistent Inputs
    with st.expander("🛡️ Role-Based Capacity & Buffer", expanded=True):
        st.session_state.team_setup['buffer'] = st.slider("Sprint Buffer (%)", 0, 50, st.session_state.team_setup.get('buffer', 10))
        rc1, rc2, rc3 = st.columns(3)
        st.session_state.team_setup['role_caps']['Dev'] = rc1.number_input("Dev Cap", 1, 24, st.session_state.team_setup['role_caps']['Dev'])
        st.session_state.team_setup['role_caps']['QA'] = rc2.number_input("QA Cap", 1, 24, st.session_state.team_setup['role_caps']['QA'])
        st.session_state.team_setup['role_caps']['Lead'] = rc3.number_input("Lead Cap", 1, 24, st.session_state.team_setup['role_caps']['Lead'])

    with st.expander("📅 Sprint Schedule & Effort", expanded=True):
        c1, c2, c3 = st.columns(3)
        st.session_state.team_setup['start_dt'] = c1.date_input("Project Start", st.session_state.team_setup['start_dt'])
        st.session_state.team_setup['num_sp'] = c2.number_input("Total Sprints", 2, 24, st.session_state.team_setup['num_sp'])
        st.session_state.team_setup['sp_days'] = c3.number_input("Working Days/Sprint", 1, 60, st.session_state.team_setup['sp_days'])

        st.subheader("Planning Inputs")
        pc1, pc2 = st.columns(2)
        fields = list(st.session_state.planning_inputs.keys())
        for i, field in enumerate(fields):
            with (pc1 if i < 5 else pc2):
                st.session_state.planning_inputs[field] = st.number_input(field, value=st.session_state.planning_inputs[field], key=f"inp_{field}")

# --- PAGE: ROADMAP EDITOR ---
elif page == "Roadmap Editor":
    st.title("🗺️ Roadmap & Timeline Trend")
    if st.session_state.master_plan is not None:
        # --- GANTT CHART SECTION ---
        st.subheader("🗓️ Project Gantt Chart")
        df_gantt = st.session_state.master_plan.copy()
        df_gantt = df_gantt.rename(columns={"Task": "Task", "Start": "Start", "Finish": "Finish", "Resource": "Resource"})
        fig = px.timeline(df_gantt, x_start="Start", x_end="Finish", y="Task", color="Sprint", 
                          hover_data=["Resource", "Hours"], title="Overall Sprint Roadmap")
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)

        # --- HOURS SPLIT SECTION ---
        st.divider()
        st.subheader("⏳ Sprint-wise Hours Split-up")
        split_data = st.session_state.master_plan.groupby(['Sprint', 'Task'])['Hours'].sum().reset_index()
        fig_split = px.bar(split_data, x="Sprint", y="Hours", color="Task", title="Effort Distribution per Sprint", text_auto=True)
        st.plotly_chart(fig_split, use_container_width=True)

        st.divider()
        st.subheader("📝 Roadmap Raw Data")
        st.session_state.master_plan = st.data_editor(st.session_state.master_plan, use_container_width=True)
    else:
        st.info("Sync Data in Sidebar to view the Roadmap.")

# --- PAGE: RESOURCE SPLIT-UP ---
elif page == "Resource Split-up":
    st.title("📊 Resource Intelligence")
    if st.session_state.master_plan is not None:
        balance_df = st.session_state.master_plan.groupby(['Resource', 'Role', 'Sprint'])['Hours'].sum().reset_index()
        st.plotly_chart(px.bar(balance_df, x='Resource', y='Hours', color='Sprint', barmode='group', title="Resource Load Comparison"), use_container_width=True)

# --- PAGE: QUALITY METRICS ---
elif page == "Quality Metrics":
    st.title("🛡️ Quality Intelligence")
    if not st.session_state.release_quality.empty:
        st.session_state.release_quality = st.data_editor(st.session_state.release_quality, use_container_width=True)
