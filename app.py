import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(page_title="Jarvis Manual Override Suite", layout="wide")

# --- Persistent Storage for Manual Overrides ---
if 'custom_tasks' not in st.session_state:
    st.session_state.custom_tasks = pd.DataFrame(columns=["Sprint", "Task", "Owner", "Role", "Hours"])
if 'deleted_tasks' not in st.session_state:
    st.session_state.deleted_tasks = set()

# --- Core Logic ---
def run_allocation(dev_names, qa_names, data, base_cap, num_sprints, buffer_pct, start_date, sprint_days, holidays, daily_hrs):
    generated_plan = []
    all_roles = dev_names + qa_names + ["Lead", "DevOps"]
    sprint_list = [f"Sprint {i}" for i in range(num_sprints)]
    resource_load = {s: {name: 0 for name in all_roles} for s in sprint_list}
    sprint_caps = {}

    for i in range(num_sprints):
        s_start = start_date + timedelta(days=i * sprint_days)
        s_end = s_start + timedelta(days=sprint_days)
        h_count = sum(1 for h in holidays if s_start <= h <= s_end)
        s_max = (base_cap - (h_count * daily_hrs)) * (1 - (buffer_pct / 100))
        sprint_caps[f"Sprint {i}"] = max(s_max, 1)

    def assign(sprint, names, task, role, hrs):
        owner = min(names, key=lambda x: resource_load[sprint][x])
        resource_load[sprint][owner] += hrs
        return {"Sprint": sprint, "Task": task, "Owner": owner, "Role": role, "Hours": hrs}

    # Standard Phase Assignments
    generated_plan.append(assign(sprint_list[0], ["Lead"], "Analysis Phase", "Lead", data["Analysis"]))
    
    dev_sprints = sprint_list[:-1] if num_sprints > 1 else sprint_list
    for s in dev_sprints:
        generated_plan.append(assign(s, dev_names, "Development Work", "Dev", data["Dev"]/len(dev_sprints)))
        generated_plan.append(assign(s, ["Lead"], "Code Review", "Lead", data["Review"]/len(dev_sprints)))

    last_s = sprint_list[-1]
    generated_plan.append(assign(last_s, dev_names, "Bug Fixes", "Dev", data["Fixes"]))
    generated_plan.append(assign(last_s, ["DevOps"], "Deployment", "Ops", data["Deploy"]))

    # Final Plan Construction
    full_df = pd.concat([pd.DataFrame(generated_plan), st.session_state.custom_tasks], ignore_index=True)
    full_df = full_df[full_df['Sprint'].isin(sprint_list)]
    
    # Filter out manually deleted tasks (using unique index for this session)
    full_df = full_df[~full_df.index.isin(st.session_state.deleted_tasks)]
    
    return full_df, sprint_caps

# --- Sidebar Configuration ---
with st.sidebar:
    st.header("📅 Global Parameters")
    start_date = st.date_input("Project Start Date", datetime.now())
    num_sprints = st.selectbox("Number of Sprints", range(1, 11), index=4)
    sprint_days = st.number_input("Sprint Days", 1, 30, 14)
    holidays = st.multiselect("Holidays", [start_date + timedelta(days=x) for x in range(60)])
    
    st.divider()
    daily_hrs = st.slider("Daily Hours", 4, 12, 8)
    buffer_pct = st.slider("Buffer (%)", 0, 50, 10)
    max_cap_base = sprint_days * daily_hrs

    st.divider()
    st.header("👥 Team")
    d_names = [st.text_input(f"Dev {i+1}", f"D{i+1}", key=f"d_{i}") for i in range(3)]
    q_names = [st.text_input(f"QA {i+1}", f"Q{i+1}", key=f"q_{i}") for i in range(1)]

# --- Main Dashboard ---
st.header("🛠️ Sprint Plan Management")

col_m1, col_m2 = st.columns(2)
with col_m1:
    with st.expander("📥 Phase Effort Inputs"):
        h_ana = st.number_input("Analysis Phase", 0, 40)
        h_dev = st.number_input("Development Phase", 0, 400)
        h_rev = st.number_input("Code Review", 0, 100)
        h_fix = st.number_input("Bug Fixes", 0, 100)
        h_dep = st.number_input("Deployment", 0, 40)
with col_m2:
    with st.expander("➕ Add Custom Task"):
        c_sprint = st.selectbox("Sprint", [f"Sprint {i}" for i in range(num_sprints)])
        c_task = st.text_input("Task Name")
        c_owner = st.selectbox("Owner", d_names + q_names + ["Lead", "DevOps"])
        c_hrs = st.number_input("Hours", 1.0, 80.0, 8.0)
        if st.button("Add Task"):
            new_t = pd.DataFrame([{"Sprint": c_sprint, "Task": c_task, "Owner": c_owner, "Role": "Manual", "Hours": c_hrs}])
            st.session_state.custom_tasks = pd.concat([st.session_state.custom_tasks, new_t], ignore_index=True)
            st.rerun()

st.divider()

if st.button("🚀 CALCULATE & SYNC PLAN", type="primary", use_container_width=True):
    phase_data = {"Analysis": h_ana, "Dev": h_dev, "Review": h_rev, "Fixes": h_fix, "Deploy": h_dep}
    final_plan, sprint_caps = run_allocation(d_names, q_names, phase_data, max_cap_base, num_sprints, buffer_pct, start_date, sprint_days, holidays, daily_hrs)
    
    t1, t2 = st.tabs(["🚀 Detailed Roadmap", "📉 Resource Loading"])
    
    with t1:
        for i in range(num_sprints):
            s_label = f"Sprint {i}"
            s_cap = sprint_caps[s_label]
            s_data = final_plan[final_plan['Sprint'] == s_label]
            
            st.subheader(f"📅 {s_label} (Max Capacity: {s_cap:.1f}h)")
            # Interactive data editor to allow for manual task deletion/adjustment
            edited_df = st.data_editor(s_data, use_container_width=True, key=f"edit_{i}", num_rows="dynamic")
            
    with t2:
        load_df = final_plan.groupby(['Sprint', 'Owner'])['Hours'].sum().reset_index()
        load_df['Cap'] = load_df['Sprint'].map(sprint_caps)
        load_df['Util %'] = (load_df['Hours'] / load_df['Cap']) * 100
        st.plotly_chart(px.bar(load_df, x="Sprint", y="Util %", color="Owner", barmode="group"))
else:
    st.info("Awaiting manual input. Click the button above to generate the plan.")
