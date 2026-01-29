import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Jarvis Scenario Architect", layout="wide")

# --- Logic Core ---
def calculate_plan(dev_count, qa_count, splits, max_cap):
    dev_names = [f"Dev {i+1}" for i in range(dev_count)]
    qa_names = [f"QA {i+1}" for i in range(qa_count)]
    
    plan = []
    resource_load = {f"Sprint {i}": {name: 0 for name in dev_names + qa_names + ["Lead", "Designer", "DevOps"]} for i in range(5)}

    def assign(sprint, names, task, hours):
        owner = min(names, key=lambda x: resource_load[sprint][x])
        resource_load[sprint][owner] += hours
        return {"Sprint": sprint, "Task": task, "Owner": owner, "Hours": hours}

    # Simplified Phase Logic for Comparison
    plan.append(assign("Sprint 0", ["Lead"], "Analysis", splits['Analysis']))
    plan.append(assign("Sprint 0", ["Designer"], "Design", splits['Doc']))

    dev_hrs = splits['TotalDev'] / 2
    for s in ["Sprint 1", "Sprint 2"]:
        for _ in range(len(dev_names)):
            plan.append(assign(s, dev_names, "Development", dev_hrs / len(dev_names)))
    
    plan.append(assign("Sprint 1", qa_names, "Test Prep", splits['QA'] * 0.2))
    plan.append(assign("Sprint 2", qa_names, "QA P1", splits['QA'] * 0.4))
    plan.append(assign("Sprint 3", qa_names, "QA P2", splits['QA'] * 0.4))
    plan.append(assign("Sprint 3", dev_names, "Fixing", splits['Fixes']))
    plan.append(assign("Sprint 4", ["DevOps"], "Deploy", splits['Deploy']))
    
    df = pd.DataFrame(plan)
    df['Overload'] = df.groupby(['Sprint', 'Owner'])['Hours'].transform('sum') > max_cap
    return df

# --- Sidebar ---
with st.sidebar:
    st.header("⚙️ Base Parameters")
    sprint_days = st.number_input("Sprint Days", 1, 30, 12)
    daily_hrs = st.slider("Daily Hours", 4, 12, 8)
    max_cap = sprint_days * daily_hrs
    
    st.divider()
    splits = {
        'TotalDev': st.number_input("Total Dev Hrs", 0, 2000, 160),
        'Analysis': 40, 'QA': 100, 'Fixes': 40, 'Retest': 20, 'Doc': 30, 'Deploy': 16
    }

# --- Main Interface ---
st.title("⚖️ Scenario Comparison")

col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Scenario A (Current)")
    dev_a = st.number_input("Devs (A)", 1, 10, 2)
    qa_a = st.number_input("QAs (A)", 1, 10, 1)
    plan_a = calculate_plan(dev_a, qa_a, splits, max_cap)
    
    load_a = plan_a.groupby(['Sprint', 'Owner'])['Hours'].sum().reset_index()
    fig_a = px.bar(load_a, x="Sprint", y="Hours", color="Owner", barmode="group", title="Scenario A Load")
    fig_a.add_hline(y=max_cap, line_dash="dash", line_color="red")
    st.plotly_chart(fig_a, use_container_width=True)
    
    overloads_a = plan_a[plan_a['Overload'] == True]['Sprint'].nunique()
    st.metric("Sprints with Overload", overloads_a, delta=None)

with col_b:
    st.subheader("Scenario B (Proposed)")
    dev_b = st.number_input("Devs (B)", 1, 10, 3)
    qa_b = st.number_input("QAs (B)", 1, 10, 2)
    plan_b = calculate_plan(dev_b, qa_b, splits, max_cap)
    
    load_b = plan_b.groupby(['Sprint', 'Owner'])['Hours'].sum().reset_index()
    fig_b = px.bar(load_b, x="Sprint", y="Hours", color="Owner", barmode="group", title="Scenario B Load")
    fig_b.add_hline(y=max_cap, line_dash="dash", line_color="red")
    st.plotly_chart(fig_b, use_container_width=True)
    
    overloads_b = plan_b[plan_b['Overload'] == True]['Sprint'].nunique()
    st.metric("Sprints with Overload", overloads_b, delta=overloads_b - overloads_a, delta_color="inverse")

st.divider()
st.info(f"Jarvis: Scenario B {'reduces' if overloads_b < overloads_a else 'increases or maintains'} the overload risk compared to Scenario A.")
