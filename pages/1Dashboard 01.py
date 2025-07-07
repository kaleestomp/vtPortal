import os
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime, timedelta

from general_utilities import general_utilities as gu
from data_utilities import dataframe_functions as dff
from plotly_charts import plot_functions as plf
from echarts import echarts as ec
from database_processor import database_processor as dbp
from dashboard_kit import dashboard_kit as dbk

# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# ---- Page Meta-data ----
st.set_page_config(page_title="Elevate Dashboard", page_icon=":material/timeline:", layout="wide", initial_sidebar_state="expanded")

# ---- Session State Initialization ----
if "Temporary Filing Directory" not in st.session_state:
    st.session_state["Temporary Filing Directory"] = os.path.dirname(os.path.abspath(__file__)) + r"\resource\data"
if "df_summary" not in st.session_state:
    st.session_state["df_summary"] = dbp.get_summary(st.session_state["Temporary Filing Directory"])

# ---- Dynamic Input Initialization ----
run_selected = "compiled"
lobby_selected = "all"

# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# ---- Header ----
head_col1, head_col2, head_col3 = st.columns([8, 3, 1], gap = "small", vertical_alignment = "bottom", border = False)
head_col1.write("# Elevate Dashboard")
project_list = ["GBC Hyundai", "Project Rise"]
selected_project = head_col3.selectbox("Project:", project_list, index = 0, placeholder = "Select a project for display", label_visibility = "visible", accept_new_options = True )
st.divider()

# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# ---- Content Structure ----
col1, col2, col3 = st.columns([2, 3.25, 3.75], gap = "medium", vertical_alignment = "top", border = False)
container_overview = col1.container(border = True)
container_tower = col1.container(border = True)
container_graphs = col2.container(border = True)
container_graph2 = col3.container(border = True)

# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# ---- Select Scenario/s ----
# ---- Mult-Select Box ----
with container_overview: 
    st.markdown("#### Overview")
    scenario_data = dbk.render_scenario_selector()

# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# ---- KPI Overview ----
if scenario_data["names"]:
    # ---- KPI Summary ----
    with container_overview:
        with st.popover(label=str("Select Run"), icon = ":material/filter_center_focus:", use_container_width =False):
            run_selected = dbp.load_run_selection(df_collections = scenario_data["data_collections"])
        st.divider() 
        filter_lv1 = dbk.render_overview(scenario_data)
    # ---- Tower Graph ----
    with container_tower: dbk.render_tower(scenario_data)

# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# ---- Passenger Queue Over Time ----
if scenario_data["names"]:
    with container_graphs:
        st.markdown("#### Performance Breakdown")
        filter_lv2 = dbk.render_timeline_charts(scenario_data, run_selected,)
        lobby_selected = filter_lv2["lobby_selected"]
        timeline_dataframes = filter_lv2["timeline_dataframes"]
        timestamp = filter_lv2["timestamp"]

# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# ---- Query Point in Time ----
if scenario_data["names"]:
    with container_graph2:
        st.markdown("#### Lobby Comfort Grading")
        dbk.render_spatial_charts(
            timeline_dataframes = timeline_dataframes, 
            color_dict = scenario_data["color_dict"], 
            run_selected = run_selected, 
            lobby_selected = lobby_selected,
            time_selected = timestamp
            )