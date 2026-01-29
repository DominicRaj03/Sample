import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="Jarvis Executive Intelligence", layout="wide")

# --- 1. Persistent Memory & State Management ---
if 'master_plan' not in st.session_state:
    st.session_state.master_plan = None
if 'quality_data' not in st.session_state:
    st.session_state.quality_data = pd.DataFrame()

# --- 2. Calculation Engines ---
def add_business_days(start_date, days):
    current_date = start_date
    added_days = 0
    while added_days < days - 1:
        current_date += timedelta(days=1)
        if current_date.weekday() < 5: added_days += 1
    return current_date

def run_allocation(dev_names, qa_names, lead_names, data, num_sprints, start_date, sprint_days):
    generated_plan = []
    for i in range(num_sprints):
        s_start = start_date + timedelta(days=i * sprint_days)
        while s_start.weekday() >= 5: s_start += timedelta(days=1)
        s_end = add_business_days(s_start, sprint_days)
        s_label = f"Sprint {i}"

        def assign(task, role, names, total_hrs):
            if total_hrs <= 0: return
            split = float(total_hrs) / len(names)
            for name in names:
                generated_plan.append({"Sprint": s_label, "Start": s_start, "Finish": s_end, "Task": task, "Owner": name, "Role": role, "Hours": round(split, 1)})

        if i == 0:
            assign("Analysis Phase", "Lead", lead_names, data["Analysis"])
            assign("TC preparation", "QA", qa_names, data["TC_Prep"])
        elif 0 < i < (num_sprints - 1):
            mid = max(1, num_sprints - 2)
            assign("Development Phase", "Dev", dev_names, data["Dev"]/mid)
            assign("Code Review", "Lead", lead_names, data["Review"]/mid)
            assign("QA testing", "QA", qa_names, data["QA_Test"]/mid)
            assign("Bug retest", "QA", qa_names, data["Retest"]/mid)
            assign("Bug Fixes", "Dev", dev_names, data["Fixes"]/mid)
        elif i == (num_sprints - 1):
            assign("Integration Testing", "QA", qa_names, data["Integ"])
            assign("Smoke test", "QA", qa_names, data["Smoke"])
            assign("Merge and Deploy", "Ops", ["DevOps"], data["Deploy"])
            
    return pd.DataFrame(generated_plan)

def balance_resources(df, capacity):
    new_df = df.copy()
    for sprint in new_df['Sprint'].unique():
        for role in ['Dev', 'QA', 'Lead']:
            subset = new_df[(new_df['Sprint'] == sprint) & (new_df['Role'] == role)]
            if subset.empty: continue
            totals = subset.groupby('Owner')['Hours'].sum()
            over = totals[totals > capacity]
            under = totals[totals < capacity]
            for o_name, o_hrs in over.items():
                excess = o_hrs - capacity
                for u_name, u_hrs in under.items():
                    if excess <= 0: break
                    transfer = min(excess, capacity - u_hrs)
                    idx = new_df[(new_df['Sprint'] == sprint) & (new_df['Owner'] == o_name)].index[0]
                    new_df.at[idx, 'Hours'] -= transfer
                    row_add = new_df.loc[idx].copy()
                    row_add['Owner'], row_add['Hours'] = u_name, transfer
                    new_df = pd.concat([new_df, pd.DataFrame([row_add])], ignore_index=True)
                    excess -= transfer
    return new_df

# --- 3. Sidebar UI ---
with st.sidebar:
    st.header("👥 Team")
    devs = [st.text_input(f"Dev {j+1}", f"Dev_{j+1}", key=f"d{j}") for j in range(3)]
    qas = [st.text_input(f"QA {j+1}", f"QA_{j+1}", key=f"q{j}") for j in range(1)]
    leads = [st.text_input(f"Lead {j+1}", f"Lead_{j+1}", key=f"l{j}") for j in range(1)]
    st.divider()
    start_dt = st.date_input("Project Start", datetime(2026, 2, 9))
    sprint_num = st.number_input("Total Sprints", 2, 10, 4)
    sprint_len = st.number_input("Days/Sprint", 1, 20, 8)
    max_hrs = st.slider("Daily Max Hours", 4, 12, 8)
    sync = st.button("🔄 Sync & Fix Displays", type="primary", use_container_width=True)

