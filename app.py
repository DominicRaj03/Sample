import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta

st.set_page_config(page_title="Jarvis Sprint Planner", layout="wide")

# --- UI Header ---
st.title("🚀 Jarvis Sprint Planner & Burndown Generator")

# --- Sidebar Inputs ---
with st.sidebar:
    st.header("1. Sprint Parameters")
    start_date = st.date_input("Sprint Start Date", datetime(2026, 1, 27))
    sprint_days = st.number_input("Sprint Duration (Days)", value=8)
    num_sprints = st.number_input("Number of Sprints", min_value=1, value=2)
    
    st.header("2. Team Composition")
    dev_count = st.number_input("Dev Team Size", value=3)
    qa_count = st.number_input("QA Team Size", value=2)
    cap_per_res = st.number_input("Capacity per Resource (hrs)", value=64)
    
    st.header("3. Data Source")
    uploaded_file = st.file_uploader("Upload Task List (Excel/CSV)", type=['xlsx', 'csv'])

# --- Logic: Capacity Calculation ---
dev_limit = dev_count * cap_per_res
qa_limit = qa_count * cap_per_res
total_team_limit = dev_limit + qa_limit

def allocate_balanced(df, n_sprints, d_limit, q_limit):
    # Data Cleaning
    df.columns = df.columns.str.strip()
    task_col = "Task Description" if "Task Description" in df.columns else df.columns[1]
    effort_col = "Hours" if "Hours" in df.columns else df.columns[-1]
    
    df[task_col] = df[task_col].fillna("Unnamed Task").astype(str)
    df['Effort'] = pd.to_numeric(df[effort_col], errors='coerce').fillna(0)
    
    # Filter out Analysis
    df = df[~df[task_col].str.contains("Analysis|SRS", case=False, na=False)].copy()
    
    # Sort for balancing (Longest Processing Time)
    df = df.sort_values(by='Effort', ascending=False)
    
    sprint_loads = {f"Sprint {i+1}": 0 for i in range(n_sprints)}
    assignments = []

    for _, row in df.iterrows():
        # Assign to sprint with the least current load
        target_sprint = min(sprint_loads, key=sprint_loads.get)
        if sprint_loads[target_sprint] + row['Effort'] <= (total_team_limit / n_sprints) * 1.1: # Allow 10% buffer
            sprint_loads[target_sprint] += row['Effort']
            assignments.append(target_sprint)
        else:
            assignments.append("Backlog")
            
    df['Assigned Sprint'] = assignments
    return df, task_col

def create_burndown(total_hours, days):
    day_list = [f"Day {i}" for i in range(days + 1)]
    ideal_line = np.linspace(total_hours, 0, days + 1)
    
    # Planned line assumes linear consumption of capacity per day
    planned_line = [total_hours - (total_hours/days * i) for i in range(days + 1)]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=day_list, y=ideal_line, name="Ideal Burndown", line=dict(color='gray', dash='dash')))
    fig.add_trace(go.Scatter(x=day_list, y=planned_line, name="Planned Burndown", line=dict(color='royalblue', width=4)))
    
    fig.update_layout(title="Sprint Burndown Chart (Work Remaining)", yaxis_title="Hours", xaxis_title="Timeline")
    return fig

# --- App Execution ---
if uploaded_file:
    data = pd.read_excel(uploaded_file) if "xlsx" in uploaded_file.name else pd.read_csv(uploaded_file)
    processed_df, t_col = allocate_balanced(data, num_sprints, dev_limit, qa_limit)

    # Tabs for Organization
    tab1, tab2 = st.tabs(["📊 Visual Analytics", "📋 Sprint Schedule"])

    with tab1:
        st.subheader("Workload Weightage")
        summary = processed_df.groupby('Assigned Sprint')['Effort'].sum().reset_index()
        fig_bar = go.Figure(go.Bar(x=summary['Assigned Sprint'], y=summary['Effort'], marker_color='teal'))
        fig_bar.update_layout(title="Total Effort Distribution per Sprint", yaxis_title="Hours")
        st.plotly_chart(fig_bar, use_container_width=True)

        

        st.subheader("Sprint Burndown (Planned)")
        total_effort = processed_df[processed_df['Assigned Sprint'] == "Sprint 1"]['Effort'].sum()
        st.plotly_chart(create_burndown(total_effort, sprint_days), use_container_width=True)

    with tab2:
        st.subheader("Task Allocation Detail")
        st.data_editor(
            processed_df[[t_col, 'Effort', 'Assigned Sprint']],
            use_container_width=True,
            hide_index=True
        )
        
        st.download_button("Download Sprint Plan", processed_df.to_csv(index=False).encode('utf-8'), "jarvis_plan.csv")
else:
    st.info("Please upload your work items file to generate the plan and burndown chart.")
