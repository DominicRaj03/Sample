import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(page_title="Jarvis Holiday Architect", layout="wide")

# --- Core Allocation Logic ---
def run_allocation(dev_names, qa_names, data, base_cap, num_sprints, buffer_pct, start_date, sprint_days, holidays, daily_hrs):
    plan = []
    all_roles = dev_names + qa_names + ["Lead", "DevOps"]
    sprint_list = [f"Sprint {i}" for i in range(num_sprints)]
    resource_load = {s: {name: 0 for name in all_roles} for s in sprint_list}
    sprint_caps = {}

    # Calculate individual sprint capacities based on holidays
    for i in range(num_sprints):
        s_start = start_date + timedelta(days=i * sprint_days)
        s_end = s_start + timedelta(days=sprint_days)
        
        # Count holidays in this range
        h_count = sum(1 for h in holidays if s_start <= h <= s_end)
        reduced_hrs = h_count * daily_hrs
        
        # Max capacity for this sprint after holidays and buffer
        s_max = (base_cap - reduced_hrs) * (1 - (buffer_pct / 100))
        sprint_caps[f"Sprint {i}"] = max(s_max, 1) # Ensure at least 1hr capacity

    def assign(sprint, names, task, role, hrs):
        owner = min(names, key=lambda x: resource_load[sprint][x])
        resource_load[sprint][owner] += hrs
        return {"Sprint": sprint, "Task": task, "Owner": owner, "Role": role, "Hours": hrs}

    # 1. S0: Analysis
    plan.append(assign(sprint_list[0], ["Lead"], "Analysis Phase", "Lead", data["Analysis Phase"]))
    
    # 2. Middle: Dev & Review
    dev_sprints = sprint_list[:-1] if num_sprints > 1 else sprint_list
    dev_per_sprint = data["Development Phase"] / len(dev_sprints)
    rev_per_sprint = data["Code Review"] / len(dev_sprints)
    tc_per_sprint = data["TC preparation"] / len(dev_sprints)

    for s in dev_sprints:
        plan.append(assign(s, qa_names, "TC preparation", "QA", tc_per_sprint))
        for _ in range(5): # Leveling chunks
            plan.append(assign(s, dev_names, "Development Work", "Dev", (dev_per_sprint/5)))
        plan.append(assign(s, ["Lead"], "Code Review", "Lead", rev_per_sprint))

    # 3. Execution (Testing)
    test_idx = min(len(sprint_list)-2, 3) if num_sprints > 3 else max(0, len(sprint_list)-2)
    plan.append(assign(sprint_list[test_idx], qa_names, "QA testing", "QA", data["QA testing"]))
    plan.append(assign(sprint_list[test_idx], qa_names, "Integration testing", "QA", data["Integration testing"]))

    # 4. Final: Launch
    last_s = sprint_list[-1]
    plan.append(assign(last_s, dev_names, "Bug Fixes", "Dev", data["Bug Fixes"]))
    plan.append(assign(last_s, ["DevOps"], "Merge and Deploy", "Ops", data["Merge and Deploy"]))
    
    return pd.DataFrame(plan), sprint_caps

# --- Sidebar ---
with st.sidebar:
    st.header("📅 Timeline & Holidays")
    start_date = st.date_input("Project Start Date", datetime.now())
    num_sprints = st.selectbox("Number of Sprints", range(1, 11), index=4)
    sprint_days = st.number_input("Sprint Duration (Days)", 1, 30, 14) # Default 2 weeks
    
    st.divider()
    holidays = st.multiselect("Select Public Holidays", 
                               [start_date + timedelta(days=x) for x in range(120)],
                               format_func=lambda x: x.strftime("%Y-%m-%d"))

    st.divider()
    st.header("🛡️ Capacity & Safety")
    daily_hrs = st.slider("Daily Hours", 4, 12, 8)
    buffer_pct = st.slider("Sprint Buffer (%)", 0, 50, 10)
    max_cap_base = sprint_days * daily_hrs

    st.divider()
    st.header("👥 Team")
    d_count = st.number_input("Dev Size", 1, 10, 3)
    q_count = st.number_input("QA Size", 1, 10, 1)
    dev_names = [st.text_input(f"Dev {i+1}", f"D{i+1}", key=f"d_{i}") for i in range(d_count)]
    qa_names = [st.text_input(f"QA {i+1}", f"Q{i+1}", key=f"q_{i}") for i in range(q_count)]

# --- Main Effort Inputs ---
st.header("📊 Phase Effort Calibration")
c1, c2, c3 = st.columns(3)
with c1:
    h_ana = st.number_input("Analysis Phase", 0, 500, 40)
    h_dev = st.number_input("Development Phase", 0, 2000, 240)
with c2:
    h_rev = st.number_input("Code Review", 0, 500, 40)
    h_tc = st.number_input("TC preparation", 0, 500, 30)
    h_qa = st.number_input("QA testing", 0, 1000, 80)
with c3:
    h_int = st.number_input("Integration testing", 0, 500, 40)
    h_fix = st.number_input("Bug Fixes", 0, 500, 40)
    h_dep = st.number_input("Merge and Deploy", 0, 500, 16)

manual_data = {
    "Analysis Phase": h_ana, "Development Phase": h_dev, "Code Review": h_rev,
    "TC preparation": h_tc, "QA testing": h_qa, "Integration testing": h_int,
    "Bug Fixes": h_fix, "Merge and Deploy": h_dep
}

# --- Results & Tabs ---
final_plan, sprint_caps = run_allocation(dev_names, qa_names, manual_data, max_cap_base, num_sprints, buffer_pct, start_date, sprint_days, holidays, daily_hrs)

t1, t2 = st.tabs(["🚀 Calendar Roadmap", "📉 Holiday Capacity Analysis"])

with t1:
    for i in range(num_sprints):
        s_label = f"Sprint {i}"
        s_cap = sprint_caps[s_label]
        s_data = final_plan[final_plan['Sprint'] == s_label].copy()
        display_df = s_data.groupby(['Task', 'Owner', 'Role'])['Hours'].sum().reset_index()
        display_df['Util %'] = (display_df['Hours'] / s_cap) * 100
        
        with st.expander(f"📅 {s_label} | Capacity: {s_cap:.1f}h (after holidays/buffer)"):
            st.dataframe(display_df.style.format({'Util %': '{:.1f}%'}), use_container_width=True, hide_index=True)

with t2:
    load_df = final_plan.groupby(['Sprint', 'Owner'])['Hours'].sum().reset_index()
    # Map the dynamic capacity for each specific sprint
    load_df['Sprint_Cap'] = load_df['Sprint'].map(sprint_caps)
    load_df['Util %'] = (load_df['Hours'] / load_df['Sprint_Cap']) * 100
    
    st.plotly_chart(px.bar(load_df, x="Sprint", y="Util %", color="Owner", barmode="group", 
                 title="Impact of Holidays on Team Utilization"))