# --- 4. Main Interface ---
st.title("Jarvis Phase-Gate Intelligence")
tab1, tab2, tab3, tab4 = st.tabs(["🗺️ Roadmap", "📊 Analytics", "🎯 Quality", "📈 Trends"])
capacity = sprint_len * max_hrs

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        vals = {
            "Analysis": st.number_input("Analysis", 0.0, 500.0, 25.0),
            "Dev": st.number_input("Development", 0.0, 1000.0, 350.0),
            "Fixes": st.number_input("Bug Fixes", 0.0, 500.0, 20.0),
            "Review": st.number_input("Code Review", 0.0, 200.0, 18.0),
            "QA_Test": st.number_input("QA testing", 0.0, 500.0, 85.0)
        }
    with c2:
        vals.update({
            "TC_Prep": st.number_input("TC preparation", 0.0, 500.0, 20.0),
            "Retest": st.number_input("Bug retest", 0.0, 200.0, 10.0),
            "Integ": st.number_input("Integration", 0.0, 200.0, 20.0),
            "Smoke": st.number_input("Smoke test", 0.0, 100.0, 5.0),
            "Deploy": st.number_input("Merge & Deploy", 0.0, 100.0, 6.0)
        })

    if st.button("🚀 GENERATE & FIX VIEW", use_container_width=True) or sync:
        st.session_state.master_plan = run_allocation(devs, qas, leads, vals, sprint_num, start_dt, sprint_len)
        st.session_state.quality_data = pd.DataFrame([{"Sprint": f"Sprint {i}", "TC": 20, "QA Bugs": 2, "Leakage": 1} for i in range(sprint_num)])
        st.rerun()

    if st.session_state.master_plan is not None:
        if st.button("⚖️ BALANCE RESOURCES"):
            st.session_state.master_plan = balance_resources(st.session_state.master_plan, capacity); st.rerun()
        st.data_editor(st.session_state.master_plan, use_container_width=True)

with tab2: # FIXED ANALYTICS
    if st.session_state.master_plan is not None:
        st.subheader("Process Gantt & Workload")
        # Gantt Chart
        fig_gantt = px.timeline(st.session_state.master_plan, x_start="Start", x_end="Finish", y="Task", color="Role", title="Timeline Detail")
        fig_gantt.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_gantt, use_container_width=True)
        # Heatmap
        usage = st.session_state.master_plan.pivot_table(index="Owner", columns="Sprint", values="Hours", aggfunc="sum").fillna(0)
        st.write("**Resource Workload Heatmap (Hours)**")
        st.dataframe(usage.style.background_gradient(cmap="Reds", axis=None), use_container_width=True)

with tab4: # FIXED TRENDS
    if not st.session_state.quality_data.empty:
        st.subheader("Defect Leakage & Maturity Trends")
        q = st.session_state.quality_data
        q["Leak Rate (%)"] = (q["Leakage"] / (q["QA Bugs"] + q["Leakage"]).replace(0,1) * 100).round(2)
        
        c_a, c_b = st.columns(2)
        with c_a:
            fig_leak = px.area(q, x="Sprint", y="Leak Rate (%)", title="Defect Leakage Trend", markers=True)
            st.plotly_chart(fig_leak, use_container_width=True)
        with c_b:
            fig_bar = px.bar(q, x="Sprint", y=["QA Bugs", "Leakage"], title="Bug Detection Breakdown", barmode="group")
            st.plotly_chart(fig_bar, use_container_width=True)
