import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Jarvis Cost Architect", layout="wide")

# --- Session State ---
if 'manual_overrides' not in st.session_state:
    st.session_state.manual_overrides = {}
if 'resource_away' not in st.session_state:
    st.session_state.resource_away = {}

# --- Logic Core ---
def run_phase_allocation(dev_data, qa_data, splits):
    plan = []
    dev_names = [d['name'] for d in dev_data]
    qa_names = [q['name'] for q in qa_data]
    
    resource_load = {f"Sprint {i}": {name: 0 for name in dev_names + qa_names + ["Lead", "Designer", "DevOps"]} for i in range(5)}

    def assign_work(sprint, names, task_name, role, hours, rate_map):
        ov_key = f"{sprint}_{task_name}"
        if ov_key in st.session_state.manual_overrides:
            owner = st.session_state.manual_overrides[ov_key]
        else:
            avail = [n for n in names if not st.session_state.resource_away.get(f"{sprint}_{n}", False)]
            owner = min(avail, key=lambda x: resource_load[sprint][x]) if avail else names[0]
        
        resource_load[sprint][owner] += hours
        cost = hours * rate_map.get(owner, 50) # Default rate $50
        return {"Sprint": sprint, "Task": task_name, "Owner": owner, "Role": role, "Hours": hours, "Cost": cost}

    # Build Rate Map
    rate_map = {d['name']: d['rate'] for d in dev_data}
    rate_map.update({q['name']: q['rate'] for q in qa_data})
    rate_map.update({"Lead": 100, "Designer": 80, "DevOps": 90})

    # Allocation logic
    plan.append(assign_work("Sprint 0", ["Lead"], "Analysis", "Lead", splits['Analysis'], rate_map))
    
    dev_per_sprint = splits['TotalDev'] / 2
    review_per_sprint = splits['CodeReview'] / 2
    
    for s in ["Sprint 1", "Sprint 2"]:
        if s == "Sprint 1":
            plan.append(assign_work(s, qa_names, "Test Prep", "QA", splits['QA'] * 0.20, rate_map))
        for d_name in dev_names:
            plan.append(assign_work(s, [d_name], f"Dev: {d_name}", "Dev", dev_per_sprint / len(dev_names), rate_map))
            plan.append(assign_work(s, [d_name], f"Review: {d_name}", "Dev", review_per_sprint / len(dev_names), rate_map))

    plan.append(assign_work("Sprint 3", qa_names, "QA Execution", "QA", splits['QA'] * 0.80, rate_map))
    plan.append(assign_work("Sprint 4", dev_names, "Bug Fixes", "Dev", splits['BugFixes'], rate_map))
    plan.append(assign_work("Sprint 4", qa_names, "Bug Retest", "QA", splits['BugRetest'], rate_map))
    plan.append(assign_work("Sprint 4", ["DevOps"], "Merge/Deploy", "Ops", splits['MergeDeploy'], rate_map))
    
    return pd.DataFrame(plan)

# --- Sidebar ---
with st.sidebar:
    st.header("👥 Team & Rates")
    total_team = st.number_input("Total Team Size", 1, 50, 4)
    d_count = st.number_input("Dev Count", 1, total_team, 3)
    q_count = st.number_input("QA Count", 1, total_team, 1)

    dev_info = []
    for i in range(d_count):
        c1, c2 = st.columns(2)
        name = c1.text_input(f"Dev {i+1}", f"D{i+1}", key=f"dn_{i}")
        rate = c2.number_input(f"Rate/h", 30, 200, 60, key=f"dr_{i}")
        dev_info.append({'name': name, 'rate': rate})

    qa_info = []
    for i in range(q_count):
        c1, c2 = st.columns(2)
        name = c1.text_input(f"QA {i+1}", f"Q{i+1}", key=f"qn_{i}")
        rate = c2.number_input(f"Rate/h", 30, 200, 45, key=f"qr_{i}")
        qa_info.append({'name': name, 'rate': rate})
    
    st.divider()
    sprint_days = st.number_input("Sprint Days", 1, 30, 12)
    max_cap = sprint_days * 8

# --- Main Dashboard ---
splits = {'Analysis': 40, 'TotalDev': 240, 'CodeReview': 40, 'QA': 100, 'BugFixes': 40, 'BugRetest': 20, 'MergeDeploy': 16}
final_plan = run_phase_allocation(dev_info, qa_info, splits)

t1, t2 = st.tabs(["💰 Budget View", "🚀 Sprint Roadmap"])

with t1:
    total_cost = final_plan['Cost'].sum()
    st.metric("Total Project Cost", f"${total_cost:,.2f}")
    
    cost_df = final_plan.groupby('Sprint')['Cost'].sum().reset_index()
    st.plotly_chart(px.pie(final_plan, values='Cost', names='Role', title="Cost Distribution by Role"), use_container_width=True)
    st.plotly_chart(px.bar(cost_df, x="Sprint", y="Cost", title="Sprint-wise Budget Burn"), use_container_width=True)

with t2:
    for i in range(5):
        s_name = f"Sprint {i}"
        s_data = final_plan[final_plan['Sprint'] == s_name]
        with st.expander(f"{s_name} | Cost: ${s_data['Cost'].sum():,.2f}"):
            st.dataframe(s_data[['Task', 'Owner', 'Hours', 'Cost']], use_container_width=True, hide_index=True)
