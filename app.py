import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

st.set_page_config(page_title="Jarvis Resource Planner", layout="wide")

# --- Sidebar ---
with st.sidebar:
    st.header("⚙️ Configuration")
    start_date = st.date_input("Kick-off Date", datetime(2026, 1, 27))
    num_sprints = st.number_input("Total Sprints", min_value=3, value=3)
    dev_count = st.number_input("Dev Team Size", value=3)
    qa_count = st.number_input("QA Team Size", value=2)
    hrs_limit = st.number_input("Capacity per Person (hrs)", value=64)
    uploaded_file = st.file_uploader("Upload Work Items", type=['xlsx', 'csv'])

def allocate_staggered_logic(df, n_sprints, d_count, q_count, limit):
    df.columns = df.columns.str.strip()
    task_col = next((c for c in df.columns if "Task" in c), df.columns[1])
    hour_col = next((c for c in df.columns if "Hours" in c or "Effort" in c), df.columns[-1])
    
    df[hour_col] = pd.to_numeric(df[hour_col], errors='coerce').fillna(0)
    
    # 1. Separate Dev and QA pool
    # Identifying QA based on your specific file keywords
    qa_keywords = ['QA', 'TESTING', 'TC', 'BUG', 'UAT', 'TESTCASE']
    df['Is_QA'] = df[task_col].str.upper().apply(lambda x: any(k in x for k in qa_keywords))
    
    dev_df = df[~df['Is_QA'] & ~df[task_col].str.contains("Analysis|SRS|Mock-up", case=False, na=False)].copy()
    total_qa_hours = df[df['Is_QA']][hour_col].sum()

    # 2. Resource Clocks
    res_clocks = {f"Sprint {s}": {**{f"Dev {i+1}": 0 for i in range(d_count)}, 
                                  **{f"QA {j+1}": 0 for j in range(q_count)}} 
                  for s in range(1, n_sprints + 1)}
    plan = []

    # 3. Dev Allocation (Spread across Sprints 1 to N-1 mostly)
    for _, row in dev_df.iterrows():
        assigned = False
        for s in range(1, n_sprints): # Devs finish early to allow QA finalization
            s_name = f"Sprint {s}"
            devs = {k: v for k, v in res_clocks[s_name].items() if "Dev" in k}
            best_dev = min(devs, key=devs.get)
            
            if res_clocks[s_name][best_dev] + row[hour_col] <= limit:
                res_clocks[s_name][best_dev] += row[hour_col]
                plan.append({"Task": row[task_col], "Hours": row[hour_col], "Sprint": s_name, "Resource": best_dev, "Role": "Dev"})
                assigned = True
                break
        if not assigned: # Overflow to last sprint if needed
            s_name = f"Sprint {n_sprints}"
            devs = {k: v for k, v in res_clocks[s_name].items() if "Dev" in k}
            best_dev = min(devs, key=devs.get)
            res_clocks[s_name][best_dev] += row[hour_col]
            plan.append({"Task": row[task_col], "Hours": row[hour_col], "Sprint": s_name, "Resource": best_dev, "Role": "Dev"})

    # 4. QA Splitting Logic (Staggered & Weighted)
    # Sprint 1: 20% (Test Case Prep)
    s1_qa_total = total_qa_hours * 0.20
    # Sprint N: Heavy Weightage (Regression/Bugs/Integration)
    sn_qa_total = total_qa_hours * 0.50
    # Remaining: Sprints 2 to N-1 (Testing previous dev)
    mid_qa_total = total_qa_hours - s1_qa_total - sn_qa_total
    
    for s in range(1, n_sprints + 1):
        s_name = f"Sprint {s}"
        if s == 1:
            current_task, current_load = "QA Test Case Preparation (20%)", s1_qa_total
        elif s == n_sprints:
            current_task, current_load = "Final Regression, Integration & Bug Fixes", sn_qa_total
        else:
            current_task, current_load = f"Testing Sprint {s-1} Deliverables", mid_qa_total / (n_sprints - 2)

        # Split load among QA resources
        share = current_load / q_count
        for j in range(q_count):
            q_res = f"QA {j+1}"
            res_clocks[s_name][q_res] += share
            plan.append({"Task": current_task, "Hours": share, "Sprint": s_name, "Resource": q_res, "Role": "QA"})

    return pd.DataFrame(plan), res_clocks

# --- Main Logic Execution ---
if uploaded_file:
    df_raw = pd.read_excel(uploaded_file) if "xlsx" in uploaded_file.name else pd.read_csv(uploaded_file)
    final_plan, clocks = allocate_staggered_logic(df_raw, num_sprints, dev_count, qa_count, hrs_limit)

    # Bottleneck Alert
    st.header("⚡ Jarvis System Alerts")
    overloaded = []
    for s, res in clocks.items():
        for r, h in res.items():
            if h > hrs_limit:
                overloaded.append(f"{r} in {s} ({int(h)}h)")
    
    if overloaded:
        st.error(f"⚠️ **Capacity Warning:** {', '.join(overloaded)} exceed the {hrs_limit}h limit.")
    else:
        st.success("✅ All resources are within the defined capacity limits.")

    # Visuals
    st.header("📊 Resource Utilization (Staggered QA)")
    
    
    chart_data = [{"Sprint": s, "Resource": r, "Hours": h, "Role": "Dev" if "Dev" in r else "QA"} for s, res in clocks.items() for r, h in res.items()]
    c_df = pd.DataFrame(chart_data)
    fig = go.Figure()
    for role, color in zip(["Dev", "QA"], ["#00B4D8", "#F94144"]):
        r_df = c_df[c_df['Role'] == role]
        for res in r_df['Resource'].unique():
            mask = r_df['Resource'] == res
            fig.add_trace(go.Bar(x=r_df[mask]['Sprint'], y=r_df[mask]['Hours'], name=res, marker_color=color))
    
    fig.add_hline(y=hrs_limit, line_dash="dash", line_color="black", annotation_text="Max Capacity")
    fig.update_layout(barmode='group', title="Sprint Load Weightage (QA Staggered)")
    st.plotly_chart(fig, use_container_width=True)

    # Detailed View
    st.header("📋 Sprint Detailed Breakdown")
    s_select = st.selectbox("Select Sprint", sorted(final_plan['Sprint'].unique()))
    s_view = final_plan[final_plan['Sprint'] == s_select]
    
    for role in ["Dev", "QA"]:
        st.subheader(f"{role} Allocation")
        r_view = s_view[s_view['Role'] == role]
        cols = st.columns(max(len(r_view['Resource'].unique()), 1))
        for idx, res in enumerate(sorted(r_view['Resource'].unique())):
            with cols[idx]:
                tasks = r_view[r_view['Resource'] == res]
                total = tasks['Hours'].sum()
                st.metric(res, f"{int(total)} / {hrs_limit}h")
                # Simple Burndown Visualization
                days = np.arange(9) # 0 to 8
                burn = np.linspace(total, 0, 9)
                fig_burn = go.Figure(go.Scatter(x=days, y=burn, mode='lines+markers', name="Ideal Burn"))
                fig_burn.update_layout(height=200, margin=dict(l=0,r=0,t=0,b=0), xaxis_title="Days", yaxis_title="Rem. Hrs")
                st.plotly_chart(fig_burn, use_container_width=True)
                with st.expander("Tasks"):
                    for _, t in tasks.iterrows():
                        st.caption(f"• {t['Task']} ({int(t['Hours'])}h)")
