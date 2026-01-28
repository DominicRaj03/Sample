import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

st.set_page_config(page_title="Jarvis Resource Planner", layout="wide")

# --- Sidebar Inputs ---
with st.sidebar:
    st.header("⚙️ Configuration")
    start_date = st.date_input("Kick-off Date", datetime(2026, 1, 27))
    num_sprints = st.number_input("Number of Sprints", min_value=2, value=3)
    
    st.subheader("Team Size")
    dev_count = st.number_input("Dev Team (Resources)", value=3)
    qa_count = st.number_input("QA Team (Resources)", value=2)
    
    st.subheader("Capacity")
    hrs_per_person = st.number_input("Hrs per Person (e.g., 8 days)", value=64)
    sprint_days = st.number_input("Sprint Work Days", value=8)
    
    uploaded_file = st.file_uploader("Upload MPESA Enhancement Excel", type=['xlsx', 'csv'])

# --- Logic: Allocation & Burndown ---
def get_resource_burndown(total_hours, days, resource_name):
    day_list = [f"Day {i}" for i in range(days + 1)]
    ideal_line = np.linspace(total_hours, 0, days + 1)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=day_list, y=ideal_line, name="Ideal Path", line=dict(color='gray', dash='dash')))
    fig.add_trace(go.Scatter(x=day_list, y=ideal_line, name="Planned Burn", line=dict(color='green', width=3)))
    
    fig.update_layout(
        title=f"Burn-down: {resource_name}",
        height=300,
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis_title="Days",
        yaxis_title="Hours Remaining"
    )
    return fig

def allocate_resources(df, n_sprints, d_count, q_count, limit):
    # CLEANING: Strip whitespace from column names to fix KeyError
    df.columns = df.columns.str.strip()
    
    # DYNAMIC COLUMN DETECTION
    task_col = next((c for c in df.columns if "Task" in c), df.columns[1])
    hour_col = next((c for c in df.columns if "Hours" in c or "Effort" in c), df.columns[-1])
    
    # Ensure Task Description is a string
    df[task_col] = df[task_col].fillna("Unknown").astype(str)
    df[hour_col] = pd.to_numeric(df[hour_col], errors='coerce').fillna(0)
    
    # Filter out Analysis phase
    df = df[~df[task_col].str.contains("Analysis|SRS", case=False, na=False)].copy()
    
    dev_tasks = df[~df[task_col].str.contains("QA|Testing|Test Case", case=False)].copy()
    qa_tasks = df[df[task_col].str.contains("QA|Testing|Test Case", case=False)].copy()

    plan = []
    res_clocks = {f"Sprint {s}": {**{f"Dev {i+1}": 0 for i in range(d_count)}, **{f"QA {i+1}": 0 for i in range(q_count)}} for s in range(1, n_sprints + 1)}

    # Dev Allocation (Balanced Weightage)
    for _, row in dev_tasks.iterrows():
        assigned = False
        for s in range(1, n_sprints + 1):
            s_name = f"Sprint {s}"
            devs = {k: v for k, v in res_clocks[s_name].items() if "Dev" in k}
            best_dev = min(devs, key=devs.get)
            if res_clocks[s_name][best_dev] + row[hour_col] <= limit:
                res_clocks[s_name][best_dev] += row[hour_col]
                plan.append({"Task": row[task_col], "Hours": row[hour_col], "Sprint": s_name, "Resource": best_dev})
                assigned = True
                break
        if not assigned: plan.append({"Task": row[task_col], "Hours": row[hour_col], "Sprint": "Backlog", "Resource": "None"})

    # Staggered QA Allocation
    for _, row in qa_tasks.iterrows():
        is_tc = "Case" in row[task_col] or "Preparation" in row[task_col]
        for s in range(1, n_sprints + 1):
            s_num = s if is_tc else s + 1
            s_name = f"Sprint {s_num}"
            if s_name not in res_clocks: continue
            qas = {k: v for k, v in res_clocks[s_name].items() if "QA" in k}
            best_qa = min(qas, key=qas.get)
            
            # Sprint 1 QA Rule (80% capacity for TC writing)
            current_limit = limit * 0.8 if (is_tc and s == 1) else limit
            
            if res_clocks[s_name][best_qa] + row[hour_col] <= current_limit:
                res_clocks[s_name][best_qa] += row[hour_col]
                plan.append({"Task": row[task_col], "Hours": row[hour_col], "Sprint": s_name, "Resource": best_qa})
                break
                
    return pd.DataFrame(plan), res_clocks

# --- Main App ---
if uploaded_file:
    df_raw = pd.read_excel(uploaded_file) if "xlsx" in uploaded_file.name else pd.read_csv(uploaded_file)
    final_plan, clocks = allocate_resources(df_raw, num_sprints, dev_count, qa_count, hrs_per_person)

    st.header("📊 Team Utilization")
    chart_data = [{"Sprint": s, "Resource": r, "Hours": h} for s, res in clocks.items() for r, h in res.items()]
    c_df = pd.DataFrame(chart_data)
    fig_main = go.Figure()
    for res in c_df['Resource'].unique():
        mask = c_df['Resource'] == res
        fig_main.add_trace(go.Bar(x=c_df[mask]['Sprint'], y=c_df[mask]['Hours'], name=res))
    fig_main.add_hline(y=hrs_per_person, line_dash="dash", line_color="red", annotation_text="Limit")
    st.plotly_chart(fig_main, use_container_width=True)

    

    st.header("📋 Resource Detail & Personal Burndowns")
    selected_sprint = st.selectbox("Select Sprint", options=sorted(final_plan['Sprint'].unique()))
    s_view = final_plan[final_plan['Sprint'] == selected_sprint]
    
    cols = st.columns(2)
    for idx, res in enumerate(sorted(s_view['Resource'].unique())):
        with cols[idx % 2]:
            res_tasks = s_view[s_view['Resource'] == res]
            total_h = res_tasks['Hours'].sum()
            with st.container(border=True):
                st.subheader(f"👤 {res}")
                st.write(f"**Total Assigned:** {total_h} / {hrs_per_person} hrs")
                
                # Individual Burndown
                st.plotly_chart(get_resource_burndown(total_h, int(sprint_days), res), use_container_width=True)
                
                with st.expander("View Task List"):
                    for _, t in res_tasks.iterrows():
                        st.write(f"- {t['Task']} ({t['Hours']}h)")

    st.download_button("Export Jarvis Plan", final_plan.to_csv(index=False).encode('utf-8'), "jarvis_resource_plan.csv")
else:
    st.info("Jarvis: Awaiting data upload. Ensure your file has 'Task Description' and 'Hours' columns.")
