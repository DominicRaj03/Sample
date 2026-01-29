import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import io

# Visual check for the required engine
try:
    import xlsxwriter
    EXCEL_SUPPORT = True
except ImportError:
    EXCEL_SUPPORT = False

st.set_page_config(page_title="Jarvis Sequential Architect", layout="wide")

if 'custom_tasks' not in st.session_state:
    st.session_state.custom_tasks = pd.DataFrame(columns=["Sprint", "Task", "Owner", "Role", "Hours"])

# --- Core Sequential Allocation Logic ---
def run_sequential_allocation(dev_names, qa_names, lead_names, data, base_cap, num_sprints, buffer_pct, start_date, sprint_days, holidays, daily_hrs):
    generated_plan = []
    sprint_list = [f"Sprint {i}" for i in range(num_sprints)]
    all_staff = dev_names + qa_names + lead_names + ["DevOps"]
    resource_load = {s: {name: 0 for name in all_staff} for s in sprint_list}
    sprint_caps = {}

    for i in range(num_sprints):
        s_start = start_date + timedelta(days=i * sprint_days)
        s_end = s_start + timedelta(days=sprint_days)
        h_count = sum(1 for h in holidays if s_start <= h <= s_end)
        s_max = (base_cap - (h_count * daily_hrs)) * (1 - (buffer_pct / 100))
        sprint_caps[f"Sprint {i}"] = max(s_max, 0.1)

    def assign(sprint, names, task, role, hrs):
        owner = min(names, key=lambda x: resource_load[sprint][x])
        resource_load[sprint][owner] += hrs
        return {"Sprint": sprint, "Task": task, "Owner": owner, "Role": role, "Hours": hrs}

    # --- SPRINT 0: Analysis & 60% TC Prep ---
    s0 = sprint_list[0]
    if data["Analysis"] > 0:
        generated_plan.append(assign(s0, lead_names, "Analysis Phase", "Lead", data["Analysis"]))
    if data["TC_Prep"] > 0:
        generated_plan.append(assign(s0, qa_names, "TC Prep (60%)", "QA", data["TC_Prep"] * 0.6))

    # --- SPRINT 1+: Development Start ---
    # Dev and Review spread from Sprint 1 to Penultimate Sprint
    dev_sprints = sprint_list[1:-1] if num_sprints > 2 else [sprint_list[1]] if num_sprints > 1 else []
    if dev_sprints:
        for s in dev_sprints:
            generated_plan.append(assign(s, dev_names, "Development Work", "Dev", data["Dev"]/len(dev_sprints)))
            # Code reviews distributed where dev happens
            generated_plan.append(assign(s, lead_names, "Code Review (Progressive)", "Lead", (data["Review"]*0.7)/len(dev_sprints)))

    # --- SPRINT 2+: Testing Start & Remaining TC Prep ---
    test_sprints = sprint_list[2:-1] if num_sprints > 3 else [sprint_list[2]] if num_sprints > 2 else []
    if test_sprints:
        # Close remaining 40% TC Prep in Sprint 2
        generated_plan.append(assign(sprint_list[2], qa_names, "TC Prep (Remaining 40%)", "QA", data["TC_Prep"] * 0.4))
        for s in test_sprints:
            generated_plan.append(assign(s, qa_names, "QA Testing", "QA", data["QA_Test"]/len(test_sprints)))
            generated_plan.append(assign(s, qa_names, "Integration Testing", "QA", data["Integ_Test"]/len(test_sprints)))

    # --- FINAL SPRINT: Stabilization & Release ---
    last_s = sprint_list[-1]
    if num_sprints > 1:
        generated_plan.append(assign(last_s, dev_names, "Bug Fixes", "Dev", data["Fixes"]))
        generated_plan.append(assign(last_s, qa_names, "Bug Retest", "QA", data["Bug_Retest"]))
        generated_plan.append(assign(last_s, lead_names, "Final Code Review", "Lead", data["Review"] * 0.3))
        generated_plan.append(assign(last_s, ["DevOps"], "Deployment", "Ops", data["Deploy"]))
        generated_plan.append(assign(last_s, qa_names, "Smoke Test", "QA", data["Smoke"]))

    full_df = pd.concat([pd.DataFrame(generated_plan), st.session_state.custom_tasks], ignore_index=True)
    return full_df[full_df['Sprint'].isin(sprint_list)], sprint_caps

