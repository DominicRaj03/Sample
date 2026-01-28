import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Jarvis Sprint Planner", layout="wide")

# Sidebar Configuration
with st.sidebar:
    st.header("1. Configuration")
    start_date = st.date_input("Start Date", datetime(2026, 1, 27))
    dev_count = st.number_input("Dev Team Size", value=3)
    qa_count = st.number_input("QA Team Size", value=2)
    capacity_per_res = st.number_input("Capacity per Resource (hrs)", value=64)
    leaves = st.number_input("Total Team Leave Days", value=0)
    
    st.header("2. Data Upload")
    uploaded_file = st.file_uploader("Upload Excel/CSV", type=['xlsx', 'csv'])

# Capacity Calculation
dev_cap_limit = (dev_count * capacity_per_res) - (leaves * 8)
qa_cap_limit = (qa_count * capacity_per_res)

if uploaded_file:
    # Load Data
    df = pd.read_excel(uploaded_file) if "xlsx" in uploaded_file.name else pd.read_csv(uploaded_file)
    
    # 3. Column Mapping UI
    st.header("3. Column Mapping")
    col_cols = st.columns(2)
    with col_cols[0]:
        dev_col = st.selectbox("Select Dev Hours Column", options=df.columns, index=df.columns.get_loc("Hours") if "Hours" in df.columns else 0)
    with col_cols[1]:
        # If you don't have a QA column, we use the same or a default
        qa_col = st.selectbox("Select QA Hours Column (Optional)", options=["None"] + list(df.columns))

    # Data Preparation
    df['Dev_Target'] = pd.to_numeric(df[dev_col], errors='coerce').fillna(0)
    if qa_col != "None":
        df['QA_Target'] = pd.to_numeric(df[qa_col], errors='coerce').fillna(0)
    else:
        df['QA_Target'] = 0 # Default to 0 if no QA column exists

    # Initial Allocation Logic
    if 'Assigned Sprint' not in df.columns:
        sprints = []
        c_dev, c_qa = 0, 0
        for _, row in df.iterrows():
            if (c_dev + row['Dev_Target'] <= dev_cap_limit):
                sprints.append("Sprint 1")
                c_dev += row['Dev_Target']
            else:
                sprints.append("Sprint 2")
        df['Assigned Sprint'] = sprints

    # Interactive Editor
    st.header("4. Interactive Sprint Plan")
    edited_df = st.data_editor(
        df,
        column_config={
            "Assigned Sprint": st.column_config.SelectboxColumn("Assigned Sprint", options=["Sprint 1", "Sprint 2"])
        },
        use_container_width=True
    )

    # Visualization
    s1 = edited_df[edited_df['Assigned Sprint'] == 'Sprint 1']
    s2 = edited_df[edited_df['Assigned Sprint'] == 'Sprint 2']
    
    s1_d, s1_q = s1['Dev_Target'].sum(), s1['QA_Target'].sum()
    s2_d, s2_q = s2['Dev_Target'].sum(), s2['QA_Target'].sum()

    st.header("5. Utilization Metrics")
    fig = go.Figure(data=[
        go.Bar(name='Dev Utilization', x=['S1', 'S2'], y=[(s1_d/dev_cap_limit)*100, (s2_d/dev_cap_limit)*100]),
        go.Bar(name='QA Utilization', x=['S1', 'S2'], y=[(s1_q/qa_cap_limit)*100, (s2_q/qa_cap_limit)*100])
    ])
    fig.add_hline(y=100, line_dash="dash", line_color="red")
    st.plotly_chart(fig, use_container_width=True)

    st.download_button("Download Plan", edited_df.to_csv(index=False).encode('utf-8'), "sprint_plan.csv")
