import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="Jarvis Executive Intelligence", layout="wide")

# --- 1. Persistent Memory ---
if 'master_plan' not in st.session_state:
    st.session_state.master_plan = None
if 'sprint_meta' not in st.session_state:
    st.session_state.sprint_meta = {}
if 'quality_data' not in st.session_state:
    st.session_state.quality_data = pd.DataFrame()

# --- 2. Allocation & Balancing Logic (Existing) ---
def add_business_days(start_date, days):
    current_date = start_date
    added_days = 0
    while added_days < days - 1:
        current_date += timedelta(days=1)
        if current_date.weekday() < 5: added_days += 1
    return current_date

def run_allocation(dev_names, qa_names, lead_names, data, num_sprints, start_date, sprint_days):
    generated_plan = []
    sprint_details = {}
    for i in range(num_sprints):
        s_start = start_date + timedelta(days=i * sprint_days)
        while s_start.weekday() >= 5: s_start += timedelta(days=1)
        s_end = add_business_days(s_start, sprint_days)
        s_label = f"Sprint {i}"
        sprint_details[s_label] = f"{s_start.strftime('%Y-%m-%d')} to {s_end.strftime('%Y-%m-%d')}"

        def assign(sprint, s_dt, e_dt, names, task, role, total_hrs):
            if total_hrs <= 0: return
            split_hrs = float(total_hrs) / len(names)
            for name in names:
                generated_plan.append({"Sprint": sprint, "Start": s_dt, "Finish": e_dt, "Task": task, "Owner": name, "Role": role, "Hours": round(split_hrs, 1)})

        if i == 0:
            assign(s_label, s_start, s_end, lead_names, "Analysis Phase", "Lead", data["Analysis"])
            assign(s_label, s_start, s_end, qa_names, "TC preparation", "QA", data["TC_Prep"])
        elif 0 < i < (num_sprints - 1) or (num_sprints == 2 and i == 1):
            mid_count = max(1, num_sprints - 2) if num_sprints > 2 else 1
            assign(s_label, s_start, s_end, dev_names, "Development Phase", "Dev", data["Dev"]/mid_count)
            assign(s_label, s_start, s_end, lead_names, "Code Review", "Lead", data["Review"]/mid_count)
            assign(s_label, s_start, s_end, qa_names, "QA testing", "QA", data["QA_Test"]/mid_count)
            assign(s_label, s_start, s_end, qa_names, "Bug retest", "QA", data["Retest"]/mid_count)
            assign(s_label, s_start, s_end, dev_names, "Bug Fixes", "Dev", data["Fixes"]/mid_count)
        if i == (num_sprints - 1) and i > 0:
            assign(s_label, s_start, s_end, qa_names, "Integration Testing", "QA", data["Integ"])
            assign(s_label, s_start, s_end, qa_names, "Smoke test", "QA", data["Smoke"])
            assign(s_label, s_start, s_end, ["DevOps"], "Merge and Deploy", "Ops", data["Deploy"])
    return pd.DataFrame(generated_plan), sprint_details

def balance_resources(df, capacity):
    new_df = df.copy()
    for sprint in new_df['Sprint'].unique():
        for role in ['Dev', 'QA', 'Lead']:
            s_role_df = new_df[(new_df['Sprint'] == sprint) & (new_df['Role'] == role)]
            if s_role_df.empty: continue
            totals = s_role_df.groupby('Owner')['Hours'].sum()
            over = totals[totals > capacity]
            under = totals[totals < capacity]
            for o_name, o_hrs in over.items():
                excess = o_hrs - capacity
                for u_name, u_hrs in under.items():
                    if excess <= 0: break
                    available = capacity - u_hrs
                    transfer = min(excess, available)
                    idx = new_df[(new_df['Sprint'] == sprint) & (new_df['Owner'] == o_name)].index[0]
                    new_df.at[idx, 'Hours'] -= transfer
                    row_add = new_df.loc[idx].copy(); row_add['Owner'] = u_name; row_add['Hours'] = transfer
                    new_df = pd.concat([new_df, pd.DataFrame([row_add])], ignore_index=True)
                    excess -= transfer
    return new_df

# --- 3. Sidebar ---
with st.sidebar:
    st.header("👥 Team Setup")
    d_names = [st.text_input(f"Dev {j+1}", f"Dev_{j+1}", key=f"d{j}") for j in range(3)]
    qa_names = [st.text_input(f"QA {j+1}", f"QA_{j+1}", key=f"q{j}") for j in range(1)]
    lead_names = [st.text_input(f"Lead {j+1}", f"Lead_{j+1}", key=f"l{j}") for j in range(1)]
    st.divider()
    start_date = st.date_input("Start", datetime(2026, 2, 9))
    num_sprints = st.number_input("Sprints", 2, 12, 4)
    sprint_days = st.number_input("Days/Sprint", 1, 30, 8)
    daily_hrs = st.slider("Daily Max", 4, 12, 8)
    sync = st.button("🔄 Sync Systems", type="primary", use_container_width=True)

