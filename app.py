import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io
import plotly.express as px

# Dependency check for Excel
try:
    import xlsxwriter
    EXCEL_SUPPORT = True
except ImportError:
    EXCEL_SUPPORT = False

st.set_page_config(page_title="Jarvis Full Spectrum Architect", layout="wide")

# --- 1. Initialize Memory ---
if 'master_plan' not in st.session_state:
    st.session_state.master_plan = None
if 'sprint_caps' not in st.session_state:
    st.session_state.sprint_caps = {}

# --- 2. Allocation Logic ---
def run_sequential_allocation(dev_names, qa_names, lead_names, data, base_cap, num_sprints, sprint_days, daily_hrs, buffer_pct):
    generated_plan = []
    sprint_list = [f"Sprint {i}" for i in range(num_sprints)]
    all_staff = dev_names + qa_names + lead_names + ["DevOps"]
    resource_load = {s: {name: 0 for name in all_staff} for s in sprint_list}
    sprint_caps = {}

    for i in range(num_sprints):
        s_max = (base_cap) * (1 - (buffer_pct / 100))
        sprint_caps[f"Sprint {i}"] = max(s_max, 0.1)

    def assign(sprint, names, task, role, hrs):
        owner = min(names, key=lambda x: resource_load[sprint][x])
        resource_load[sprint][owner] += hrs
        return {"Sprint": sprint, "Task": task, "Owner": owner, "Role": role, "Hours": float(hrs)}

    # Phase Distribution
    s0 = sprint_list[0]
    generated_plan.append(assign(s0, lead_names, "Analysis Phase", "Lead", data["Analysis"]))
    generated_plan.append(assign(s0, qa_names, "TC Prep (60%)", "QA", data["TC_Prep"] * 0.6))

    dev_sprints = sprint_list[1:-1] if num_sprints > 2 else [sprint_list[1]] if num_sprints > 1 else []
    for s in dev_sprints:
        generated_plan.append(assign(s, dev_names, "Development Work", "Dev", data["Dev"]/len(dev_sprints)))
        generated_plan.append(assign(s, lead_names, "Code Review (Progressive)", "Lead", (data["Review"]*0.7)/len(dev_sprints)))

    test_sprints = sprint_list[2:-1] if num_sprints > 3 else ([sprint_list[2]] if num_sprints > 2 else [])
    if test_sprints:
        generated_plan.append(assign(sprint_list[2], qa_names, "TC Prep (Remaining 40%)", "QA", data["TC_Prep"] * 0.4))
        for s in test_sprints:
            generated_plan.append(assign(s, qa_names, "QA Testing", "QA", data["QA_Test"]/len(test_sprints)))
            generated_plan.append(assign(s, qa_names, "Integration Testing", "QA", data["Integ_Test"]/len(test_sprints)))

    last_s = sprint_list[-1]
    generated_plan.append(assign(last_s, dev_names, "Bug Fixes", "Dev", data["Fixes"]))
    generated_plan.append(assign(last_s, qa_names, "Bug Retest", "QA", data["Bug_Retest"]))
    generated_plan.append(assign(last_s, lead_names, "Final Code Review", "Lead", data["Review"] * 0.3))
    generated_plan.append(assign(last_s, ["DevOps"], "Deployment", "Ops", data["Deploy"]))
    generated_plan.append(assign(last_s, qa_names, "Smoke Test", "QA", data["Smoke"]))

    return pd.DataFrame(generated_plan), sprint_caps

# --- 3. Sidebar ---
with st.sidebar:
    st.header("👥 Team Setup")
    d_count = st.number_input("Devs", 1, 10, 3)
    q_count = st.number_input("QA", 1, 10, 1)
    l_count = st.number_input("Leads", 1, 5, 1)
    
    dev_names = [st.text_input(f"Dev {i+1}", f"D{i+1}", key=f"dn_{i}") for i in range(d_count)]
    qa_names = [st.text_input(f"QA {i+1}", f"Q{i+1}", key=f"qn_{i}") for i in range(q_count)]
    lead_names = [st.text_input(f"Lead {i+1}", f"L{i+1}", key=f"ln_{i}") for i in range(l_count)]

    st.header("📅 Settings")
    num_sprints = st.selectbox("Total Sprints", range(2, 11), index=3)
    sprint_days = st.number_input("Days/Sprint", 1, 30, 14)
    daily_hrs = st.slider("Daily Hrs", 4, 12, 8)
    buffer_pct = st.slider("Buffer %", 0, 50, 10)
    max_cap_base = sprint_days * daily_hrs

# --- 4. Main UI ---
st.title("Jarvis Phase-Gate Manager")

with st.expander("📥 Effort Baseline"):
    inputs = {
        "Analysis": st.number_input("Analysis", value=25.0), "Dev": st.number_input("Dev", value=150.0),
        "Review": st.number_input("Review", value=20.0), "TC_Prep": st.number_input("TC Prep", value=40.0), 
        "QA_Test": st.number_input("QA Test", value=80.0), "Integ_Test": st.number_input("Integ Test", value=20.0),
        "Fixes": st.number_input("Fixes", value=30.0), "Bug_Retest": st.number_input("Retest", value=15.0), 
        "Smoke": st.number_input("Smoke", value=8.0), "Deploy": st.number_input("Deploy", value=6.0)
    }

if st.button("🚀 GENERATE INITIAL PLAN", type="primary", use_container_width=True):
    plan, caps = run_sequential_allocation(dev_names, qa_names, lead_names, inputs, max_cap_base, num_sprints, sprint_days, daily_hrs, buffer_pct)
    st.session_state.master_plan = plan
    st.session_state.sprint_caps = caps

if st.session_state.master_plan is not None:
    # --- High-Level Timeline Breakdown ---
    st.header("📍 Sprint Breakdown View")
    timeline = st.session_state.master_plan.groupby('Sprint')['Task'].apply(lambda x: ", ".join(set(x))).reset_index()
    st.table(timeline)

    st.divider()
    st.header("📝 Detailed Roadmap Editor")
    st.session_state.master_plan = st.data_editor(
        st.session_state.master_plan,
        use_container_width=True,
        key="main_editor",
        column_config={"Hours": st.column_config.NumberColumn("Hours", format="%.1f")}
    )

    # --- Metrics & Validation ---
    st.divider()
    base_sum = sum(inputs.values())
    curr_sum = st.session_state.master_plan['Hours'].sum()
    
    util = st.session_state.master_plan.groupby(['Sprint', 'Owner'])['Hours'].sum().reset_index()
    util['Cap'] = util['Sprint'].map(st.session_state.sprint_caps)
    overloads = util[util['Hours'] > util['Cap']]

    m1, m2, m3 = st.columns(3)
    m1.metric("Baseline Total", f"{base_sum:.1f}h")
    m2.metric("Adjusted Total", f"{curr_sum:.1f}h", delta=f"{curr_sum - base_sum:.1f}h", delta_color="inverse")
    m3.metric("Overloaded Staff", len(overloads))

    if not overloads.empty:
        st.error("⚠️ Over-allocation detected in charts below.")

    st.plotly_chart(px.bar(util, x="Sprint", y="Hours", color="Owner", barmode="group", 
                           title="Resource Load Comparison"), use_container_width=True)

    if EXCEL_SUPPORT:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
            st.session_state.master_plan.to_excel(writer, index=False)
        st.download_button("📥 Export Final Plan", data=buf.getvalue(), file_name="Jarvis_Plan.xlsx")

if st.button("🗑️ Reset All"):
    st.session_state.master_plan = None
    st.rerun()
