import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import io

st.set_page_config(page_title="Jarvis Capacity Manager", layout="wide")

# --- Persistent Storage ---
if 'custom_tasks' not in st.session_state:
    st.session_state.custom_tasks = pd.DataFrame(columns=["Sprint", "Task", "Owner", "Role", "Hours"])

# --- Core Allocation Logic ---
def run_allocation(dev_names, qa_names, data, base_cap, num_sprints, buffer_pct, start_date, sprint_days, holidays, daily_hrs):
    generated_plan = []
    baseline_hrs = []
    all_roles = dev_names + qa_names + ["Lead", "DevOps"]
    sprint_list = [f"Sprint {i}" for i in range(num_sprints)]
    resource_load = {s: {name: 0 for name in all_roles} for s in sprint_list}
    sprint_caps = {}

    for i in range(num_sprints):
        s_start = start_date + timedelta(days=i * sprint_days)
        s_end = s_start + timedelta(days=sprint_days)
        h_count = sum(1 for h in holidays if s_start <= h <= s_end)
        s_max = (base_cap - (h_count * daily_hrs)) * (1 - (buffer_pct / 100))
        sprint_caps[f"Sprint {i}"] = max(s_max, 0.1)

    def assign(sprint, names, task, role, hrs, is_baseline=True):
        owner = min(names, key=lambda x: resource_load[sprint][x])
        resource_load[sprint][owner] += hrs
        task_entry = {"Sprint": sprint, "Task": task, "Owner": owner, "Role": role, "Hours": hrs}
        if is_baseline:
            baseline_hrs.append(task_entry)
        return task_entry

    # Logic Distribution
    if data["Analysis"] > 0:
        generated_plan.append(assign(sprint_list[0], ["Lead"], "Analysis Phase", "Lead", data["Analysis"]))
    
    dev_sprints = sprint_list[:-1] if num_sprints > 1 else sprint_list
    for s in dev_sprints:
        if data["Dev"] > 0:
            generated_plan.append(assign(s, dev_names, "Development Work", "Dev", data["Dev"]/len(dev_sprints)))
        if data["Review"] > 0:
            generated_plan.append(assign(s, ["Lead"], "Code Review", "Lead", data["Review"]/len(dev_sprints)))
        if data["TC_Prep"] > 0:
            generated_plan.append(assign(s, qa_names, "TC Preparation", "QA", data["TC_Prep"]/len(dev_sprints)))

    test_idx = min(len(sprint_list)-2, 3) if num_sprints > 3 else max(0, len(sprint_list)-2)
    t_sprint = sprint_list[test_idx]
    if data["QA_Test"] > 0:
        generated_plan.append(assign(t_sprint, qa_names, "QA Testing", "QA", data["QA_Test"]))
    if data["Integ_Test"] > 0:
        generated_plan.append(assign(t_sprint, qa_names, "Integration Testing", "QA", data["Integ_Test"]))

    last_s = sprint_list[-1]
    if data["Fixes"] > 0:
        generated_plan.append(assign(last_s, dev_names, "Bug Fixes", "Dev", data["Fixes"]))
    if data["Bug_Retest"] > 0:
        generated_plan.append(assign(last_s, qa_names, "Bug Retest", "QA", data["Bug_Retest"]))
    if data["Deploy"] > 0:
        generated_plan.append(assign(last_s, ["DevOps"], "Deployment", "Ops", data["Deploy"]))
    if data["Smoke"] > 0:
        generated_plan.append(assign(last_s, qa_names, "Smoke Test", "QA", data["Smoke"]))

    full_df = pd.concat([pd.DataFrame(generated_plan), st.session_state.custom_tasks], ignore_index=True)
    return full_df[full_df['Sprint'].isin(sprint_list)], sprint_caps, pd.DataFrame(baseline_hrs)

# --- Sidebar ---
with st.sidebar:
    st.header("📅 Project Setup")
    start_date = st.date_input("Start Date", datetime.now())
    num_sprints = st.selectbox("Total Sprints", range(1, 11), index=4)
    sprint_days = st.number_input("Days per Sprint", 1, 30, 14)
    holidays = st.multiselect("Public Holidays", [start_date + timedelta(days=x) for x in range(90)])
    
    st.divider()
    daily_hrs = st.slider("Individual Daily Hrs", 4, 12, 8)
    buffer_pct = st.slider("Capacity Buffer (%)", 0, 50, 10)
    max_cap_base = sprint_days * daily_hrs

    st.divider()
    st.header("👥 Team List")
    d_names = [st.text_input(f"Dev {i+1}", f"D{i+1}", key=f"d_{i}") for i in range(3)]
    q_names = [st.text_input(f"QA {i+1}", f"Q{i+1}", key=f"q_{i}") for i in range(1)]

# --- Main UI ---
st.title("Jarvis Phase-Gate Manager")

