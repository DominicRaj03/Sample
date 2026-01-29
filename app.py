import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import io

# Config
st.set_page_config(page_title="Jarvis - Sprint planning", layout="wide")

# --- 1. Persistent State Initialization ---
# This block ensures that every UI component is backed by session_state
if 'master_plan' not in st.session_state:
    st.session_state.master_plan = None
if 'release_quality' not in st.session_state:
    st.session_state.release_quality = pd.DataFrame()
if 'team_setup' not in st.session_state:
    st.session_state.team_setup = {
        'devs': ["Solaimalai", "Ananth", "Surya"], # Default values from your setup
        'qas': ["Noah"], 
        'leads': ["Narmadha"], 
        'num_sp': 4, 
        'sp_days': 10, 
        'start_dt': datetime(2026, 2, 9),
        'buffer': 10,
        'role_caps': {'Dev': 8, 'QA': 8, 'Lead': 8}
    }
if 'planning_inputs' not in st.session_state:
    # Initialize all lifecycle fields to zero to prevent erase on navigation
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

# SYNC & LOAD: Propagates current state to all pages
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

# RESET ALL: Clears the state manually
if st.sidebar.button("🗑️ Reset All Data", use_container_width=True):
    for key in ['master_plan', 'release_quality', 'team_setup', 'planning_inputs']:
        st.session_state.pop(key, None)
    st.rerun()

# --- PAGE: MASTER SETUP ---
if page == "Master Setup":
    st.title("⚙️ Project & Team Configuration")
    
    with st.expander("🛡️ Role-Based Capacity & Buffer", expanded=True):
        bc1, bc2 = st.columns(2)
        with bc1:
            st.session_state.team_setup['buffer'] = st.slider("Sprint Buffer (%)", 0, 50, st.session_state.team_setup.get('buffer', 10))
        with bc2:
            rc1, rc2, rc3 = st.columns(3)
            st.session_state.team_setup['role_caps']['Dev'] = rc1.number_input("Dev Cap", 1, 24, st.session_state.team_setup['role_caps']['Dev'])
            st.session_state.team_setup['role_caps']['QA'] = rc2.number_input("QA Cap", 1, 24, st.session_state.team_setup['role_caps']['QA'])
            st.session_state.team_setup['role_caps']['Lead'] = rc3.number_input("Lead Cap", 1, 24, st.session_state.team_setup['role_caps']['Lead'])

    with st.expander("👥 Team Definition", expanded=False):
        col1, col2, col3 = st.columns(3)
        # Using session_state for text inputs ensures values persist on navigation
        with col1:
            d_sz = st.number_input("Dev Team Size", 1, 10, len(st.session_state.team_setup['devs']))
            st.session_state.team_setup['devs'] = [st.text_input(f"Dev {j+1}", st.session_state.team_setup['devs'][j] if j < len(st.session_state.team_setup['devs']) else f"Dev_{j+1}", key=f"d{j}") for j in range(d_sz)]
        with col2:
            q_sz = st.number_input("QA Team Size", 1, 5, len(st.session_state.team_setup['qas']))
            st.session_state.team_setup['qas'] = [st.text_input(f"QA {j+1}", st.session_state.team_setup['qas'][j] if j < len(st.session_state.team_setup['qas']) else f"QA_{j+1}", key=f"q{j}") for j in range(q_sz)]
        with col3:
            l_sz = st.number_input("Lead Team Size", 1, 5, len(st.session_state.team_setup['leads']))
            st.session_state.team_setup['leads'] = [st.text_input(f"Lead {j+1}", st.session_state.team_setup['leads'][j] if j < len(st.session_state.team_setup['leads']) else f"Lead_{j+1}", key=f"l{j}") for j in range(l_sz)]

    with st.expander("📅 Sprint Schedule & Effort", expanded=True):
        c1, c2, c3 = st.columns(3)
        st.session_state.team_setup['start_dt'] = c1.date_input("Project Start", st.session_state.team_setup['start_dt'])
        st.session_state.team_setup['num_sp'] = c2.number_input("Total Sprints", 2, 24, st.session_state.team_setup['num_sp'])
        st.session_state.team_setup['sp_days'] = c3.number_input("Working Days/Sprint", 1, 60, st.session_state.team_setup['sp_days'])

        st.subheader("Planning Inputs")
        pc1, pc2 = st.columns(2)
        # Lifecycle fields mapped to persistent session state
        with pc1:
            for field in ["Analysis Phase", "Development Phase", "Bug Fixes", "Code Review", "QA testing"]:
                st.session_state.planning_inputs[field] = st.number_input(field, value=st.session_state.planning_inputs.get(field, 0.0))
        with pc2:
            for field in ["TC preparation", "Bug retest", "Integration Testing", "Smoke test", "Merge and Deploy"]:
                st.session_state.planning_inputs[field] = st.number_input(field, value=st.session_state.planning_inputs.get(field, 0.0))

# --- PAGE: ROADMAP EDITOR ---
elif page == "Roadmap Editor":
    st.title("🗺️ Roadmap Editor")
    if st.session_state.master_plan is not None:
        # Validation logic remains active during manual edits
        sp_days = st.session_state.team_setup['sp_days']
        buffer_pct = st.session_state.team_setup['buffer']
        usage = st.session_state.master_plan.groupby(['Sprint', 'Owner', 'Role'])['Hours'].sum().reset_index()
        
        for _, row in usage.iterrows():
            role_limit = st.session_state.team_setup['role_caps'].get(row['Role'], 8)
            net_cap = (role_limit * sp_days) * ((100 - buffer_pct) / 100)
            if row['Hours'] > net_cap:
                st.error(f"⚠️ Capacity Breach: {row['Owner']} ({row['Hours']}h > {net_cap}h limit)")
        
        st.session_state.master_plan = st.data_editor(st.session_state.master_plan, use_container_width=True)
    else:
        st.info("Sync Data in Sidebar to load the Roadmap.")

# --- PAGE: RESOURCE SPLIT-UP ---
elif page == "Resource Split-up":
    st.title("📊 Resource Intelligence")
    if st.session_state.master_plan is not None:
        balance_df = st.session_state.master_plan.groupby(['Owner', 'Role', 'Sprint'])['Hours'].sum().reset_index()
        st.plotly_chart(px.bar(balance_df, x='Owner', y='Hours', color='Sprint', barmode='group', title="Team Load Balancing"), use_container_width=True)
        
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
        st.plotly_chart(px.line(st.session_state.release_quality, x="Sprint", y="Bugs Found", markers=True, title="Defect Trend"))
