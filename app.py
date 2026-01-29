import streamlit as st
import pandas as pd
import plotly.express as px
import io

st.set_page_config(page_title="Jarvis Ingest Architect", layout="wide")

# --- Constants & Validation ---
REQUIRED_INPUTS = [
    "Analysis Phase", "Development Phase", "Code Review", "Bug Fixes",
    "TC preparation", "QA testing", "Bug retest", "Integration testing",
    "Merge and Deploy", "Smoke test"
]

def validate_excel(df):
    missing = [col for col in REQUIRED_INPUTS if col not in df.columns]
    if missing:
        return False, missing
    return True, []

# --- Template Generator ---
def generate_template():
    output = io.BytesIO()
    # Create a dummy dataframe with the required headers
    template_df = pd.DataFrame(columns=REQUIRED_INPUTS)
    # Add one row of example data (zeros)
    template_df.loc[0] = [0] * len(REQUIRED_INPUTS)
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        template_df.to_excel(writer, index=False, sheet_name='ProjectInputs')
    return output.getvalue()

# --- Core Allocation Logic ---
def run_excel_allocation(dev_names, qa_names, data_row, settings):
    plan = []
    all_roles = dev_names + qa_names + ["Lead", "Designer", "DevOps"]
    resource_load = {f"Sprint {i}": {name: 0 for name in all_roles} for i in range(5)}
    
    multiplier = 1.10 if settings['apply_buffer'] else 1.0
    limit = settings['max_cap']

    def assign(sprint, names, task, role, hrs):
        owner = min(names, key=lambda x: resource_load[sprint][x])
        buffered = hrs * multiplier
        resource_load[sprint][owner] += buffered
        return {"Sprint": sprint, "Task": task, "Owner": owner, "Role": role, "Hours": buffered}

    # S0: Analysis
    plan.append(assign("Sprint 0", ["Lead"], "Analysis", "Lead", data_row["Analysis Phase"]))
    
    # S1 & S2: Development & quality gates
    dev_split = data_row["Development Phase"] / 2
    rev_split = data_row["Code Review"] / 2
    
    for s in ["Sprint 1", "Sprint 2"]:
        if s == "Sprint 1":
            plan.append(assign(s, qa_names, "TC Preparation", "QA", data_row["TC preparation"]))
        
        for d in dev_names:
            plan.append(assign(s, [d], "Development", "Dev", dev_split / len(dev_names)))
        
        # Lead Review with Backup Delegation
        if settings['enable_delegation'] and (resource_load[s]["Lead"] + (rev_split * multiplier) > limit):
            plan.append(assign(s, [settings['backup']], "Delegated Review", "Senior Dev", rev_split))
        else:
            plan.append(assign(s, ["Lead"], "Lead Review", "Lead", rev_split))

    # S3: Testing Heavy
    plan.append(assign("Sprint 3", qa_names, "QA Testing", "QA", data_row["QA testing"]))
    plan.append(assign("Sprint 3", qa_names, "Integration Testing", "QA", data_row["Integration testing"]))

    # S4: Stabilization & Launch
    plan.append(assign("Sprint 4", dev_names, "Bug Fixes", "Dev", data_row["Bug Fixes"]))
    plan.append(assign("Sprint 4", qa_names, "Bug Retest", "QA", data_row["Bug retest"]))
    plan.append(assign("Sprint 4", ["DevOps"], "Merge and Deploy", "Ops", data_row["Merge and Deploy"]))
    plan.append(assign("Sprint 4", qa_names, "Smoke Test", "QA", data_row["Smoke test"]))
    
    return pd.DataFrame(plan)

# --- Sidebar ---
with st.sidebar:
    st.header("📂 Data Management")
    
    # Template Downloader
    st.download_button(
        label="📄 Download Excel Template",
        data=generate_template(),
        file_name="jarvis_input_template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    uploaded_file = st.file_uploader("Upload Project Data", type=["xlsx", "csv"])
    
    st.divider()
    st.header("👥 Team")
    d_count = st.number_input("Dev Count", 1, 10, 3)
    q_count = st.number_input("QA Count", 1, 10, 1)
    dev_names = [st.text_input(f"Dev {i+1}", f"D{i+1}", key=f"d_{i}") for i in range(d_count)]
    qa_names = [st.text_input(f"QA {i+1}", f"Q{i+1}", key=f"q_{i}") for i in range(q_count)]
    
    st.divider()
    sprint_days = st.number_input("Sprint Days", 1, 30, 12)
    workload_cap = st.slider("Workload Cap %", 50, 100, 90)
    backup_dev = st.selectbox("Lead Backup", options=dev_names)
    enable_delegation = st.toggle("Enable Delegation", value=True)
    apply_buffer = st.toggle("10% Buffer", value=False)

# --- Main App ---
if uploaded_file:
    try:
        df_input = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
        is_valid, missing_cols = validate_excel(df_input)
        
        if not is_valid:
            st.error(f"Required {missing_cols} inputs missing")
        else:
            st.success("Data Validated")
            project_data = df_input.iloc[0]
            
            settings = {
                'apply_buffer': apply_buffer,
                'enable_delegation': enable_delegation,
                'backup': backup_dev,
                'max_cap': (sprint_days * 8) * (workload_cap / 100)
            }
            
            final_plan = run_excel_allocation(dev_names, qa_names, project_data, settings)
            
            tabs = st.tabs(["🚀 Timeline", "📊 Heatmap"])
            with tabs[0]:
                for i in range(5):
                    s_name = f"Sprint {i}"
                    with st.expander(s_name):
                        st.dataframe(final_plan[final_plan['Sprint'] == s_name], use_container_width=True, hide_index=True)
            with tabs[1]:
                load_df = final_plan.groupby(['Sprint', 'Owner'])['Hours'].sum().reset_index()
                st.plotly_chart(px.bar(load_df, x="Sprint", y="Hours", color="Owner", barmode="group"))
    except Exception as e:
        st.error(f"Error processing file: {e}")
else:
    st.info("Upload the Excel template with your phase hours to begin.")
