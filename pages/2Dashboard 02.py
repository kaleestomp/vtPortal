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
from dashboard_kit_2 import dashboard_kit as dbk2

# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# ---- Page Meta-data ----
st.set_page_config(page_title="Elevate Dashboard", page_icon=":material/timeline:", layout="wide", initial_sidebar_state="collapsed")

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

# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# ---- Content Structure ----
col1, col2 = st.columns([2, 7], gap = "small", vertical_alignment = "top", border = False)
container_overview = col1.container(border = True)
container_tower = col1.container(border = True)
container_graphs = col2.container(border = True)

# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# ---- Select Scenario/s ----
# ---- Mult-Select Box ----
with container_overview: 
    st.markdown("#### Overview")
    scenario_data = dbk.render_scenario_selector()
    color_dict = scenario_data["color_dict"]
    metadata_table = scenario_data["metadata_table"]
    # Rerieve Dataframe structure in [type]->[lobby]->[run]->[dataframe]
    scenario_data = dbp.sort_data_collections(scenario_data["data_collections"])
    
# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# ---- KPI Overview ----
if list(scenario_data.keys()):
    # ---- KPI Summary ----
    with container_overview:
        with st.popover(label=str("Select Run"), icon = ":material/filter_center_focus:", use_container_width =False):
            run_selected = dbp.load_run_pills(scenario_data)
        scenario_timestamps = dbk2.render_time_control({scenario: content["timeline"]["all"]["compiled"] for scenario, content in scenario_data.items()})

# ---- Passenger Queue Over Time ----
if list(scenario_data.keys()):
    with container_graphs:
        filter_lv2 = dbk2.render_lobby_panel(scenario_data, run_selected, scenario_timestamps, color_dict, metadata_table)