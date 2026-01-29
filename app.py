import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import io

# Config
st.set_page_config(page_title="Jarvis - Sprint planning", layout="wide")

# --- 1. Persistent Memory ---
if 'master_plan' not in st.session_state:
    st.session_state.master_plan = None
if 'release_quality' not in st.session_state:
    st.session_state.release_quality = pd.DataFrame()
if 'team_setup' not in st.session_state:
    st.session_state.team_setup = {"devs": [], "qas": [], "leads": [], "capacity": 0}

# --- 2. Logic Engine ---
def run_allocation(devs, qas, leads, planning_data, num_sprints, start_date, sprint_days):
    plan = []
    curr_dt = pd.to_datetime(start_date)
    for i in range(num_sprints):
        s_start = curr_dt + timedelta(days=i * sprint_days)
        s_end = s_start + timedelta(days=sprint_days - 1)
        s_label = f"Sprint {i}"

        def assign(task, role, names, total_hrs):
            if total_hrs <= 0 or not names: return
            split = float(total_hrs) / len(names)
            for name in names:
                plan.append({"Sprint": s_label, "Start": s_start, "Finish": s_end, 
                             "Task": task, "Owner": name, "Role": role, "Hours": round(split, 1)})

        if i == 0:
            assign("Analysis Phase", "Lead", leads, planning_data["Analysis"])
            assign("TC preparation", "QA", qas, planning_data["TC_Prep"])
        elif 0 < i < (num_sprints - 1):
            mid = max(1, num_sprints - 2)
            assign("Development Phase", "Dev", devs, planning_data["Dev"]/mid)
            assign("Code Review", "Lead", leads, planning_data["Review"]/mid)
            assign("QA testing", "QA", qas, planning_data["QA_Test"]/mid)
            assign("Bug retest", "QA", qas, planning_data["Retest"]/mid)
            assign("Bug Fixes", "Dev", devs, planning_data["Fixes"]/mid)
        elif i == (num_sprints - 1):
            assign("Integration Testing", "QA", qas, planning_data["Integ"])
            assign("Smoke test", "QA", qas, planning_data["Smoke"])
            assign("Merge and Deploy", "Ops", ["DevOps"], planning_data["Deploy"])
    return pd.DataFrame(plan)

# --- 3. Sidebar Navigation ---
st.sidebar.title("💠 Jarvis Navigation")
page = st.sidebar.radio("Go to:", ["Master Setup", "Roadmap Editor", "Resource Split-up", "Quality Metrics"])

# --- PAGE: MASTER SETUP ---
if page == "Master Setup":
    st.title("⚙️ Project & Team Configuration")
    
    with st.expander("👥 Team Definition", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            d_sz = st.number_input("Devs", 1, 10, 3)
            devs = [st.text_input(f"D{j+1}", f"Dev_{j+1}", key=f"d{j}") for j in range(d_sz)]
        with col2:
            q_sz = st.number_input("QAs", 1, 5, 1)
            qas = [st.text_input(f"Q{j+1}", f"QA_{j+1}", key=f"q{j}") for j in range(q_sz)]
        with col3:
            l_sz = st.number_input("Leads", 1, 5, 1)
            leads = [st.text_input(f"L{j+1}", f"Lead_{j+1}", key=f"l{j}") for j in range(l_sz)]

    with st.expander("📅 Sprint Schedule & Effort", expanded=True):
        c1, c2, c3 = st.columns(3)
        start_dt = c1.date_input("Start", datetime(2026, 2, 9))
        num_sp = c2.number_input("Sprints", 2, 24, 4)
        sp_days = c3.number_input("Days/Sprint", 1, 60, 10)
        daily_h = st.slider("Daily Limit", 1, 24, 8)
        st.session_state.team_setup['capacity'] = sp_days * daily_h

        st.subheader("Planning Inputs")
        pc1, pc2 = st.columns(2)
        with pc1:
            h_a = st.number_input("Analysis", 0.0); h_d = st.number_input("Dev", 0.0); h_f = st.number_input("Bug Fixes", 0.0)
            h_r = st.number_input("Review", 0.0); h_q = st.number_input("QA Test", 0.0)
        with pc2:
            h_t = st.number_input("TC Prep", 0.0); h_re = st.number_input("Retest", 0.0); h_i = st.number_input("Integ", 0.0)
            h_s = st.number_input("Smoke", 0.0); h_de = st.number_input("Deploy", 0.0)

    if st.button("🚀 GENERATE ALL PAGES", use_container_width=True):
        inputs = {"Analysis": h_a, "Dev": h_d, "Fixes": h_f, "Review": h_r, "QA_Test": h_q, 
                  "TC_Prep": h_t, "Retest": h_re, "Integ": h_i, "Smoke": h_s, "Deploy": h_de}
        st.session_state.master_plan = run_allocation(devs, qas, leads, inputs, num_sp, start_dt, sp_days)
        st.session_state.release_quality = pd.DataFrame([{"Sprint": f"Sprint {i}", "TCs Created": 0, "TCs Executed": 0, "Bugs Found": 0} for i in range(num_sp)])
        st.success("Data Propagated to all pages.")

# --- PAGE: ROADMAP EDITOR ---
elif page == "Roadmap Editor":
    st.title("🗺️ Roadmap Editor")
    if st.session_state.master_plan is not None:
        cap = st.session_state.team_setup['capacity']
        usage = st.session_state.master_plan.groupby(['Sprint', 'Owner'])['Hours'].sum().reset_index()
        over = usage[usage['Hours'] > cap]
        if not over.empty:
            for _, r in over.iterrows(): st.error(f"⚠️ {r['Owner']} overload in {r['Sprint']} ({r['Hours']}h > {cap}h)")
        
        st.session_state.master_plan = st.data_editor(st.session_state.master_plan, use_container_width=True)
    else:
        st.info("Configure 'Master Setup' first.")

# --- PAGE: RESOURCE SPLIT-UP ---
elif page == "Resource Split-up":
    st.title("📊 Resource Wise Sprint Split-up")
    if st.session_state.master_plan is not None:
        owners = st.session_state.master_plan["Owner"].unique()
        selected = st.selectbox("Select Resource to Inspect", owners)
        
        res_data = st.session_state.master_plan[st.session_state.master_plan["Owner"] == selected]
        
        c1, c2 = st.columns([1, 2])
        with c1:
            st.write(f"**Workload for {selected}**")
            st.dataframe(res_data[["Sprint", "Task", "Hours"]], hide_index=True)
        with c2:
            fig = px.pie(res_data, values='Hours', names='Task', title=f"Task Distribution: {selected}")
            st.plotly_chart(fig)
        
        st.divider()
        st.subheader("Global Resource Comparison")
        comp = st.session_state.master_plan.pivot_table(index="Owner", columns="Sprint", values="Hours", aggfunc="sum").fillna(0)
        st.dataframe(comp.style.background_gradient(cmap="YlGnBu"), use_container_width=True)

# --- PAGE: QUALITY METRICS ---
elif page == "Quality Metrics":
    st.title("🛡️ Release Quality Metrics")
    if not st.session_state.release_quality.empty:
        st.session_state.release_quality = st.data_editor(st.session_state.release_quality, use_container_width=True)
        
        q = st.session_state.release_quality
        q["Execution %"] = (q["TCs Executed"] / q["TCs Created"].replace(0, 1) * 100).round(1)
        
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(px.line(q, x="Sprint", y="Bugs Found", markers=True, title="Defect Trend"))
        with col2:
            st.plotly_chart(px.bar(q, x="Sprint", y="Execution %", color="Execution %", title="Testing Coverage"))
