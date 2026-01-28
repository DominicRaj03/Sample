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
    # Filter out Analysis phase as requested
    df = df[~df[task_col].str.contains("Analysis|SRS|Mock-up", case=False, na=False)].copy()
    
    # Identify QA vs Dev tasks (Heuristic: keywords in task/description)
    df['Type'] = df[task_col].apply(lambda x: 'QA' if any(word in str(x).upper() for word in ['QA', 'TESTING', 'UAT', 'BUG']) else 'Dev')
    df['Effort'] = pd.to_numeric(df[effort_col], errors='coerce').fillna(0)
    
    # Sort tasks by effort (Descending) for better balancing
    df = df.sort_values(by='Effort', ascending=False)
    
    # Initialize Sprint Loads
    sprint_data = {f"Sprint {i+1}": {"Dev": 0, "QA": 0, "Tasks": []} for i in range(n_sprints)}
    assignments = []

    for idx, row in df.iterrows():
        task_type = row['Type']
        effort = row['Effort']
        
        # Find the sprint with the LOWEST current load for that specific resource type
        # that still has capacity
        best_sprint = None
        min_load = float('inf')
        
        for s_name, load in sprint_data.items():
            current_load = load[task_type]
            limit = d_limit if task_type == 'Dev' else q_limit
            
            if current_load + effort <= limit:
                if current_load < min_load:
                    min_load = current_load
                    best_sprint = s_name
        
        if best_sprint:
            sprint_data[best_sprint][task_type] += effort
            df.at[idx, 'Assigned Sprint'] = best_sprint
        else:
            df.at[idx, 'Assigned Sprint'] = "Unassigned (Over Capacity)"

    return df

if uploaded_file:
    # Load and clean
    df_raw = pd.read_excel(uploaded_file) if "xlsx" in uploaded_file.name else pd.read_csv(uploaded_file)
    df_raw.columns = df_raw.columns.str.strip()
    
    # Auto-detect columns from your MPESA file
    task_col = "Task Description" if "Task Description" in df_raw.columns else df_raw.columns[0]
    effort_col = "Hours" if "Hours" in df_raw.columns else df_raw.columns[-1]

    # Run Balanced Logic
    processed_df = balanced_allocation(df_raw, num_sprints, dev_cap_limit, qa_cap_limit, effort_col, task_col)

    # 1. Dashboard Metrics
    st.header("Balanced Sprint Summary")
    cols = st.columns(num_sprints)
    for i, sprint_name in enumerate(processed_df['Assigned Sprint'].unique()):
        if "Unassigned" in sprint_name: continue
        with cols[i % num_sprints]:
            s_data = processed_df[processed_df['Assigned Sprint'] == sprint_name]
            d_load = s_data[s_data['Type'] == 'Dev']['Effort'].sum()
            q_load = s_data[s_data['Type'] == 'QA']['Effort'].sum()
            st.metric(f"{sprint_name} Load", f"{int(d_load + q_load)} hrs")
            st.caption(f"Dev: {int(d_load)}/{dev_cap_limit}h | QA: {int(q_load)}/{qa_cap_limit}h")

    # 2. Visual Balance Chart
    st.subheader("Workload Weightage Comparison")
    chart_data = []
    for s in [f"Sprint {i+1}" for i in range(num_sprints)]:
        s_data = processed_df[processed_df['Assigned Sprint'] == s]
        chart_data.append({"Sprint": s, "Role": "Dev", "Hours": s_data[s_data['Type'] == 'Dev']['Effort'].sum()})
        chart_data.append({"Sprint": s, "Role": "QA", "Hours": s_data[s_data['Type'] == 'QA']['Effort'].sum()})
    
    chart_df = pd.DataFrame(chart_data)
    fig = go.Figure()
    for role in ["Dev", "QA"]:
        role_df = chart_df[chart_df['Role'] == role]
        fig.add_trace(go.Bar(x=role_df['Sprint'], y=role_df['Hours'], name=role))
    
    fig.update_layout(barmode='stack', title="Hours Allocated per Sprint (Balanced)")
    st.plotly_chart(fig, use_container_width=True)

    # 3. Interactive Schedule
    st.subheader("Detailed Work Schedule (Drag/Edit to adjust)")
    final_df = st.data_editor(
        processed_df[[task_col, 'Type', 'Effort', 'Assigned Sprint']],
        column_config={
            "Assigned Sprint": st.column_config.SelectboxColumn("Sprint", options=[f"Sprint {i+1}" for i in range(num_sprints)] + ["Backlog"]),
            "Effort": st.column_config.NumberColumn("Hours")
        },
        use_container_width=True,
        hide_index=True
    )
    
    st.download_button("Export Balanced Plan", final_df.to_csv(index=False).encode('utf-8'), "balanced_sprint_plan.csv")