# --- Sidebar ---
with st.sidebar:
    st.header("👥 Team Size & Split")
    d_count = st.number_input("Developers", 1, 20, 3)
    q_count = st.number_input("QA", 1, 20, 1)
    l_count = st.number_input("Leads", 1, 5, 1)
    
    st.divider()
    dev_names = [st.text_input(f"Dev {i+1}", f"D{i+1}", key=f"d_{i}") for i in range(d_count)]
    qa_names = [st.text_input(f"QA {i+1}", f"Q{i+1}", key=f"q_{i}") for i in range(q_count)]
    lead_names = [st.text_input(f"Lead {i+1}", f"L{i+1}", key=f"l_{i}") for i in range(l_count)]

    st.divider()
    st.header("📅 Timeline")
    start_date = st.date_input("Start Date", datetime.now())
    num_sprints = st.selectbox("Total Sprints", range(2, 11), index=3) # Min 2 for the logic
    sprint_days = st.number_input("Days per Sprint", 1, 30, 14)
    daily_hrs = st.slider("Daily Hrs", 4, 12, 8)
    buffer_pct = st.slider("Buffer (%)", 0, 50, 10)
    max_cap_base = sprint_days * daily_hrs

# --- Main Dashboard ---
st.title("Jarvis Phase-Gate Manager")

col_in1, col_in2 = st.columns(2)
with col_in1:
    with st.expander("📥 Effort Inputs", expanded=True):
        h_ana = st.number_input("Analysis Phase", min_value=0.0, value=25.0)
        h_dev = st.number_input("Development Phase", min_value=0.0, value=150.0)
        h_rev = st.number_input("Code Review", min_value=0.0, value=20.0)
        h_tcp = st.number_input("TC preparation", min_value=0.0, value=40.0)
        h_qat = st.number_input("QA testing", min_value=0.0, value=80.0)
        h_int = st.number_input("Integration Testing", min_value=0.0, value=20.0)
        h_fix = st.number_input("Bug Fixes", min_value=0.0, value=30.0)
        h_ret = st.number_input("Bug retest", min_value=0.0, value=15.0)
        h_smo = st.number_input("Smoke test", min_value=0.0, value=8.0)
        h_dep = st.number_input("Deployment", min_value=0.0, value=6.0)

with col_in2:
    with st.expander("➕ Manual Tasks"):
        c_sprint = st.selectbox("Sprint", [f"Sprint {i}" for i in range(num_sprints)])
        c_task = st.text_input("Task Description")
        c_owner = st.selectbox("Assignee", dev_names + qa_names + lead_names + ["DevOps"])
        c_hrs = st.number_input("Hrs", min_value=0.1, value=8.0)
        if st.button("Add Task"):
            new_t = pd.DataFrame([{"Sprint": c_sprint, "Task": c_task, "Owner": c_owner, "Role": "Manual", "Hours": c_hrs}])
            st.session_state.custom_tasks = pd.concat([st.session_state.custom_tasks, new_t], ignore_index=True)
            st.rerun()
    if st.button("🗑️ Reset All"):
        st.session_state.custom_tasks = pd.DataFrame(columns=["Sprint", "Task", "Owner", "Role", "Hours"])
        st.rerun()

st.divider()

if st.button("🚀 CALCULATE SEQUENTIAL PLAN", type="primary", use_container_width=True):
    phase_data = {"Analysis": h_ana, "Dev": h_dev, "Review": h_rev, "TC_Prep": h_tcp, "QA_Test": h_qat, "Integ_Test": h_int, "Fixes": h_fix, "Bug_Retest": h_ret, "Smoke": h_smo, "Deploy": h_dep}
    final_plan, sprint_caps = run_sequential_allocation(dev_names, qa_names, lead_names, phase_data, max_cap_base, num_sprints, buffer_pct, start_date, sprint_days, [], daily_hrs)
    
    # Utilization Check
    util_check = final_plan.groupby(['Sprint', 'Owner'])['Hours'].sum().reset_index()
    util_check['Cap'] = util_check['Sprint'].map(sprint_caps)
    util_check['Util %'] = (util_check['Hours'] / util_check['Cap']) * 100

    t1, t2 = st.tabs(["🚀 Sequential Roadmap", "📉 Resource Load"])
    with t1:
        for i in range(num_sprints):
            s_lbl = f"Sprint {i}"
            s_data = final_plan[final_plan['Sprint'] == s_lbl].copy()
            s_utils = util_check[util_check['Sprint'] == s_lbl].set_index('Owner')['Util %'].to_dict()
            s_data['Staff Load %'] = s_data['Owner'].map(s_utils)
            st.subheader(f"📅 {s_lbl} (Capacity: {sprint_caps[s_lbl]:.1f}h)")
            st.dataframe(s_data.style.applymap(lambda v: 'color: red; font-weight: bold' if v > 100 else '', subset=['Staff Load %']).format({'Staff Load %': '{:.1f}%'}), use_container_width=True)
    with t2:
        st.plotly_chart(px.bar(util_check, x="Sprint", y="Util %", color="Owner", barmode="group", title="Resource Utilization by Role"))
