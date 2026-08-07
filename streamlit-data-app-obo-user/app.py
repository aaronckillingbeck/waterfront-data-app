import os
from databricks import sql
from databricks.sdk.core import Config
import streamlit as st
import pandas as pd

# Ensure environment variable is set correctly
assert os.getenv('DATABRICKS_WAREHOUSE_ID'), "DATABRICKS_WAREHOUSE_ID must be set in app.yaml."

# Databricks config
cfg = Config()

# Insert into the SQL warehouse with the user credentials
def insert_data_with_user_token(name: str, category: str, cost: float, user_token: str):
    """Execute an INSERT statement to append data to Unity Catalog."""
    query = f"""INSERT INTO workspace.default.waterfront_mock_data (name, category, cost) VALUES ('{name}', '{category}', '{cost}')"""
    with sql.connect(
        server_hostname=cfg.host,
        http_path=f"/sql/1.0/warehouses/{cfg.warehouse_id}",
        access_token=user_token  # Pass the user token into the SQL connect to insert on behalf of user
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)

# Query the SQL warehouse with the user credentials
def fetch_recent_data_with_user_token(user_token: str) -> pd.DataFrame:
    """Fetch the most recent table data to display in the app."""
    query = "SELECT * FROM workspace.default.waterfront_mock_data ORDER BY id DESC LIMIT 50"
    with sql.connect(
        server_hostname=cfg.host,
        http_path=f"/sql/1.0/warehouses/{cfg.warehouse_id}",
        access_token=user_token  # Pass the user token into the SQL connect to query on behalf of user
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall_arrow().to_pandas()

#UI setup
st.set_page_config(layout="wide")
st.title("Waterfront Data Entry")

# Extract user access token from the request headers
user_token = st.context.headers.get('X-Forwarded-Access-Token')
col1, col2 = st.columns([1, 2])

# In order to query with Service Principal credentials, comment the above line and uncomment the below line
# data = sql_query_with_service_principal("SELECT * FROM samples.nyctaxi.trips LIMIT 5000")
with col1:
    st.subheader("Add New Name")

    #UI Inputs
    name = st.text_input("Requester Name")
    category = st.selectbox("Category", ["Maintenance", "Cleaning", "Painting", "Fueling"])
    cost = st.number_input("Cost", min_value=0.0, step=10.0)

    # Submit Action
    if st.button("Append Record"):
        if name:
            try:
                insert_data_with_user_token(name, category, float(cost), user_token)
                st.success(f"Successfully added {name}")
            except Exception as e:
                st.error(f"Failed to insert record. Error: {e}")
        else:
            st.error("Name is required")
with col2:
    st.subheader("Recent Records")
    try:
        data = fetch_recent_data_with_user_token(user_token)
        st.dataframe(data=data, height=400, use_container_width=True)
    except Exception as e:
        st.info("No data found or table does not exist")


