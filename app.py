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
    fig.update_layout(title=f"Burn-down: {resource_name}", height=250, margin=dict(l=20, r=20, t=40, b=20))
    return fig

def allocate_resources(df, n_sprints, d_count, q_count, limit):
    df.columns = df.columns.str.strip()
    task_col = next((c for c in df.columns if "Task" in c), df.columns[1])
    hour_col = next((c for c in df.columns if "Hours" in c or "Effort" in c), df.columns[-1])
    
    df[task_col] = df[task_col].fillna("Unknown").astype(str)
    df[hour_col] = pd.to_numeric(df[hour_col], errors='coerce').fillna(0)
    
    # Filter Analysis
    df = df[~df[task_col].str.contains("Analysis|SRS|Mock-up", case=False, na=False)].copy()
    
    # Explicit Type Identification
    df['Type'] = df[task_col].apply(lambda x: 'QA' if any(word in x.upper() for word in ['QA', 'TESTING', 'TC', 'UAT', 'BUG']) else 'Dev')
    
    dev_tasks = df[df['Type'] == 'Dev'].copy()
    qa_tasks = df[df['Type'] == 'QA'].copy()

    plan = []
    res_clocks = {f"Sprint {s}": {**{f"Dev {i+1}": 0 for i in range(d_count)}, **{f"QA {i+1}": 0 for i in range(q_count)}} for s in range(1, n_sprints + 1)}

    # 1. Dev Allocation (Balanced)
    for _, row in dev_tasks.iterrows():
        assigned = False
        for s in range(1, n_sprints + 1):
            s_name = f"Sprint {s}"
            devs = {k: v for k, v in res_clocks[s_name].items() if "Dev" in k}
            best_dev = min(devs, key=devs.get)
            if res_clocks[s_name][best_dev] + row[hour_col] <= limit:
                res_clocks[s_name][best_dev] += row[hour_col]
                plan.append({"Task": row[task_col], "Hours": row[hour_col], "Sprint": s_name, "Resource": best_dev, "Role": "Dev"})
                assigned = True
                break
        if not assigned: plan.append({"Task": row[task_col], "Hours": row[hour_col], "Sprint": "Backlog", "Resource": "None", "Role": "Dev"})

    # 2. QA Staggered Allocation
    for _, row in qa_tasks.iterrows():
        # TC Preparation / Creation goes to current sprint, Testing/Execution to next
        is_tc = any(word in row[task_col].upper() for word in ['CASE', 'PREPARATION', 'CREATION'])
        
        assigned = False
        for s in range(1, n_sprints + 1):
            # If TC: Try current sprint. If Testing: Try s+1
            target_s = s if is_tc else s + 1
            s_name = f"Sprint {target_s}"
            
            if s_name not in res_clocks: continue
            
            qas = {k: v for k, v in res_clocks[s_name].items() if "QA" in k}
            best_qa = min(qas, key=qas.get)
            
            # Apply 80% Rule for TC in Sprint 1
            current_limit = limit * 0.8 if (is_tc and target_s == 1) else limit
            
            if res_clocks[s_name][best_qa] + row[hour_col] <= current_limit:
                res_clocks[s_name][best_qa] += row[hour_col]
                plan.append({"Task": row[task_col], "Hours": row[hour_col], "Sprint": s_name, "Resource": best_qa, "Role": "QA"})
                assigned = True
                break
        if not assigned: plan.append({"Task": row[task_col], "Hours": row[hour_col], "Sprint": "Backlog", "Resource": "None", "Role": "QA"})
                
    return pd.DataFrame(plan), res_clocks

# --- Main App ---
if uploaded_file:
    df_raw = pd.read_excel(uploaded_file) if "xlsx" in uploaded_file.name else pd.read_csv(uploaded_file)
    final_plan, clocks = allocate_resources(df_raw, num_sprints, dev_count, qa_count, hrs_per_person)

    # 1. Dashboard Metrics
    st.header("📈 Sprint Utilization Overview")
    metric_cols = st.columns(num_sprints)
    for i in range(num_sprints):
        s_name = f"Sprint {i+1}"
        s_data = final_plan[final_plan['Sprint'] == s_name]
        d_hrs = s_data[s_data['Role'] == 'Dev']['Hours'].sum()
        q_hrs = s_data[s_data['Role'] == 'QA']['Hours'].sum()
        with metric_cols[i]:
            st.metric(s_name, f"{int(d_hrs + q_hrs)} Total Hrs")
            st.caption(f"🛠️ Dev: {int(d_hrs)}h | 🧪 QA: {int(q_hrs)}h")

    # 2. Visualization
    chart_data = [{"Sprint": s, "Resource": r, "Hours": h, "Role": "Dev" if "Dev" in r else "QA"} for s, res in clocks.items() for r, h in res.items()]
    c_df = pd.DataFrame(chart_data)
    fig_main = go.Figure()
    for role, color in zip(["Dev", "QA"], ["#636EFA", "#EF553B"]):
        role_df = c_df[c_df['Role'] == role]
        for res in role_df['Resource'].unique():
            mask = role_df['Resource'] == res
            fig_main.add_trace(go.Bar(x=role_df[mask]['Sprint'], y=role_df[mask]['Hours'], name=res, marker_color=color))
    
    fig_main.add_hline(y=hrs_per_person, line_dash="dash", line_color="black", annotation_text="Cap")
    fig_main.update_layout(barmode='group', title="Effort Distribution by Resource (Dev vs QA)")
    st.plotly_chart(fig_main, use_container_width=True)

    # 3. Individual Resource Breakdown
    st.header("📋 Resource Tasks & Burndowns")
    selected_sprint = st.selectbox("Select Sprint", options=sorted(final_plan['Sprint'].unique()))
    s_view = final_plan[final_plan['Sprint'] == selected_sprint]
    
    for role in ["Dev", "QA"]:
        st.subheader(f"{role} Team Breakdown")
        role_view = s_view[s_view['Role'] == role]
        cols = st.columns(max(len(role_view['Resource'].unique()), 1))
        for idx, res in enumerate(sorted(role_view['Resource'].unique())):
            with cols[idx]:
                res_tasks = role_view[role_view['Resource'] == res]
                total_h = res_tasks['Hours'].sum()
                with st.container(border=True):
                    st.markdown(f"**👤 {res}**")
                    st.markdown(f"Usage: `{int(total_h)}/{int(hrs_per_person)}h`")
                    st.plotly_chart(get_resource_burndown(total_h, int(sprint_days), res), use_container_width=True)
                    with st.expander("Tasks"):
                        for _, t in res_tasks.iterrows():
                            st.write(f"- {t['Task']} ({int(t['Hours'])}h)")

    st.download_button("Export Final Sprint Plan", final_plan.to_csv(index=False).encode('utf-8'), "jarvis_qa_dev_plan.csv")
else:
    st.info("Jarvis: Please upload the data file to generate the balanced QA/Dev sprint plan.")
