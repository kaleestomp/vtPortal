import streamlit as st
import os
import json
from datetime import datetime
import pandas as pd
from echarts import echarts as ec
from database_processor import database_processor as dbp
from elvr_pipeline_utilities import dataframe_functions as edff
from upload_processer import upload_processor as up

# ---- Page Meta-data ----
st.set_page_config(
    page_title="Elevate Portal",
    page_icon=":material/database:",
    layout = "wide" 
)
st.sidebar.success("Select a scope above.")

# ---- Initialize Session State ----
st.session_state["selected_rows"] = []
st.session_state["metadata_table"] = pd.DataFrame() 
st.session_state["Temporary Filing Directory"] = os.path.dirname(os.path.abspath(__file__)) + r"\resource\data"
project_list = ["GBC Hyundai", "Project Rise"]
temp_database_dir = st.session_state["Temporary Filing Directory"]
st.session_state["df_summary"] = dbp.get_summary(temp_database_dir)

# ---- Header ----
head_col1, head_col2 = st.columns([5, 1], gap = "medium", vertical_alignment = "bottom", border = False)
head_col1.write("# Welcome to Elevate Portal")
st.divider()
col1, col2 = st.columns([1.5, 4], gap = "medium", vertical_alignment = "top", border = False)

# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# ---- User Note ----
container_usernote = col1.container(key = "container_usernote", border=True)
container_usernote.markdown(
        f"""
        #### User Note
        Hello {str(os.getenv('USERNAME') or os.getenv('USER'))}! 👋  
        This is the prototye **Elevate Portal** to demo the management and visualize of Vertical Transport simulation data, including below features:  
        -- Mining simulation data and plotting KPIs via interactive charts (Queue Length, Wait Time, etc)  
        -- Overlay multiple results set via intuitive Multi-search bar  
        -- Manage Project datasets: any new and old results can be uploaded, processed, sorted, and visualized on the platform.  
        There is a directory page that shows you all catalogued simulation results associated to a project, tagged by KPIs and other relevant info
        Please go ahead and try them out. Remember that as many features are for demo only, they may not be stable.
    """
    )

# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# ---- Upload ----
form_upload = col1.container(key = "file_upload_form", border=True)
with form_upload:
    up.render_upload_form(temp_database_dir)

# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# ---- # Terminate Rest of the Program if no summary data is available ----
if st.session_state["df_summary"] is None: exit()

# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# ---- Set Up Directory ----
container_catalogue = col2.container(key = "scope_selection", border=True)
catalogue_col1, catalogue_col2 = container_catalogue.columns([1, 3], gap = "medium", vertical_alignment = "bottom", border = False)
with catalogue_col1:
    st.markdown("#### Project Directory")
    # ---- Project Selection ---
    st.selectbox("Project:", project_list, index = 0, placeholder = "Select a project for display", label_visibility = "collapsed", accept_new_options = False )
    # ---- Render Project Summary ---
    df_summary = st.session_state["df_summary"]
    project_state_summary = f"""
        Simulations Avaliable: {len(df_summary["Scenario"])}  
        Last Updated: {str(df_summary["Date"].max())}  
        """
    st.markdown(project_state_summary)

# ---- Directory Plot ----
with container_catalogue: 
    parallel_plot = st.empty()

# ---- Directory Table ----
catalogue_selection = container_catalogue.dataframe( #returns a dictionary
    data = st.session_state["df_summary"].drop(columns=["File"], inplace=False, errors="ignore"),
    height = 550,
    row_height= 50,
    use_container_width = True, 
    on_select = "rerun",
    selection_mode = "single-row",
    hide_index = True,
    column_config={
        "Queue Chart": st.column_config.LineChartColumn("Queue", y_min=0, y_max=df_summary["Longest Queue"].max()),
        "Wait Time Chart": st.column_config.LineChartColumn("Wait Time", y_min=0, y_max=df_summary["Max Wait Time"].max()),
        "Transit Time Chart": st.column_config.LineChartColumn("Transit Time", y_min=0, y_max=df_summary["Max Transit Time"].max()),
        "Travel Time Chart": st.column_config.LineChartColumn("Travel Time", y_min=0, y_max=df_summary["Max Travel Time"].max()),
        },
    )
st.session_state["selected_rows"] = catalogue_selection["selection"]["rows"]

# ---- Render Parrallel Plot ----
with parallel_plot:
    ec.render_parallel_plot(df_summary = st.session_state["df_summary"], chart_size=400, highlight_row_indices = st.session_state["selected_rows"],)
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# ---- Render Review Panels ----
with col2:
    st.session_state["metadata_table"] = st.session_state["df_summary"].loc[st.session_state["selected_rows"]]
    data_collections = dbp.load_scenarios_multiple(
        metadata_table = st.session_state["metadata_table"],
        database_dir = temp_database_dir,
        )
    dbp.render_dataframes(df_collections = data_collections, metadata_table = st.session_state["metadata_table"])