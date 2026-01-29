import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(page_title="Jarvis Leveling Architect", layout="wide")

# --- Core Allocation & Leveling Logic ---
def run_allocation(dev_names, qa_names, data, max_cap, apply_leveling=False):
    plan = []
    all_roles = dev_names + qa_names + ["Lead", "DevOps"]
    resource_load = {f"Sprint {i}": {name: 0 for name in all_roles} for i in range(5)}
    
    def assign(sprint, names, task, role, hrs):
        # If leveling is enabled, we sort names by current load to pick the least busy
        if apply_leveling:
            owner = min(names, key=lambda x: resource_load[sprint][x])
        else:
            # Standard sequential-first balancing
            owner = min(names, key=lambda x: resource_load[sprint][x])
            
        resource_load[sprint][owner] += hrs
        return {"Sprint": sprint, "Task": task, "Owner": owner, "Role": role, "Hours": hrs}

    # S0: Analysis
    plan.append(assign("Sprint 0", ["Lead"], "Analysis Phase", "Lead", data["Analysis Phase"]))
    
    # S1 & S2: Dev & Review
    dev_split = data["Development Phase"] / 2
    rev_split = data["Code Review"] / 2
    
    for s in ["Sprint 1", "Sprint 2"]:
        if s == "Sprint 1":
            plan.append(assign(s, qa_names, "TC preparation", "QA", data["TC preparation"]))
        
        # Dev tasks are assigned individually to allow for balancing
        # We split the total dev hours by 10 units per sprint for better leveling granularity
        units = 10
        unit_hrs = (dev_split / units)
        for _ in range(units):
            plan.append(assign(s, dev_names, "Development Work", "Dev", unit_hrs))
            
        plan.append(assign(s, ["Lead"], "Code Review", "Lead", rev_split))

    # S3: QA
    plan.append(assign("Sprint 3", qa_names, "QA testing", "QA", data["QA testing"]))
    plan.append(assign("Sprint 3", qa_names, "Integration testing", "QA", data["Integration testing"]))

    # S4: Launch
    plan.append(assign("Sprint 4", dev_names, "Bug Fixes", "Dev", data["Bug Fixes"]))
    plan.append(assign("Sprint 4", qa_names, "Bug retest", "QA", data["Bug retest"]))
    plan.append(assign("Sprint 4", ["DevOps"], "Merge and Deploy", "Ops", data["Merge and Deploy"]))
    plan.append(assign("Sprint 4", qa_names, "Smoke test", "QA", data["Smoke test"]))
    
    return pd.DataFrame(plan)

# --- Sidebar ---
with st.sidebar:
    st.header("👥 Team & Timeline")
    total_size = st.number_input("Total Team Size", 1, 50, 5)
    d_count = st.number_input("Dev Team Size", 1, total_size, 3)
    q_count = st.number_input("QA Team Size", 1, total_size - d_count, 1)
    
    dev_names = [st.text_input(f"Dev {i+1}", f"D{i+1}", key=f"d_{i}") for i in range(d_count)]
    qa_names = [st.text_input(f"QA {i+1}", f"Q{i+1}", key=f"q_{i}") for i in range(q_count)]

    st.divider()
    sprint_days = st.number_input("Sprint Days", 1, 30, 10)
    daily_hrs = st.slider("Daily Hours", 4, 12, 8)
    max_cap = sprint_days * daily_hrs
    
    st.divider()
    leveling_on = st.toggle("Enable Resource Leveling", value=True, help="Automatically balances tasks across the team to avoid overload.")

# --- Main Effort Inputs ---
st.header("📊 Phase Effort (Hours)")
c1, c2, c3 = st.columns(3)
with c1:
    h_ana = st.number_input("Analysis Phase", 0, 500, 40)
    h_dev = st.number_input("Development Phase", 0, 2000, 240)
    h_rev = st.number_input("Code Review", 0, 500, 40)
with c2:
    h_tc = st.number_input("TC preparation", 0, 500, 30)
    h_qa = st.number_input("QA testing", 0, 1000, 80)
    h_int = st.number_input("Integration testing", 0, 500, 40)
with c3:
    h_fix = st.number_input("Bug Fixes", 0, 500, 40)
    h_ret = st.number_input("Bug retest", 0, 500, 20)
    h_dep = st.number_input("Merge and Deploy", 0, 500, 16)
    h_smo = st.number_input("Smoke test", 0, 500, 8)

manual_data = {
    "Analysis Phase": h_ana, "Development Phase": h_dev, "Code Review": h_rev,
    "TC preparation": h_tc, "QA testing": h_qa, "Integration testing": h_int,
    "Bug Fixes": h_fix, "Bug retest": h_ret, "Merge and Deploy": h_dep, "Smoke test": h_smo
}

# --- Dashboard ---
final_plan = run_allocation(dev_names, qa_names, manual_data, max_cap, apply_leveling=leveling_on)

t1, t2 = st.tabs(["🚀 Phase Roadmap", "📉 Utilization Dashboard"])

with t1:
    for i in range(5):
        s_name = f"Sprint {i}"
        s_data = final_plan[final_plan['Sprint'] == s_name].copy()
        
        # Aggregate tasks for display clarity
        display_df = s_data.groupby(['Task', 'Owner', 'Role'])['Hours'].sum().reset_index()
        display_df['Util %'] = (display_df['Hours'] / max_cap) * 100
        
        with st.expander(f"{s_name}"):
            st.dataframe(display_df.style.format({'Util %': '{:.1f}%'}), use_container_width=True, hide_index=True)

with t2:
    load_df = final_plan.groupby(['Sprint', 'Owner'])['Hours'].sum().reset_index()
    load_df['Util %'] = (load_df['Hours'] / max_cap) * 100
    
    fig = px.bar(load_df, x="Sprint", y="Util %", color="Owner", barmode="group",
                 title="Team Utilization Balance")
    fig.add_hline(y=100, line_dash="dash", line_color="red", annotation_text="100% Capacity")
    st.plotly_chart(fig, use_container_width=True)
