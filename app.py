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

# --- 2. Logic Engines ---
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
                generated_plan.append({
                    "Sprint": sprint, "Start": s_dt, "Finish": e_dt, 
                    "Task": task, "Owner": name, "Role": role, "Hours": round(split_hrs, 1)
                })

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
                    
                    # Deduct from overloaded
                    idx = new_df[(new_df['Sprint'] == sprint) & (new_df['Owner'] == o_name)].index[0]
                    new_df.at[idx, 'Hours'] -= transfer
                    
                    # Add to underloaded
                    row_add = new_df.loc[idx].copy()
                    row_add['Owner'] = u_name
                    row_add['Hours'] = transfer
                    new_df = pd.concat([new_df, pd.DataFrame([row_add])], ignore_index=True)
                    excess -= transfer
    return new_df

# --- 3. Sidebar ---
with st.sidebar:
    st.header("👥 Team")
    d_count = st.number_input("Devs", 1, 10, 3); q_count = st.number_input("QA", 1, 10, 1); l_count = st.number_input("Leads", 1, 10, 1)
    dev_names = [st.text_input(f"D{j+1}", f"Dev_{j+1}", key=f"d{j}") for j in range(d_count)]
    qa_names = [st.text_input(f"Q{j+1}", f"QA_{j+1}", key=f"q{j}") for j in range(q_count)]
    lead_names = [st.text_input(f"L{j+1}", f"Lead_{j+1}", key=f"l{j}") for j in range(l_count)]
    st.divider(); st.header("📅 Settings")
    start_date = st.date_input("Start", datetime(2026, 2, 9))
    num_sprints = st.number_input("Sprints", 2, 12, 3)
    sprint_days = st.number_input("Days/Sprint", 1, 30, 8)
    daily_hrs = st.slider("Daily Max", 4, 12, 8)
    sync = st.button("🔄 Sync Systems", type="primary", use_container_width=True)

# --- 4. Main UI ---
st.title("Jarvis Phase-Gate Intelligence")
tab1, tab2, tab3, tab4 = st.tabs(["🗺️ Roadmap Editor", "📊 Analytics", "🎯 Quality & Forecast", "📈 Trends"])
capacity = sprint_days * daily_hrs

with tab1:
    st.subheader("🛠️ Effort Baseline (Hours)")
    c1, c2 = st.columns(2)
    with c1:
        a_h = st.number_input("Analysis Phase", 0.0, 500.0, 25.0)
        d_h = st.number_input("Development Phase", 0.0, 2000.0, 350.0)
        f_h = st.number_input("Bug Fixes", 0.0, 500.0, 20.0)
        r_h = st.number_input("Code Review", 0.0, 200.0, 18.0)
        q_h = st.number_input("QA testing", 0.0, 1000.0, 85.0)
    with c2:
        tp_h = st.number_input("TC preparation", 0.0, 500.0, 20.0)
        rt_h = st.number_input("Bug retest", 0.0, 500.0, 10.0)
        it_h = st.number_input("Integration Testing", 0.0, 500.0, 20.0)
        sm_h = st.number_input("Smoke test", 0.0, 500.0, 5.0)
        md_h = st.number_input("Merge and Deploy", 0.0, 500.0, 6.0)

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🚀 GENERATE DATA", use_container_width=True) or sync:
            inputs = {"Analysis":a_h,"Dev":d_h,"Fixes":f_h,"Review":r_h,"QA_Test":q_h,"TC_Prep":tp_h,"Retest":rt_h,"Integ":it_h,"Smoke":sm_h,"Deploy":md_h}
            st.session_state.master_plan, st.session_state.sprint_meta = run_allocation(dev_names, qa_names, lead_names, inputs, num_sprints, start_date, sprint_days)
            st.session_state.quality_data = pd.DataFrame([{"Sprint": s, "Test Cases": 0, "Bugs Found": 0} for s in st.session_state.sprint_meta.keys()])
            st.rerun()
    with col_btn2:
        if st.session_state.master_plan is not None:
            if st.button("⚖️ BALANCE RESOURCES", use_container_width=True):
                st.session_state.master_plan = balance_resources(st.session_state.master_plan, capacity)
                st.success("Resource load balanced across team members!")
                st.rerun()

    if st.session_state.master_plan is not None:
        st.session_state.master_plan = st.data_editor(st.session_state.master_plan, use_container_width=True)

with tab2:
    if st.session_state.master_plan is not None:
        pivot = st.session_state.master_plan.pivot_table(index="Owner", columns="Sprint", values="Hours", aggfunc="sum", fill_value=0)
        st.dataframe(pivot.style.applymap(lambda x: 'background-color: #501010' if x > capacity else ''), use_container_width=True)

with tab3:
    if st.session_state.master_plan is not None:
        st.session_state.quality_data = st.data_editor(st.session_state.quality_data, use_container_width=True)
        q_df = st.session_state.quality_data.copy()
        qa_hrs = st.session_state.master_plan[st.session_state.master_plan["Role"] == "QA"].groupby("Sprint")["Hours"].sum()
        q_df["Productivity"] = (q_df["Test Cases"] / q_df["Sprint"].map(qa_hrs).replace(0,1)).round(2)
        avg_density = (q_df["Bugs Found"].sum() / q_df["Test Cases"].replace(0,1).sum()) if q_df["Test Cases"].sum() > 0 else 0.1
        q_df["Predicted Risk"] = q_df.apply(lambda r: round(r["Test Cases"] * avg_density) if r["Bugs Found"] == 0 and r["Test Cases"] > 0 else None, axis=1)
        st.table(q_df.fillna("-"))