if st.button("🗑️ Reset All Configuration"):
    st.session_state.custom_tasks = pd.DataFrame(columns=["Sprint", "Task", "Owner", "Role", "Hours"])
    st.rerun()

st.header("🛠️ Planning Inputs")
c_in1, c_in2 = st.columns(2)

with c_in1:
    with st.expander("📥 Effort Estimation (Hours)", expanded=True):
        h_ana = st.number_input("Analysis Phase", min_value=0.0)
        h_dev = st.number_input("Development Phase", min_value=0.0)
        h_rev = st.number_input("Code Review", min_value=0.0)
        h_tcp = st.number_input("TC preparation", min_value=0.0)
        h_qat = st.number_input("QA testing", min_value=0.0)
        h_int = st.number_input("Integration Testing", min_value=0.0)
        h_fix = st.number_input("Bug Fixes", min_value=0.0)
        h_ret = st.number_input("Bug retest", min_value=0.0)
        h_smo = st.number_input("Smoke test", min_value=0.0)
        h_dep = st.number_input("Deployment", min_value=0.0)

with c_in2:
    with st.expander("➕ Manual Task Entry"):
        c_sprint = st.selectbox("Assign to Sprint", [f"Sprint {i}" for i in range(num_sprints)])
        c_task = st.text_input("Task Description")
        c_owner = st.selectbox("Assignee", d_names + q_names + ["Lead", "DevOps"])
        c_hrs = st.number_input("Effort (Hrs)", min_value=0.1, value=8.0)
        if st.button("Insert Task"):
            new_t = pd.DataFrame([{"Sprint": c_sprint, "Task": c_task, "Owner": c_owner, "Role": "Manual", "Hours": c_hrs}])
            st.session_state.custom_tasks = pd.concat([st.session_state.custom_tasks, new_t], ignore_index=True)
            st.rerun()
    st.info(f"Manual tasks count: {len(st.session_state.custom_tasks)}")

st.divider()

if st.button("🚀 CALCULATE & REFRESH DASHBOARD", type="primary", use_container_width=True):
    phase_data = {"Analysis": h_ana, "Dev": h_dev, "Review": h_rev, "TC_Prep": h_tcp, "QA_Test": h_qat, "Integ_Test": h_int, "Fixes": h_fix, "Bug_Retest": h_ret, "Smoke": h_smo, "Deploy": h_dep}
    final_plan, sprint_caps, baseline_df = run_allocation(d_names, q_names, phase_data, max_cap_base, num_sprints, buffer_pct, start_date, sprint_days, holidays, daily_hrs)
    
    # Utilization and Variance Calc
    util_check = final_plan.groupby(['Sprint', 'Owner'])['Hours'].sum().reset_index()
    util_check['Cap'] = util_check['Sprint'].map(sprint_caps)
    util_check['Util_Pct'] = (util_check['Hours'] / util_check['Cap']) * 100

    variance_df = final_plan.groupby('Sprint')['Hours'].sum().reset_index().rename(columns={'Hours': 'Current'})
    base_grouped = baseline_df.groupby('Sprint')['Hours'].sum().reset_index().rename(columns={'Hours': 'Baseline'})
    variance_df = variance_df.merge(base_grouped, on='Sprint', how='left').fillna(0)

    # Excel Download
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        final_plan.to_excel(writer, index=False, sheet_name='Roadmap')
        util_check.to_excel(writer, index=False, sheet_name='Utilization')
    st.download_button("📥 Export Project Plan (.xlsx)", data=buffer.getvalue(), file_name="Project_Plan.xlsx")

    t1, t2 = st.tabs(["🚀 Phase Roadmap", "📉 Capacity & Variance"])
    
    with t1:
        for i in range(num_sprints):
            s_lbl = f"Sprint {i}"
            s_cap = sprint_caps[s_lbl]
            s_data = final_plan[final_plan['Sprint'] == s_lbl].copy()
            s_utils = util_check[util_check['Sprint'] == s_lbl].set_index('Owner')['Util_Pct'].to_dict()
            s_data['Owner_Sprint_Load %'] = s_data['Owner'].map(s_utils)
            
            st.subheader(f"📅 {s_lbl} (Cap: {s_cap:.1f}h)")
            st.dataframe(s_data.style.applymap(lambda v: 'color: red; font-weight: bold' if v > 100 else '', subset=['Owner_Sprint_Load %']).format({'Owner_Sprint_Load %': '{:.1f}%'}), use_container_width=True)

    with t2:
        st.plotly_chart(px.bar(util_check, x="Sprint", y="Util_Pct", color="Owner", barmode="group", title="Resource Utilization (Sentinel View)"))
        st.plotly_chart(px.bar(variance_df, x="Sprint", y=["Baseline", "Current"], barmode="group", title="Sprint Effort Variance (Baseline vs Manual Changes)"))
