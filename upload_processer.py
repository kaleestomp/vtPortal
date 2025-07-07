import os
import json
import math
import pandas as pd
from datetime import datetime, timedelta
from io import StringIO
import streamlit as st
from elvr_pipeline_utilities import dataframe_functions as edff
from database_processor import database_processor as dbp

class upload_processor:

    @staticmethod

    # -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # ---- Process Raw Data ----
    #@st.dialog("Verify Uploads", width="large")
    def generate_logs_and_save(upload_collections:list[dict], database_dir:str, description:str = ""):
        
        # ---- Setup Pogress Bar ----
        log_sum = 0
        scenario_sum = 0
        for dict in upload_collections: 
            log_sum += dict["summary"]["log_count"].sum()
            scenario_sum += len(dict["summary"])
        status = "Processing Uploads. This may take a minute for large files..."
        loading_bar = st.progress(0, text = status)
        log_counter = 0
        scenario_counter = 0

        # ---- Iterate through Upload Collections ----
        for dict in upload_collections:
            # ---- Initialize Scenario Logs ----
            file_name = dict["name"]
            elvr_logs = dict["logs"]
            filing_dir = os.path.join(database_dir, file_name)

            # ---- Iterate through each Simulation ID ----
            unique_sim_ids = list({log["simulation_id"] for log in elvr_logs})
            
            for sim_id in unique_sim_ids:
                scenario_counter += 1

                # ---- Locate Directory ----
                scenario_filing_dir = os.path.join(filing_dir, sim_id)
                os.makedirs(scenario_filing_dir, exist_ok=True)# Create the directory if it doesn't exist

                # ---- Collect Log Data for current scenario ----
                matching_elvr_logs = [log for log in elvr_logs if log["simulation_id"] == sim_id]
                # ---- Skip if no logs for this simulation ID ----
                if not matching_elvr_logs: continue 

                # ---- Initialize Table Logs ----
                lift_logbook_runlist = []
                passenger_logbook_runlist = []
                timeline_dict_runlist = []
                timeline_all_lobbys_runlist = []

                # ---- Iterate through each Run ----
                run_counter = 0
                unique_run_ids = list({log["run"] for log in matching_elvr_logs})

                for run_id in unique_run_ids:
                    # ---- Collect Logs for current run ----
                    elvr_logs_per_run = [log for log in matching_elvr_logs if log["run"] == run_id]
                    df_passenger_elvr = None
                    df_lift_elvr = None
                    for log in elvr_logs_per_run:
                        if log["category"] == "Person":
                            df_passenger_elvr = log["dataframe"]
                        elif log["category"] == "SpatialPlot":
                            df_lift_elvr = log["dataframe"]

                    # ---- Skip if no passenger or lift logs for this run ----
                    if df_passenger_elvr is None or df_lift_elvr is None:
                        print(f"Skipping run {run_id} for simulation {sim_id} due to missing data.")
                        continue

                    # ---- Log Dataframes to Scenarios ----
                    lift_logbook = edff.parse_lift_elvr(df_lift_elvr)
                    passenger_logbook = edff.parse_passenger_elvr(df_passenger_elvr)
                    timeline_logbooks = edff.get_timeline_logbooks(passenger_logbook)
                    timeline_all_lobbys = edff.compile_timeline(list(timeline_logbooks.values()))

                    # ---- Save Dataframes ----
                    run_filing_dir = os.path.join(scenario_filing_dir, f"{run_id}")
                    os.makedirs(run_filing_dir, exist_ok=True)
                    lift_logbook.to_feather(os.path.join(run_filing_dir, "lift_logbook.feather"))
                    passenger_logbook.to_feather(os.path.join(run_filing_dir, "passenger_logbook.feather"))
                    timeline_all_lobbys.to_feather(os.path.join(run_filing_dir, "timeline_logbook.feather"))

                    for lobby_id, df_timeline in timeline_logbooks.items():
                        df_timeline.to_feather(os.path.join(run_filing_dir, f"timeline_logbook_{lobby_id}.feather"))

                    # ---- Save Summary Data ----
                    lift_count = len(lift_logbook['lift_id'].unique()) if lift_logbook is not None and 'lift_id' in lift_logbook else 0
                    scenario_name = f"{file_name}: {lift_count} Lift"

                    summary_dict = edff.get_summary_kpi([passenger_logbook], [timeline_all_lobbys])
                    summary_dict["name"] = scenario_name
                    summary_dict["simulation_id"] = sim_id
                    summary_dict["run_id"] = run_id
                    summary_dict["lift_count"] = lift_count
                    
                    summary_save_dir = os.path.join(run_filing_dir, "summary.txt")
                    with open(summary_save_dir, "w") as file: file.write(json.dumps(summary_dict, default=str)) # use `json.loads` to do the reverse

                    lift_logbook_runlist.append(lift_logbook)
                    passenger_logbook_runlist.append(passenger_logbook)
                    timeline_dict_runlist.append(timeline_logbooks)
                    timeline_all_lobbys_runlist.append(timeline_all_lobbys)

                    # ---- Update Status ----
                    log_counter += len(elvr_logs_per_run)
                    run_counter += 1
                    status = f"Processing Logs {log_counter}/{log_sum}... Scenario {scenario_counter}/{scenario_sum}, Run {run_counter}/{len(unique_run_ids)}" #Uploads ({log_counter/log_sum:.1%})...: 
                    loading_bar.progress((log_counter/log_sum), text = status)
                    
                # ---- Compile Run Data and Save----
                compiled_filing_dir = os.path.join(scenario_filing_dir, f"compiled")
                os.makedirs(compiled_filing_dir, exist_ok=True)
                compiled_timeline_all_lobbys_allrun = edff.compile_timeline(timeline_all_lobbys_runlist)
                compiled_timeline_all_lobbys_allrun.to_feather(os.path.join(compiled_filing_dir, "timeline_logbook.feather"))
                
                # ---- Compiled Timeline by Lobby ----
                #timeline_dict_runlist[0] is the first run. keys() are the lobby ids
                unique_lobby_ids = timeline_dict_runlist[0].keys() if timeline_dict_runlist else []
                for lobby_id in unique_lobby_ids:
                    # get all the runs for each lobby
                    timeline_perlobby_runlist = [timeline_dict[lobby_id] for timeline_dict in timeline_dict_runlist]
                    compiled_timeline_perlobby_allrun = edff.compile_timeline(timeline_perlobby_runlist)
                    compiled_timeline_perlobby_allrun.to_feather(os.path.join(compiled_filing_dir, f"timeline_logbook_{lobby_id}.feather"))
                
                # ---- Compile Summary ----
                scenario_summary = edff.get_summary_kpi(passenger_logbook_runlist, timeline_all_lobbys_runlist)
                scenario_summary["name"] = scenario_name    
                scenario_summary["simulation_id"] = sim_id
                scenario_summary["run_count"] = len(unique_run_ids)
                scenario_summary["lift_count"] = len(lift_logbook_runlist[0]['lift_id'].unique())
                scenario_summary["floor_count"] = passenger_logbook_runlist[0]["lobby_id"].nunique() if passenger_logbook_runlist else 0
                with open(os.path.join(scenario_filing_dir, "summary.txt"), "w") as file: 
                    file.write(json.dumps(scenario_summary, default=str))
            
            # ---- Additional Metadata ----
            metadata = {
                "project" : "GBC Hyundai",
                "author" : str(os.getlogin()),  # Fetch the username of the client-side computer
                "description" : description,
                "date" : datetime.now().strftime("%Y/%m/%d_%H:%M:%S"),
            }
            # ---- Save Metadata ----
            metadata_path = os.path.join(filing_dir, "metadata.txt")
            with open(metadata_path, "w") as file: file.write(json.dumps(metadata, default=str))

        # ---- Close Progress Bar ----
        loading_bar.empty()  # Clear the progress bar after processing is complete
    
    # ---- Verify Dataframes ----
    def verify_dataframes_and_submit(upload_collections:list[dict], base_dir:str, custom_description:str = ""):
        st.divider()
        file_name_display = st.empty()
        caption_display = st.empty()
        dataframe_display = st.empty()
        verify_col1, verify_col2, verify_col3 = st.columns([3,1,1], gap = "medium", vertical_alignment = "bottom", border = False)
        submitted = verify_col1.button("Submit", type = "primary", use_container_width = True)

        # ---- Get Summary Information ----
        upload_summaries = [content["summary"] for content in upload_collections]
        upload_names = [content["name"] for content in upload_collections]
        for i, upload_summary in enumerate(upload_summaries):
            upload_summary["name"] = pd.Series([upload_names[i]]).repeat(len(upload_summary)).reset_index(drop=True)
        upload_summary_joint = pd.concat(upload_summaries, ignore_index=True)
        upload_summary_joint = upload_summary_joint[["name", "simulation_id", "run", "lift_count", "log_count"]]

        summary_statement = f"""
            {len(upload_summary_joint)} Scenarios | 
            {upload_summary_joint["run"].sum()} Runs | 
            Lifts: {upload_summary_joint["lift_count"].min()} to {upload_summary_joint["lift_count"].max()} | 
            Total Logs: {upload_summary_joint["log_count"].sum()}
        """
        # ---- Display Summary Table ----
        file_name_display.markdown(f"###### Verify Contents:")
        caption_display.caption(summary_statement)
        dataframe_display.write(upload_summary_joint)
        
        # ---- Managge Submission ----  
        if submitted:
            upload_processor.generate_logs_and_save(upload_collections, base_dir, custom_description)
            # ---- Update Summary Table in Session State ----
            st.session_state["df_summary"] = dbp.get_summary(base_dir)
            # ---- Reset Uploader (Not Working Just Yet)----
            st.rerun() # Ensure the list is not empty

    # ---- Upload Form ----
    def render_upload_form(base_dir:str):
        upload_form_description = """
                #### Upload Data
                **Elevate Portal** digest raw data output from 
                **Elevate** or **Elevate Remake** to execute KPI analytics for critical communications.
                **Elevate Portal** collects, sort and stores data from each simulation run to enable performance tracking and comparative studies.
                You may upload new simulation data here.
            """
        # ---- Upload Form Header ----
        st.markdown(upload_form_description)
        st.divider()
        form_upload_col1, form_upload_col2 = st.columns([3, 2], gap = "medium", vertical_alignment = "top", border = False)
        # ---- Uploader Widget -----
        uploaded_file_list = form_upload_col1.file_uploader("Select Simulation Result File/s (.elvr)", type = [".elvr"], accept_multiple_files = True, label_visibility= "visible")
        custom_name = form_upload_col2.text_area("Optional Metadata:", value = None, placeholder = "Optional Scenario Name", label_visibility = "hidden")
        custom_description = form_upload_col2.text_area("Description:", value = None, height = 100, max_chars = 1000, placeholder = "Optional Scenario Description", label_visibility = "collapsed")

        # ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
        # ---- Process Uploads ----
        upload_collections = []
        elvr_name = ""
        for uploaded_file in uploaded_file_list:
            elvr_logs = edff.parse_elvr(uploaded_file)
            elvr_logs_summary = edff.summarise_elvr_logs(elvr_logs)
            elvr_name = os.path.splitext(uploaded_file.name)[0] # custom_name if custom_name is not None else os.path.splitext(uploaded_file.name)[0]
            elvr_content = {
                "name": elvr_name,
                "logs": elvr_logs,
                "summary": elvr_logs_summary
            }
            upload_collections.append(elvr_content)

        # ---- Verify Uploads ----
        if upload_collections: 
            upload_processor.verify_dataframes_and_submit(upload_collections, base_dir, custom_description)

# -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------