st.title("Jarvis Phase-Gate Intelligence")
tab1, tab2, tab3, tab4 = st.tabs(["🗺️ Roadmap Editor", "📊 Analytics", "🎯 Quality & Forecast", "📈 Trends"])
capacity = sprint_days * daily_hrs

with tab1:
    st.subheader("🛠️ Effort Baseline (Hours)")
    col_l, col_r = st.columns(2)
    with col_l:
        a_h = st.number_input("Analysis Phase", 0.0, 500.0, 25.0)
        d_h = st.number_input("Development Phase", 0.0, 2000.0, 350.0)
        f_h = st.number_input("Bug Fixes", 0.0, 500.0, 20.0)
        r_h = st.number_input("Code Review", 0.0, 200.0, 18.0)
        q_h = st.number_input("QA testing", 0.0, 1000.0, 85.0)
    with col_r:
        tp_h = st.number_input("TC preparation", 0.0, 500.0, 20.0)
        rt_h = st.number_input("Bug retest", 0.0, 500.0, 10.0)
        it_h = st.number_input("Integration Testing", 0.0, 500.0, 20.0)
        sm_h = st.number_input("Smoke test", 0.0, 500.0, 5.0)
        md_h = st.number_input("Merge and Deploy", 0.0, 500.0, 6.0)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🚀 GENERATE DATA", use_container_width=True) or sync:
            inputs = {"Analysis":a_h,"Dev":d_h,"Fixes":f_h,"Review":r_h,"QA_Test":q_h,"TC_Prep":tp_h,"Retest":rt_h,"Integ":it_h,"Smoke":sm_h,"Deploy":md_h}
            st.session_state.master_plan, st.session_state.sprint_meta = run_allocation(d_names, qa_names, lead_names, inputs, num_sprints, start_date, sprint_days)
            # Initialize with Leakage Tracking Columns
            st.session_state.quality_data = pd.DataFrame([{"Sprint": s, "Test Cases": 0, "QA Bugs": 0, "Escaped Bugs": 0} for s in st.session_state.sprint_meta.keys()])
            st.rerun()
    with c2:
        if st.session_state.master_plan is not None:
            if st.button("⚖️ BALANCE RESOURCES", use_container_width=True):
                st.session_state.master_plan = balance_resources(st.session_state.master_plan, capacity); st.rerun()

    if st.session_state.master_plan is not None:
        st.session_state.master_plan = st.data_editor(st.session_state.master_plan, use_container_width=True)

with tab3:
    if st.session_state.master_plan is not None:
        st.subheader("Quality & Leakage Analysis")
        st.session_state.quality_data = st.data_editor(st.session_state.quality_data, use_container_width=True)
        
        q_df = st.session_state.quality_data.copy()
        qa_hrs = st.session_state.master_plan[st.session_state.master_plan["Role"] == "QA"].groupby("Sprint")["Hours"].sum()
        
        # Calculations
        q_df["Total Bugs"] = q_df["QA Bugs"] + q_df["Escaped Bugs"]
        # Leakage % = (Escaped Bugs / Total Bugs) * 100
        q_df["Leakage (%)"] = (q_df["Escaped Bugs"] / q_df["Total Bugs"].replace(0,1) * 100).round(2)
        q_df["Productivity"] = (q_df["Test Cases"] / q_df["Sprint"].map(qa_hrs).replace(0,1)).round(2)

        # --- GRAPHS ---
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            # Defect Distribution
            fig_dist = px.bar(q_df, x="Sprint", y=["QA Bugs", "Escaped Bugs"], title="Bug Detection: QA vs. Leakage", barmode="stack", color_discrete_map={"QA Bugs": "royalblue", "Escaped Bugs": "#ef553b"})
            st.plotly_chart(fig_dist, use_container_width=True)

        with col_g2:
            # Leakage Trend
            fig_leak = px.line(q_df, x="Sprint", y="Leakage (%)", title="Defect Leakage Trend (Lower is Better)", markers=True)
            fig_leak.add_hrect(y0=0, y1=10, fillcolor="green", opacity=0.1, annotation_text="Ideal Zone")
            st.plotly_chart(fig_leak, use_container_width=True)
        
        st.divider()
        st.table(q_df.fillna("-"))
