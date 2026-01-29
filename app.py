import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# Config
st.set_page_config(page_title="Jarvis - Sprint planning", layout="wide")

# --- 1. Persistent State Management ---
if 'master_plan' not in st.session_state:
    st.session_state.master_plan = None
if 'release_quality' not in st.session_state:
    # Ensuring Quality Metrics persist across navigation
    st.session_state.release_quality = pd.DataFrame(columns=["Sprint", "TCs Created", "TCs Executed", "Bugs Found"])
if 'team_setup' not in st.session_state:
    st.session_state.team_setup = {
        'devs': ["Solaimalai", "Ananth", "Surya"], #
        'qas': ["Noah"], 
        'leads': ["Narmadha"], 
        'num_sp': 4, 
        'sp_days': 10, 
        'start_dt': datetime(2026, 2, 9),
        'buffer': 10,
        'role_caps': {'Dev': 8, 'QA': 8, 'Lead': 8}
    }
if 'planning_inputs' not in st.session_state:
    # Full lifecycle fields
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

st.sidebar.divider()
st.sidebar.subheader("🔄 Central Control")

if st.sidebar.button("🔃 Sync & Load Data", use_container_width=True, type="primary"):
    st.session_state.master_plan = run_allocation(
        st.session_state.team_setup['devs'], st.session_state.team_setup['qas'],
        st.session_state.team_setup['leads'], st.session_state.planning_inputs,
        st.session_state.team_setup['num_sp'], st.session_state.team_setup['start_dt'],
        st.session_state.team_setup['sp_days'], st.session_state.team_setup['buffer']
    )
    # Initialize quality metrics with zero data
    st.session_state.release_quality = pd.DataFrame([
        {"Sprint": f"Sprint {i}", "TCs Created": 0, "TCs Executed": 0, "Bugs Found": 0} 
        for i in range(st.session_state.team_setup['num_sp'])
    ])
    st.sidebar.success("Environment Synced!")

# --- PAGE: RESOURCE SPLIT-UP ---
if page == "Resource Split-up":
    st.title("📊 Resource Intelligence")
    if st.session_state.master_plan is not None:
        # Force graph generation from session_state
        util_df = st.session_state.master_plan.groupby(['Resource', 'Sprint'])['Hours'].sum().reset_index()
        if not util_df.empty:
            st.plotly_chart(px.bar(util_df, x='Sprint', y='Hours', color='Resource', barmode='group', title="Resource Load Split-up"), use_container_width=True)
        
        owners = st.session_state.master_plan["Resource"].unique()
        sel = st.selectbox("Resource Detail", owners)
        res_data = st.session_state.master_plan[st.session_state.master_plan["Resource"] == sel]
        st.plotly_chart(px.pie(res_data, values='Hours', names='Task', title=f"Task Distribution: {sel}"))
    else:
        st.info("No data found. Please 'Sync & Load' from the sidebar.")

# --- PAGE: QUALITY METRICS ---
elif page == "Quality Metrics":
    st.title("🛡️ Quality Intelligence")
    # Display editor for metrics
    st.session_state.release_quality = st.data_editor(st.session_state.release_quality, use_container_width=True)
    
    # Check if data exists before plotting
    if not st.session_state.release_quality.empty:
        q_df = st.session_state.release_quality
        # Only show graph if there is non-zero data to visualize
        if q_df["Bugs Found"].sum() > 0 or q_df["TCs Executed"].sum() > 0:
            fig_q = px.line(q_df, x="Sprint", y="Bugs Found", markers=True, title="Defect Trend")
            st.plotly_chart(fig_q, use_container_width=True)
            
            fig_tc = px.bar(q_df, x="Sprint", y=["TCs Created", "TCs Executed"], barmode="group", title="Testing Progress")
            st.plotly_chart(fig_tc, use_container_width=True)
        else:
            st.warning("Enter values in the table above to generate Quality Trends.")

# --- PAGE: MASTER SETUP ---
elif page == "Master Setup":
    st.title("⚙️ Project Configuration")
    # All inputs here are mapped to st.session_state.team_setup and st.session_state.planning_inputs
    st.write("Current Configuration Locked for Navigation Persistence.")
