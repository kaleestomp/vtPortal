import os
import json
import math
import pandas as pd
from datetime import datetime, timedelta
from io import StringIO
import streamlit as st
from elvr_pipeline_utilities import dataframe_functions as edff
from data_utilities import dataframe_functions as dff
from general_utilities import general_utilities as gu

class database_processor:

    @staticmethod
    # -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # ---- Generate Summary Dataframe ----
    def get_summary(database_dir):
        file_list = [item for item in os.listdir(database_dir) if os.path.isdir(os.path.join(database_dir, item))]
        if not file_list: return None

        # ---- Initialize Metadata ----
        date_list = []
        author_list = []
        description_list = []

        elvr_name_list = []
        scenario_id_list = []
        scenario_name_list = []
        run_count_list = []
        lift_count_list = []
        max_queue_list = []
        peak_time_list = []
        mean_wait_time_list = []
        mean_transit_time_list = []
        mean_travel_time_list = []
        max_wait_time_list = []
        max_transit_time_list = []
        max_travel_time_list = []
        
        ql_chart_list = []
        wt_chart_list = []
        transit_chart_list = []
        travel_chart_list = []

        # ---- Process Each Filing Folder ----
        for file_name in file_list:
            file_dir = os.path.join(database_dir, file_name)
            scenario_ids = [item for item in os.listdir(file_dir) if os.path.isdir(os.path.join(file_dir, item))]
            if not scenario_ids: return None
            # ---- Fetch Filing Metadata ----
            date = None
            author = ""
            description = ""
            file_metadata_path = os.path.join(file_dir, "metadata.txt")
            if os.path.exists(file_metadata_path):
                with open(file_metadata_path, "r") as file:
                    metadata_cache = json.loads(file.read())
                    date = metadata_cache["date"]
                    author = metadata_cache["author"]
                    description = metadata_cache["description"]
            
            # ---- Append Level 1 Metadata ----
            scenario_id_list.extend(scenario_ids)
            elvr_name_list.extend([file_name] * len(scenario_ids))
            date_list.extend([date] * len(scenario_ids))  # Extend date list with the same date for each scenario
            author_list.extend([author] * len(scenario_ids))
            description_list.extend([description] * len(scenario_ids)) 

            # ---- Process Each Scenario ----
            for scenario_id in scenario_ids: 
                scenario_dir = os.path.join(file_dir, scenario_id)
                scenario_metadata_path = os.path.join(scenario_dir, "summary.txt")
                # ---- Append Level 2 Metadata ----
                if os.path.exists(scenario_metadata_path):
                    with open(scenario_metadata_path, "r") as file:
                        metadata_cache = json.loads(file.read())
                        scenario_name_list.append(metadata_cache['name'])
                        run_count_list.append(metadata_cache["run_count"])
                        lift_count_list.append(metadata_cache["lift_count"])

                        max_queue_list.append(metadata_cache["queue_length"])
                        peak_time_list.append(str(timedelta(seconds = int(metadata_cache["peak_time"]))))
                        mean_wait_time_list.append(metadata_cache["mean_wait_time"])
                        mean_transit_time_list.append(metadata_cache["mean_transit_time"])
                        mean_travel_time_list.append(metadata_cache["mean_travel_time"])
                        max_wait_time_list.append(metadata_cache["max_wait_time"])
                        max_transit_time_list.append(metadata_cache["max_transit_time"])
                        max_travel_time_list.append(metadata_cache["max_travel_time"])
                
                # ---- Sample Data for Charts ----
                df_timeline = pd.read_feather(os.path.join(scenario_dir, "compiled", "timeline_logbook.feather"))
                ql_charted = df_timeline['queue_length'].tolist() # or queue_length_mean, queue_length does not exist in compiled dataframe
                wt_charted = df_timeline['mean_wait_time'].tolist()
                transit_charted = df_timeline['mean_transit_time'].tolist()
                travel_charted = df_timeline['mean_travel_time'].tolist()
                ql_chart_list.append(ql_charted[::60])
                wt_chart_list.append(wt_charted[::60])
                transit_chart_list.append(transit_charted[::60])
                travel_chart_list.append(travel_charted[::60])
        
        df_summary = pd.DataFrame()
        df_summary["Date"] = date_list
        df_summary["File"] = elvr_name_list
        df_summary["ID"] = scenario_id_list
        df_summary["Scenario"] = scenario_name_list
        df_summary["Author"] = author_list
        df_summary["Description"] = description_list

        df_summary["Runs"] = run_count_list
        df_summary["Lifts"] = lift_count_list
        
        df_summary["Longest Queue"] = max_queue_list
        df_summary["Peak Time"] = peak_time_list
        df_summary["Queue Chart"] = ql_chart_list
        df_summary["Average Wait Time"] = mean_wait_time_list
        df_summary["Wait Time Chart"] = wt_chart_list
        df_summary["Average Transit Time"] = mean_transit_time_list
        df_summary["Transit Time Chart"] = transit_chart_list
        df_summary["Average Travel Time"] = mean_travel_time_list
        df_summary["Travel Time Chart"] = travel_chart_list
        df_summary["Max Wait Time"] = max_wait_time_list
        df_summary["Max Transit Time"] = max_transit_time_list
        df_summary["Max Travel Time"] = max_travel_time_list

        return df_summary

    def get_snapshot(metadata_table:pd.DataFrame, color_dict={}):
        df_snapshot = metadata_table.copy()
        df_snapshot.rename(columns={
            "Longest Queue": "Queue",
            "Average Wait Time": "Wait Time",
            "Average Transit Time": "Transit Time",
            "Average Travel Time": "Travel Time"
        }, inplace=True)
        # Apply rounding to specific columns
        #column_order = ["Scenario", "Lifts", "Longest Queue", "Average Wait Time", "Average Transit Time", "Average Travel Time"]   
        # columns_to_round = ["Queue", "Wait Time", "Transit Time", "Travel Time"]
        # for column in columns_to_round:
        #     if column in df_snapshot.columns: df_snapshot[column] = int(round(df_snapshot[column]))
        
        column_order = ["Scenario", "Lifts", "Queue", "Wait Time", "Transit Time", "Travel Time"]

        def highlight_row(row):
            color = color_dict.get(row['Scenario'], "white")  # Default to white if name not found
            color = gu.make_color_brighter(color, 0.8)  # Make the color brighter
            return ["background-color: {}".format(color)] * len(row)
        styled_df = df_snapshot.style.apply(highlight_row, axis=1)

        st.dataframe(styled_df, hide_index=True, use_container_width=True, column_order= column_order, on_select="ignore", row_height = 60)

        return df_snapshot

    # -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # ---- Load Dataframes to Memory ----
    def load_scenario_dataframes(scenario_id:str, file_name:str, database_dir:str, scope:list[str] = ["lift", "passenger", "timeline"]) -> dict:
        scenario_dir = os.path.join(database_dir, file_name, scenario_id)
        run_list = [item for item in os.listdir(scenario_dir) if os.path.isdir(os.path.join(scenario_dir, item))]
        df_collection = {}
        # ---- Fetch Run Data ----
        for run_id in run_list:
            #st.write(run_id)
            run_dir = os.path.join(scenario_dir, run_id)
            feather_list = [file for file in os.listdir(run_dir) if file.endswith('.feather')]
            run_dict = {}
            lift_dict = {}
            passenger_dict = {}
            timeline_dict = {}
            for feather_name in feather_list:
                feather_path = os.path.join(run_dir, feather_name)
                
                if feather_name.startswith("lift") and "lift" in scope: 
                    df_lift = pd.read_feather(feather_path)
                    run_dict["lift"] = df_lift
                    for lift_id, df_lift_split in df_lift.groupby("lift_id"):
                        lift_dict[str(lift_id)] = df_lift_split
                    run_dict["lift_perlift"] = lift_dict
                    
                elif feather_name.startswith("passenger") and "passenger" in scope:
                    df_passenger = pd.read_feather(feather_path)
                    run_dict["passenger"] = df_passenger
                    for lobby_id, df_passenger_split in df_passenger.groupby("lobby_id"):
                        passenger_dict[str(lobby_id)] = df_passenger_split
                    run_dict["passenger_perlobby"] = passenger_dict
                    
                elif feather_name.startswith("timeline") and "timeline" in scope:
                    # ---- Set Scope ----
                    col_names = pd.read_feather(feather_path, columns=[]).columns.tolist()
                    col_scope = [col for col in col_names if 
                                 not col.endswith("_register") or 
                                 col in ["wait_time_register", "mean_wait_time_register"]]
                    # wait_time_register takes a long time to load but necessary for queue length threshold graph
                    # -- Load Dataframe ----
                    if feather_name == "timeline_logbook.feather":
                        run_dict["timeline"] = pd.read_feather(feather_path, columns = col_scope)#
                    else:
                        lobby_id = feather_name.split("_")[-1].replace(".feather", "").strip()
                        timeline_dict[lobby_id] = pd.read_feather(feather_path, columns = col_scope)#
                        
            run_dict["timeline_perlobby"] = timeline_dict
            df_collection[str(run_id).strip()] = run_dict

        return df_collection
    
    def load_scenarios_multiple(metadata_table:pd.DataFrame, database_dir:str, scope:list[str] = ["lift", "passenger", "timeline"]) -> dict:
        # ---- Load Dataframes ----
        df_collections = {}
        theme_colors = ['rgb(51, 204, 255)', 'rgb(204, 51, 0)', 'rgb(204, 153, 255)', 'rgb(255, 102, 204)']

        for i, (idx, row) in enumerate(metadata_table.iterrows()):
            scenario = row["Scenario"]
            file_name = row["File"]
            scenario_id = row["ID"]
            # ---- Load Dataframes ----
            df_collection = database_processor.load_scenario_dataframes(scenario_id, file_name, database_dir, scope)
            df_collections[scenario] = {
                "data": df_collection,
                "color": theme_colors[i],
                "run_list" : list(df_collection.keys()),
                "lobby_list" : list(df_collection['compiled']['timeline_perlobby'].keys())
            }

        return df_collections
    
    def fetch_timelines(df_collections:dict, run_selected:str, lobby_selected:str) -> dict:
        timeline_dataframes = {}
        for scenario, content in df_collections.items():
            if lobby_selected == "all":
                timeline_dataframes[scenario] = content["data"][run_selected]["timeline"]
            else:
                timeline_dataframes[scenario] = content["data"][run_selected]["timeline_perlobby"][lobby_selected]
        return timeline_dataframes
    
    def sort_data_collections(data_collections:dict):
        data_collections_sorted = {}
        for scenario, content in data_collections.items():
            # Initialize Dict with Lobby_ID structure
            scenario_dict = {}
            scenario_dict["timeline"] = {}
            scenario_dict["passenger"] = {}
            #scenario_dict["lift"] = {}
            for run_id, run_dict in content["data"].items():
                # Ensure 'all' key exists for each type
                scenario_dict["timeline"].setdefault("all", {})
                scenario_dict["timeline"]["all"][run_id] = run_dict["timeline"]
                for lobby_id, df in run_dict["timeline_perlobby"].items():
                    scenario_dict["timeline"].setdefault(lobby_id, {})
                    scenario_dict["timeline"][lobby_id][run_id] = df

                if run_id == "compiled": continue

                scenario_dict["passenger"].setdefault("all", {})
                scenario_dict["passenger"]["all"][run_id] = run_dict["passenger"]
                for lobby_id, df in run_dict["passenger_perlobby"].items():
                    scenario_dict["passenger"].setdefault(lobby_id, {})
                    scenario_dict["passenger"][lobby_id][run_id] = df

                #scenario_dict["lift"].setdefault("all", {})
                #scenario_dict["lift"]["all"][run_id] = run_dict["lift"]
                # for lobby_id, df in run_dict["lift_perlift"].items():
                #     scenario_dict["lift"].setdefault(lobby_id, {})
                #     scenario_dict["lift"][lobby_id][run_id] = df

            data_collections_sorted[scenario] = scenario_dict
        
        return data_collections_sorted
    
    # def order_data_collections(data_collections:dict):
    #     names = list(data_collections.keys())
    #     kpis = []
    #     for content in data_collections.values():
    #         kpis.append(content["timeline"]["all"]["compiled"]["queue_length"].mean())
    #     sorted_names = [name for _, name in sorted(zip(kpis, names), reverse=True)]
    #     data_collections_sorted = {
    #         scenario: data_collections[scenario] for scenario in sorted_names
    #     }
    #     return data_collections_sorted
        
    # -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # ---- Selection Toggles -----
    def load_run_selection(df_collections:dict, multiple:bool = True, skip_compiled:bool = False, widget_key:str = "run_selectior",) -> str:
        run_list = []
        if multiple:
            for scenario, content in df_collections.items():
                for run_id in content["run_list"]:
                    if run_id not in run_list:
                        run_list.append(run_id)
        else:
            for run_id in df_collections.keys():
                if run_id not in run_list:
                    run_list.append(run_id)

        run_list = [run_id for run_id in run_list if str(run_id).isdigit()]
        run_list = sorted([int(run) for run in run_list])  # Convert to int for sorting
        run_list = [str(run) for run in run_list]  # Convert to string for display
        if not skip_compiled: run_list.insert(0, "compiled")
        run_selection = st.segmented_control(
            label="Select Run", 
            options= run_list, 
            default= run_list[0], 
            label_visibility="visible", 
            key = widget_key
            )
        
        return run_selection

    def load_lobby_options(df_collections:dict, multiple:bool = True) -> str:
        lobby_list = []
        if multiple:
            for scenario, content in df_collections.items():
                for lobby_id in content["lobby_list"]:
                    if lobby_id not in lobby_list:
                        lobby_list.append(lobby_id)
        else:
            for lobby_id in df_collections['compiled']['timeline_perlobby'].keys():
                if lobby_id not in lobby_list:
                    lobby_list.append(lobby_id)
    
        lobby_list = [lobby_id for lobby_id in lobby_list if str(lobby_id).isdigit()]
        lobby_list = sorted([int(lobby_id) for lobby_id in lobby_list])  # Convert to int for sorting
        lobby_list = [str(lobby_id) for lobby_id in lobby_list]  # Convert to string for display
        lobby_list.insert(0, "all")

        return lobby_list
    def load_lobby_selection(df_collections:dict, multiple:bool = True, widget_key:str = "lobby_selectior") -> str:
        lobby_list = database_processor.load_lobby_options(df_collections, multiple)
        lobby_selection = st.segmented_control(
            label="Select Lobby", 
            options = lobby_list,
            default = "all", 
            label_visibility="visible", 
            key = widget_key
            )
        return lobby_selection
    
    def load_lobby_selectbox(df_collections:dict, multiple:bool = True, widget_key:str = "lobby_selectior") -> str:
        lobby_list = database_processor.load_lobby_options(df_collections, multiple)
        lobby_selection = st.selectbox(
            label="Select Lobby", 
            options = lobby_list,
            index = 0,
            label_visibility="visible", 
            key = widget_key
            )
        return lobby_selection
    
    def load_run_pills(scenario_data:dict, widget_key:str = "run_selectior",) -> str:
        run_list = []
        for content in scenario_data.values():
            run_list.extend(content["timeline"]["all"].keys())
        run_list = list(set(run_list))
        if "compiled" in run_list: run_list.remove("compiled")
        run_list = [run_id for run_id in run_list if str(run_id).isdigit()]
        run_list = sorted([int(run) for run in run_list])  # Convert to int for sorting
        run_list = [str(run) for run in run_list]  # Convert to string for display
        run_list.insert(0, "compiled")
        run_selection = st.segmented_control(
            label="Select Run", 
            options= run_list, 
            default= run_list[0], 
            label_visibility="visible", 
            key = widget_key
            )
        
        return run_selection


    def load_lobby_pills(scenario_data:dict, widget_key:str = "lobby_selectior") -> str:
        lobby_list = []
        for content in scenario_data.values():
            lobby_list.extend(content["timeline"].keys())
        lobby_list = list(set(lobby_list))
        if "all" in lobby_list: lobby_list.remove("all")  # Remove 'all' if it exists
        lobby_list = [lobby_id for lobby_id in lobby_list if str(lobby_id).isdigit()]
        lobby_list = sorted([int(lobby_id) for lobby_id in lobby_list])  # Convert to int for sorting
        lobby_list = [str(lobby_id) for lobby_id in lobby_list]  # Convert to string for display
        lobby_list.insert(0, "all")
        
        lobby_selection = st.pills(
                label = "Select Lobby",
                selection_mode = "single",
                options  = lobby_list,
                default = lobby_list[0],
            )
        return lobby_selection


    def load_lift_selection(df_collection:dict, widget_key:str = "lift_selectior") -> str:
        lift_list = []
        for lift_id in df_collection['1']['lift_perlift'].keys():
            if lift_id not in lift_list:
                lift_list.append(lift_id)
    
        lift_list = [lift_id for lift_id in lift_list if str(lift_id).isdigit()]
        lift_list = sorted([int(lift_id) for lift_id in lift_list])  # Convert to int for sorting
        lift_list = [str(lift_id) for lift_id in lift_list]  # Convert to string for display
        lift_list.insert(0, "all")
        lift_selection = st.segmented_control(
            label="Select Lift", 
            options = lift_list,
            default = "all", 
            label_visibility="visible", 
            key = widget_key
            )
        return lift_selection
    
    # -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # ----- Render Dataframes -----
    def render_scenario_statement(scenario_metadata:pd.Series) -> None:
        scenario_state_summary = f"""
            Date: {scenario_metadata["Date"]}  
            Uploaded by: {scenario_metadata["Author"]}
            """
        st.markdown(scenario_state_summary)

    def render_kpi_metrics (scenario_metadata:pd.Series) -> None:
        col0, col1, col2, col3, col4, col5 = st.columns([2,1,1,1,1,1], gap = "small", vertical_alignment = "top", border = False)
        
        with col0: database_processor.render_scenario_statement(scenario_metadata)
        col1.metric(label="Lift/s", value=str(scenario_metadata["Lifts"]))
        col2.metric(label="Longest Queue", value=str(scenario_metadata["Longest Queue"]) + " p", delta="12")
        col3.metric(label="Average Wait Time", value=str(scenario_metadata["Average Wait Time"]) + " s", delta="24") # To be updated
        col4.metric(label="Average Transit Time", value=str(scenario_metadata["Average Transit Time"])) # To be updated
        col5.metric(label="Average Travel Time", value=str(scenario_metadata["Average Travel Time"])) # To be updated

    def render_dataframes(df_collections:dict, metadata_table:pd.DataFrame):

        for i, (idx, row) in enumerate(metadata_table.iterrows()):
            file_name = row["File"]
            scenario_id = row["ID"]
            scenario_name = row["Scenario"]
            container = st.container(key = f"container_review_{file_name.strip()}_{scenario_id}", border=True)
            df_collection = df_collections[scenario_name]["data"]
            
            with container:
                st.write(f"#### {scenario_name}")
                database_processor.render_kpi_metrics(scenario_metadata = row)
                tab_timeline, tab_passenger, tab_lift = st.tabs([":material/search_activity: Timeline", ":material/accessibility_new: Passenger Logs", ":material/elevator: Elevator Logs"])
                
                with tab_timeline:
                    run_selection = database_processor.load_run_selection(df_collection, multiple=False, widget_key=f"run_selection_timeline_{file_name.strip()}_{scenario_id}")
                    lobby_selection = database_processor.load_lobby_selection(df_collection, multiple=False, widget_key=f"lobby_selection_timeline_{file_name.strip()}_{scenario_id}")
                    if lobby_selection == "all": df_display = df_collection[str(run_selection)]["timeline"]
                    else: df_display = df_collection[str(run_selection)]["timeline_perlobby"][str(lobby_selection)]
                    
                    columns_todrop = [col for col in df_display.columns if 
                                      (col.endswith("_register") and col != "passenger_register") or
                                      col.endswith("_regiester") or
                                      col.startswith("threshold")]
                    
                    df_display.drop(columns=columns_todrop, inplace=True, errors="ignore")
                    if run_selection is not None: st.dataframe(df_display, height=800)

                with tab_passenger:
                    run_selection = database_processor.load_run_selection(df_collection, multiple=False, skip_compiled = True, widget_key=f"run_selection_passenger_{file_name.strip()}_{scenario_id}")
                    lobby_selection = database_processor.load_lobby_selection(df_collection, multiple=False, widget_key=f"lobby_selection_passenger_{file_name.strip()}_{scenario_id}")
                    if lobby_selection == "all": df_display = df_collection[str(run_selection)]["passenger"]
                    else: df_display = df_collection[str(run_selection)]["passenger_perlobby"][str(lobby_selection)]
                    if run_selection is not None: st.dataframe(df_display, height=800)

                with tab_lift:
                    run_selection = database_processor.load_run_selection(df_collection, multiple=False, skip_compiled = True, widget_key=f"run_selection_lift_{file_name.strip()}_{scenario_id}")
                    lift_selection = database_processor.load_lift_selection(df_collection, widget_key=f"lift_selection_{file_name.strip()}_{scenario_id}")
                    if lift_selection == "all": df_display = df_collection[str(run_selection)]["lift"]
                    else: df_display = df_collection[str(run_selection)]["lift_perlift"][str(lift_selection)]
                    if run_selection is not None: st.dataframe(df_display, height=800)

    # -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------