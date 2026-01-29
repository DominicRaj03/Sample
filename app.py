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
    st.session_state.team_setup = {"devs": [], "qas": [], "leads": [], "role_caps": {"Dev": 8, "QA": 8, "Lead": 8}}
if 'planning_inputs' not in st.session_state:
    st.session_state.planning_inputs = {}

# --- 2. Logic Engine ---
def run_allocation(devs, qas, leads, planning_data, num_sprints, start_date, sprint_days, buffer_pct):
    plan = []
    curr_dt = pd.to_datetime(start_date)
    # Apply Sprint Buffer to available hours
    efficiency_factor = (100 - buffer_pct) / 100
    
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
            st.session_state.team_setup['sp_days'], st.session_state.team_setup.get('buffer', 0)
        )
        st.session_state.release_quality = pd.DataFrame([
            {"Sprint": f"Sprint {i}", "TCs Created": 0, "TCs Executed": 0, "Bugs Found": 0} 
            for i in range(st.session_state.team_setup['num_sp'])
        ])
        st.sidebar.success("Environment Synced!")

if st.sidebar.button("🗑️ Reset All Data", use_container_width=True):
    st.session_state.master_plan = None
    st.session_state.release_quality = pd.DataFrame()
    st.rerun()

# --- PAGE: MASTER SETUP ---
if page == "Master Setup":
    st.title("⚙️ Project & Team Configuration")
    
    with st.expander("🛡️ Role-Based Capacity & Buffer", expanded=True):
        bc1, bc2 = st.columns(2)
        with bc1:
            st.session_state.team_setup['buffer'] = st.slider("Sprint Buffer (%)", 0, 50, 10, help="Reserve % of capacity for unplanned tasks")
        with bc2:
            st.write("**Daily Max Hours by Role**")
            rc1, rc2, rc3 = st.columns(3)
            st.session_state.team_setup['role_caps']['Dev'] = rc1.number_input("Dev", 1, 24, 8)
            st.session_state.team_setup['role_caps']['QA'] = rc2.number_input("QA", 1, 24, 8)
            st.session_state.team_setup['role_caps']['Lead'] = rc3.number_input("Lead", 1, 24, 8)

    with st.expander("👥 Team Definition", expanded=False):
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
        # Validation Warnings Logic
        sp_days = st.session_state.team_setup['sp_days']
        buffer_pct = st.session_state.team_setup.get('buffer', 0)
        
        usage = st.session_state.master_plan.groupby(['Sprint', 'Owner', 'Role'])['Hours'].sum().reset_index()
        
        for index, row in usage.iterrows():
            role_limit = st.session_state.team_setup['role_caps'].get(row['Role'], 8)
            net_capacity = (role_limit * sp_days) * ((100 - buffer_pct) / 100)
            
            if row['Hours'] > net_capacity:
                st.error(f"⚠️ **Validation Warning:** {row['Owner']} ({row['Role']}) has {row['Hours']}h in {row['Sprint']}. Max available after {buffer_pct}% buffer is {net_capacity}h.")
        
        st.session_state.master_plan = st.data_editor(st.session_state.master_plan, use_container_width=True)
    else:
        st.info("Sync data in sidebar to start.")

# --- PAGE: RESOURCE SPLIT-UP ---
elif page == "Resource Split-up":
    st.title("📊 Resource Balancing & Intelligence")
    if st.session_state.master_plan is not None:
        # Resource Balancing View
        st.subheader("Team Resource Balancing (Load vs Capacity)")
        balance_df = st.session_state.master_plan.groupby(['Owner', 'Role', 'Sprint'])['Hours'].sum().reset_index()
        fig_bal = px.bar(balance_df, x='Owner', y='Hours', color='Sprint', barmode='group', title="Resource Load Balancing")
        st.plotly_chart(fig_bal, use_container_width=True)
        
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
        st.plotly_chart(px.line(q, x="Sprint", y="Bugs Found", title="Defect Discovery Trend", markers=True))
