import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Jarvis Sprint Planner", layout="wide")

# Sidebar Configuration
with st.sidebar:
    st.header("Configuration")
    start_date = st.date_input("Start Date", datetime(2026, 1, 27))
    num_sprints = st.number_input("How Many Sprints", min_value=1, value=2)
    dev_count = st.number_input("Dev Team", value=3)
    qa_count = st.number_input("QA Team", value=2)
    capacity_per_res = st.number_input("Capacity per Resource (hrs)", value=64)
    leaves = st.number_input("Total Team Leave Days", value=0)
    
    uploaded_file = st.file_uploader("Upload Excel/CSV Work Items", type=['xlsx', 'csv'])

# Capacity Calculation
dev_cap_limit = (dev_count * capacity_per_res) - (leaves * 8)
qa_cap_limit = (qa_count * capacity_per_res)

def initial_allocation(df, dev_limit, qa_limit):
    sprint_assignments = []
    current_dev, current_qa = 0, 0
    
    for _, row in df.iterrows():
        d_hrs = row.get('Dev Hours', 0)
        q_hrs = row.get('QA Hours', 0)
        
        if (current_dev + d_hrs <= dev_limit) and (current_qa + q_hrs <= qa_limit):
            sprint_assignments.append("Sprint 1")
            current_dev += d_hrs
            current_qa += q_hrs
        else:
            sprint_assignments.append("Sprint 2")
            
    df['Assigned Sprint'] = sprint_assignments
    return df

if uploaded_file:
    # Load Data
    raw_df = pd.read_excel(uploaded_file) if "xlsx" in uploaded_file.name else pd.read_csv(uploaded_file)
    
    # Run Initial Logic
    if 'Assigned Sprint' not in raw_df.columns:
        allocated_df = initial_allocation(raw_df, dev_cap_limit, qa_cap_limit)
    else:
        allocated_df = raw_df

    st.header("Interactive Sprint Editor")
    st.info("Jarvis: You can manually override the 'Assigned Sprint' column directly in the table below.")
    
    # Manual Override Table
    edited_df = st.data_editor(
        allocated_df,
        column_config={
            "Assigned Sprint": st.column_config.SelectboxColumn(
                "Assigned Sprint",
                options=["Sprint 1", "Sprint 2"],
                required=True,
            )
        },
        use_container_width=True,
        num_rows="dynamic"
    )

    # Recalculate Metrics based on Edits
    s1_data = edited_df[edited_df['Assigned Sprint'] == 'Sprint 1']
    s2_data = edited_df[edited_df['Assigned Sprint'] == 'Sprint 2']
    
    s1_dev, s1_qa = s1_data['Dev Hours'].sum(), s1_data['QA Hours'].sum()
    s2_dev, s2_qa = s2_data['Dev Hours'].sum(), s2_data['QA Hours'].sum()

    # Dashboard Metrics
    st.header("Updated Utilization Summary")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("S1 Dev Load", f"{s1_dev} / {dev_cap_limit}h", delta=f"{s1_dev - dev_cap_limit}" if s1_dev > dev_cap_limit else None, delta_color="inverse")
    c2.metric("S1 QA Load", f"{s1_qa} / {qa_cap_limit}h", delta=f"{s1_qa - qa_cap_limit}" if s1_qa > qa_cap_limit else None, delta_color="inverse")
    c3.metric("S2 Dev Load", f"{s2_dev} / {dev_cap_limit}h", delta=f"{s2_dev - dev_cap_limit}" if s2_dev > dev_cap_limit else None, delta_color="inverse")
    c4.metric("S2 QA Load", f"{s2_qa} / {qa_cap_limit}h", delta=f"{s2_qa - qa_cap_limit}" if s2_qa > qa_cap_limit else None, delta_color="inverse")

    # Chart
    fig = go.Figure(data=[
        go.Bar(name='Dev Utilization %', x=['Sprint 1', 'Sprint 2'], y=[(s1_dev/dev_cap_limit)*100, (s2_dev/dev_cap_limit)*100], marker_color='#1f77b4'),
        go.Bar(name='QA Utilization %', x=['Sprint 1', 'Sprint 2'], y=[(s1_qa/qa_cap_limit)*100, (s2_qa/qa_limit)*100], marker_color='#ff7f0e')
    ])
    fig.update_layout(barmode='group', yaxis_title="Percentage (%)", yaxis=dict(range=[0, 120]))
    fig.add_hline(y=100, line_dash="dash", line_color="red", annotation_text="Limit")
    st.plotly_chart(fig, use_container_width=True)
    
    st.download_button("Export Final Plan", edited_df.to_csv(index=False).encode('utf-8'), "final_sprint_plan.csv")