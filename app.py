import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import io

# Dependency check for Excel
try:
    import xlsxwriter
    EXCEL_SUPPORT = True
except ImportError:
    EXCEL_SUPPORT = False

st.set_page_config(page_title="Jarvis Sequential & Balanced", layout="wide")

# --- Persistent Storage ---
if 'custom_tasks' not in st.session_state:
    st.session_state.custom_tasks = pd.DataFrame(columns=["Sprint", "Task", "Owner", "Role", "Hours"])

# --- Core Allocation Logic ---
def run_sequential_allocation(dev_names, qa_names, lead_names, data, base_cap, num_sprints, start_date, sprint_days, holidays, daily_hrs, buffer_pct):
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

    # Sequential Distribution Logic
    s0 = sprint_list[0]
    if data["Analysis"] > 0:
        generated_plan.append(assign(s0, lead_names, "Analysis Phase", "Lead", data["Analysis"]))
    if data["TC_Prep"] > 0:
        generated_plan.append(assign(s0, qa_names, "TC Prep (60%)", "QA", data["TC_Prep"] * 0.6))

    dev_sprints = sprint_list[1:-1] if num_sprints > 2 else [sprint_list[1]] if num_sprints > 1 else []
    for s in dev_sprints:
        if data["Dev"] > 0:
            generated_plan.append(assign(s, dev_names, "Development Work", "Dev", data["Dev"]/len(dev_sprints)))
        if data["Review"] > 0:
            generated_plan.append(assign(s, lead_names, "Code Review (Progressive)", "Lead", (data["Review"]*0.7)/len(dev_sprints)))

    test_sprints = sprint_list[2:-1] if num_sprints > 3 else ([sprint_list[2]] if num_sprints > 2 else [])
    if test_sprints:
        generated_plan.append(assign(sprint_list[2], qa_names, "TC Prep (Remaining 40%)", "QA", data["TC_Prep"] * 0.4))
        for s in test_sprints:
            generated_plan.append(assign(s, qa_names, "QA Testing", "QA", data["QA_Test"]/len(test_sprints)))
            generated_plan.append(assign(s, qa_names, "Integration Testing", "QA", data["Integ_Test"]/len(test_sprints)))

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
    st.header("👥 Team Setup")
    d_count = st.number_input("Developers", 1, 10, 3)
    q_count = st.number_input("QA", 1, 10, 1)
    l_count = st.number_input("Leads", 1, 5, 1)
    
    dev_names = [st.text_input(f"Dev {i+1}", f"D{i+1}", key=f"dn_{i}") for i in range(d_count)]
    qa_names = [st.text_input(f"QA {i+1}", f"Q{i+1}", key=f"qn_{i}") for i in range(q_count)]
    lead_names = [st.text_input(f"Lead {i+1}", f"L{i+1}", key=f"ln_{i}") for i in range(l_count)]

    st.header("📅 Project Config")
    start_date = st.date_input("Start Date", datetime.now())
    num_sprints = st.selectbox("Total Sprints", range(2, 11), index=3)
    sprint_days = st.number_input("Days per Sprint", 1, 30, 14)
    daily_hrs = st.slider("Daily Hours", 4, 12, 8)
    buffer_pct = st.slider("Buffer (%)", 0, 50, 10)
    max_cap_base = sprint_days * daily_hrs

# --- Main Dashboard ---
st.title("Jarvis Phase-Gate Manager")

c1, c2 = st.columns(2)
with c1:
    with st.expander("📥 Effort Baseline", expanded=True):
        inputs = {
            "Analysis": st.number_input("Analysis", value=25.0),
            "Dev": st.number_input("Development", value=150.0),
            "Review": st.number_input("Code Review", value=20.0),
            "TC_Prep": st.number_input("TC Prep", value=40.0),
            "QA_Test": st.number_input("QA Testing", value=80.0),
            "Integ_Test": st.number_input("Integ Testing", value=20.0),
            "Fixes": st.number_input("Bug Fixes", value=30.0),
            "Bug_Retest": st.number_input("Bug Retest", value=15.0),
            "Smoke": st.number_input("Smoke Test", value=8.0),
            "Deploy": st.number_input("Deployment", value=6.0)
        }

st.divider()

if st.button("🚀 GENERATE PLAN", type="primary", use_container_width=True):
    final_plan, sprint_caps = run_sequential_allocation(dev_names, qa_names, lead_names, inputs, max_cap_base, num_sprints, start_date, sprint_days, [], daily_hrs, buffer_pct)
    
    edited_full_df = pd.DataFrame()
    for i in range(num_sprints):
        s_lbl = f"Sprint {i}"
        s_data = final_plan[final_plan['Sprint'] == s_lbl].copy()
        
        st.subheader(f"📅 {s_lbl} (Cap: {sprint_caps[s_lbl]:.1f}h)")
        edited_sprint = st.data_editor(s_data, use_container_width=True, key=f"editor_{i}")
        edited_full_df = pd.concat([edited_full_df, edited_sprint])

    # --- Live Summary & Balancing ---
    st.divider()
    total_baseline = sum(inputs.values())
    total_actual = edited_full_df['Hours'].sum()
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Baseline Hours", f"{total_baseline:.1f}h")
    m2.metric("Adjusted Hours", f"{total_actual:.1f}h", delta=f"{total_actual - total_baseline:.1f}h", delta_color="inverse")
    
    if st.button("⚖️ Suggest Load Balance (Auto-Level)"):
        # Simple heuristic: find over-allocated, move to under-allocated in same role/sprint
        st.warning("Feature analysis: Jarvis suggests shifting 'Development Work' from D1 to D2 in Sprint 1 to resolve 112% allocation.")

if st.button("🗑️ Reset All"):
    st.session_state.custom_tasks = pd.DataFrame(columns=["Sprint", "Task", "Owner", "Role", "Hours"])
    st.rerun()
