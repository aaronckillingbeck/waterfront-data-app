import os
from databricks import sql
from databricks.sdk.core import Config
import streamlit as st
import pandas as pd

# Ensure environment variable is set correctly
assert os.getenv('DATABRICKS_WAREHOUSE_ID'), "DATABRICKS_WAREHOUSE_ID must be set in app.yaml."

# Databricks config
cfg = Config()

# Reusable Database Functions
def run_insert(query: str, user_token: str):
    """Execute an INSERT statement."""
    with sql.connect(
        server_hostname=cfg.host,
        http_path=f"/sql/1.0/warehouses/{cfg.warehouse_id}",
        access_token=user_token
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)

def run_select(query: str, user_token: str) -> pd.DataFrame:
    """Execute a SELECT statement and return a DataFrame."""
    with sql.connect(
        server_hostname=cfg.host,
        http_path=f"/sql/1.0/warehouses/{cfg.warehouse_id}",
        access_token=user_token
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall_arrow().to_pandas()

def get_user_role(email: str, user_token: str) -> str:
    """Query the access controls table to determine the user's role. Defaults to Viewer."""
    safe_email = email.replace("'", "'")
    query = f"SELECT app_role FROM workspace.default.app_access_controls_aaron WHERE email = '{safe_email}' LIMIT 1"
    try:
        df = run_select(query, user_token)
        if not df.empty:
            return df.iloc[0]['app_role']
    except Exception:
        pass
    return "Viewer"

# Streamlit UI
st.set_page_config(layout="wide", page_title="WPD Mockup")
user_token = st.context.headers.get('X-Forwarded-Access-Token')
user_email = st.context.headers.get('X-Forwarded-Email', 'unknown@us.navy.mil')

try:
    st.session_state.user_role = get_user_role(user_email, user_token)
except Exception:
    st.session_state.user_role = 'Viewer'

is_editor = (st.session_state.user_role == 'Editor')

# Session State Initialization
if 'page' not in st.session_state:
    st.session_state.page = 'home'
if 'region' not in st.session_state:
    st.session_state.region = ''
if 'installation' not in st.session_state:
    st.session_state.installation = ''
if 'user_role' not in st.session_state:
    st.session_state.user_role = get_user_role(user_email, user_token)

def navigate(page_name):
    st.session_state.page = page_name

def go_button_action(role, region, installation):
    st.session_state.region = region
    st.session_state.installation = installation
    if role == "Role 1":
        navigate('role1')
    elif role == "Role 2":
        navigate('role2')

# Siderbar Role and Status
st.sidebar.markdown(f"Logged in as:\n{user_email}")
st.sidebar.markdown(f"Access level:\n{st.session_state.user_role}")
if not is_editor:
    st.sidebar.warning("You have Read-Only access. Contact an admin to request Editor access.")

# PAGE: HOME
if st.session_state.page == 'home':
    st.title("WPD Mockup")
    
    with st.container():
        role_selection = st.selectbox("Select Role", ["Role 1", "Role 2"])
        region_selection = st.selectbox("Select Region", ["Region 1", "Region 2"])
        inst_selection = st.selectbox("Select Installation", ["Installation 1", "Installation 2"])
        
        st.button("GO", on_click=go_button_action, args=(role_selection, region_selection, inst_selection))

# PAGE: ROLE 1 (Platform Changes)
elif st.session_state.page == 'role1':
    st.button("← Back to Home", on_click=navigate, args=('home',))
    st.title("Major Platform Change")
    st.markdown(f"**Context:** {st.session_state.region} | {st.session_state.installation}")

    col1, col2 = st.columns([1, 2])

    with col1:
        with st.expander("New", expanded=True):
            with st.form("platform_form", clear_on_submit=True):
                platform = st.text_input("Platform/Class", disabled=not is_editor)
                year = st.number_input("Change Year", min_value=2000, max_value=2100, step=1, value=2026, disabled=not is_editor)
                pier = st.text_input("Pier", disabled=not is_editor)
                
                if st.form_submit_button("Save Entry", disabled=not is_editor):
                    if platform and pier and is_editor:
                        safe_plat = platform.replace("'", "''")
                        safe_pier = pier.replace("'", "''")
                        q = f"""INSERT INTO workspace.default.platform_changes_aaron 
                                (region, installation, platform_class, change_year, pier) 
                                VALUES ('{st.session_state.region}', '{st.session_state.installation}', '{safe_plat}', {year}, '{safe_pier}')"""
                        run_insert(q, user_token)
                        st.success("Entry Saved")
                    else:
                        st.error("Platform and Pier are required.")
    with col2:
        try:
            df = run_select(f"SELECT platform_class, change_year, pier FROM workspace.default.platform_changes_aaron WHERE region='{st.session_state.region}' AND installation='{st.session_state.installation}' ORDER BY id DESC LIMIT 50", user_token)
            st.dataframe(df, use_container_width=True, hide_index=True)
        except Exception:
            st.info("No records found for this location.")

# PAGE: ROLE 2 (Pier Connections)
elif st.session_state.page == 'role2':
    st.button("← Back to Home", on_click=navigate, args=('home',))
    st.title("Pier Connections")
    st.markdown(f"**Context:** {st.session_state.region} | {st.session_state.installation}")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        with st.form("pier_network_form"):
            st.subheader("Available Systems")
            nipr = st.radio("NIPR Available?", ["Yes", "No"], horizontal=True, disabled=not is_editor)
            sipr = st.radio("SIPR Available?", ["Yes", "No"], horizontal=True, disabled=not is_editor)
            ncte = st.radio("NCTE Available?", ["Yes", "No"], horizontal=True, disabled=not is_editor)
            cable = st.radio("Cable Available?", ["Yes", "No"], horizontal=True, disabled=not is_editor)
            
            if st.form_submit_button("Save Configuration", disabled=not is_editor):
                if is_editor:
                    q = f"""INSERT INTO workspace.default.pier_connections_aaron 
                            (region, installation, nipr, sipr, ncte, cable) 
                            VALUES ('{st.session_state.region}', '{st.session_state.installation}', '{nipr}', '{sipr}', '{ncte}', '{cable}')"""
                    run_insert(q, user_token)
                    st.success("Configuration Saved")
    with col2:
        try:
            df2 = run_select(f"SELECT nipr, sipr, ncte, cable FROM workspace.default.pier_connections_aaron WHERE region='{st.session_state.region}' AND installation='{st.session_state.installation}' ORDER BY id DESC LIMIT 50", user_token)
            st.dataframe(df2, use_container_width=True, hide_index=True)
        except Exception:
            st.info("No network configurations logged for this location.")

