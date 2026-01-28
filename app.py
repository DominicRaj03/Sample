import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Jarvis Sprint Planner", layout="wide")

# Sidebar Configuration
with st.sidebar:
    st.header("1. Sprint Configuration")
    start_date = st.date_input("Development Start Date", datetime(2026, 1, 27))
    num_sprints = st.number_input("Number of Sprints", min_value=1, value=2)
    
    st.subheader("Team Capacity")
    dev_count = st.number_input("Dev Team Size", value=3)
    qa_count = st.number_input("QA Team Size", value=2)
    capacity_per_res = st.number_input("Capacity per Resource (hrs)", value=64)
    leaves = st.number_input("Total Leave Hours (Team)", value=0)
    
    uploaded_file = st.file_uploader("Upload Work Items (Excel/CSV)", type=['xlsx', 'csv'])

# Capacity Limits
dev_cap_limit = (dev_count * capacity_per_res) - leaves
qa_cap_limit = (qa_count * capacity_per_res)

def balanced_allocation(df, n_sprints, d_limit, q_limit, effort_col, task_col):
    # FIX: Ensure column is string to prevent AttributeError
    df[task_col] = df[task_col].fillna("Unknown").astype(str)
    
    # Filter out Analysis phase
    df = df[~df[task_col].str.contains("Analysis|SRS|Mock-up", case=False, na=False)].copy()
    
    # Identify QA vs Dev tasks
    df['Type'] = df[task_col].apply(lambda x: 'QA' if any(word in x.upper() for word in ['QA', 'TESTING', 'UAT', 'BUG']) else 'Dev')
    df['Effort'] = pd.to_numeric(df[effort_col], errors='coerce').fillna(0)
    
    # Sort tasks by effort (Descending) for balanced distribution
    df = df.sort_values(by='Effort', ascending=False)
    
    # Initialize Sprint Loads
    sprint_data = {f"Sprint {i+1}": {"Dev": 0, "QA": 0} for i in range(n_sprints)}
    df['Assigned Sprint'] = "Unassigned"

    for idx, row in df.iterrows():
        task_type = row['Type']
        effort = row['Effort']
        limit = d_limit if task_type == 'Dev' else q_limit
        
        # Greedily assign to the sprint with the lowest current load
        best_sprint = None
        min_load = float('inf')
        
        for s_name in sprint_data:
            current_load = sprint_data[s_name][task_type]
            if current_load + effort <= limit:
                if current_load < min_load:
                    min_load = current_load
                    best_sprint = s_name
        
        if best_sprint:
            sprint_data[best_sprint][task_type] += effort
            df.at[idx, 'Assigned Sprint'] = best_sprint
        else:
            df.at[idx, 'Assigned Sprint'] = "Backlog (Over Capacity)"

    return df.sort_index()

if uploaded_file:
    df_raw = pd.read_excel(uploaded_file) if "xlsx" in uploaded_file.name else pd.read_csv(uploaded_file)
    df_raw.columns = df_raw.columns.str.strip()
    
    # Auto-detect columns from your specific file
    task_col = "Task Description" if "Task Description" in df_raw.columns else df_raw.columns[0]
    effort_col = "Hours" if "Hours" in df_raw.columns else df_raw.columns[-1]

    processed_df = balanced_allocation(df_raw, num_sprints, dev_cap_limit, qa_cap_limit, effort_col, task_col)

    # Dashboard Metrics
    st.header("Balanced Sprint Summary")
    cols = st.columns(num_sprints)
    for i in range(num_sprints):
        s_name = f"Sprint {i+1}"
        with cols[i]:
            s_data = processed_df[processed_df['Assigned Sprint'] == s_name]
            d_load = s_data[s_data['Type'] == 'Dev']['Effort'].sum()
            q_load = s_data[s_data['Type'] == 'QA']['Effort'].sum()
            st.metric(s_name, f"{int(d_load + q_load)} hrs")
            st.caption(f"Dev: {int(d_load)}/{dev_cap_limit}h | QA: {int(q_load)}/{qa_cap_limit}h")

    # Visual Weightage Chart
    
    st.subheader("Workload Weightage Comparison")
    chart_data = []
    for i in range(num_sprints):
        s = f"Sprint {i+1}"
        s_data = processed_df[processed_df['Assigned Sprint'] == s]
        chart_data.append({"Sprint": s, "Role": "Dev", "Hours": s_data[s_data['Type'] == 'Dev']['Effort'].sum()})
        chart_data.append({"Sprint": s, "Role": "QA", "Hours": s_data[s_data['Type'] == 'QA']['Effort'].sum()})
    
    fig = go.Figure()
    for role in ["Dev", "QA"]:
        subset = [d for d in chart_data if d['Role'] == role]
        fig.add_trace(go.Bar(x=[d['Sprint'] for d in subset], y=[d['Hours'] for d in subset], name=role))
    
    fig.update_layout(barmode='stack', title="Hours Allocated (Balanced Logic)")
    st.plotly_chart(fig, use_container_width=True)

    # Detailed Table
    st.subheader("Final Plan")
    st.data_editor(
        processed_df[[task_col, 'Type', 'Effort', 'Assigned Sprint']],
        use_container_width=True,
        hide_index=True
    )
    
    st.download_button("Export Balanced Plan", processed_df.to_csv(index=False).encode('utf-8'), "balanced_sprint_plan.csv")
