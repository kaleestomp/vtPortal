import os
import io
import math
import numpy as np
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from io import StringIO

class dataframe_functions:

    @staticmethod
    # -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    #### 0.1 Parse ELVR File to Inital Logs
    # ---- 0.1.1 Parse ELVR File ----
    def parse_elvr(uploaded_file, print_log = False) -> list[dict]:

        # ---- Pasrse ELVR ----
        logs = []
        # ---- Fetch File ----
        # uploaded_file is a file-like object (e.g. from Streamlit)
        f = io.TextIOWrapper(uploaded_file, encoding="utf-8")
        filename = getattr(uploaded_file, "name", "uploaded_file")

        # ---- Operate on File ----
        cur_table_category = None
        cur_table = []
        run = None
        sim_id = None
        lift_count = None
        field_mapping = {
            "SpatialPlot": ["lift_id", "time", "lobby_id", "load", "area"],
            "Person": ["time_arrived", "lobby_id", "unk_index_1", "destination_id", "weight","capacity_factor", "loading_time", "unloading_time", "tbc_time_disembarked",
                    "unk_index_2", "lift_id", "tbc_wait_time_end", "tbc_transit_time_end", 
                    "tbc_index_3", "actual_destination_id", "tbc_index_4", "tbc_index_5", "tbc_index_6", "tbc_index_7", "tbc_index_8", "tbc_index_9", "tbc_index_10", 
                    "tbc_metric_11", "tbc_metric_12", "tbc_metric_13", "tbc_index_14", "tbc_index_15"],
            }
        time_start = datetime.now()
        skip_categories = ["NoPassengers", "RemoteMonitoring"]

        # ---- Parse through each line ----
        for line in f: 
            # ---- Clean and Skip blank lines ----
            line = line.strip()
            if not line: continue
            # ---- Get Summary Inforamtion ----
            if line.startswith("SimulationID"):
                cells = line.split(",")
                sim_id = cells[0].split(": ")[1]
                run = cells[1].strip()
                if print_log: print("Loading Simulation ID: " + sim_id + ", Run: " + run)
                continue
            
            # ---- Collect Table Information ----
            entry_category = line.split(",")[0]
            
            # ---- Log First Line ----
            if cur_table_category is None:
                cur_table_category = entry_category
                cur_table.append(line)
                continue

            # ---- Log End of Table ----
            if (cur_table_category != entry_category): # End of current table
                if (cur_table_category not in skip_categories):
                    # ---- Log and Clear Table ----
                    if print_log: print(f"Loading Dataframe: {cur_table_category} with {len(cur_table)} entries")
                    df_elvr = pd.read_csv(StringIO("\n".join(cur_table)), header=None, low_memory=True)
                    df_elvr.drop(df_elvr.columns[0], axis=1, inplace=True)
                    # ---- Apply Field Mapping ----
                    if cur_table_category in field_mapping: df_elvr.columns = field_mapping[cur_table_category]
                    # ---- Get Lift Count ----
                    if cur_table_category == "SpatialPlot": lift_count = df_elvr.iloc[:, 0].nunique()
                    logs.append({"category": cur_table_category, "dataframe": df_elvr, "simulation_id": sim_id, "run": run, "lift_count": lift_count})
                    cur_table = []

                # ---- Start New Table ----
                cur_table_category = entry_category
                # ---- Skip Lines based on categories ----
                if cur_table_category in skip_categories: continue
                cur_table.append(line)
                continue
            
            # ---- Log Lines ----
            if cur_table_category == entry_category: # Collect Rows
                cur_table.append(line)
                continue
                
        print(f"Finished Parsing {filename} \nEntries Logged: {len(logs)} \nProcessing Time: {(datetime.now() - time_start).total_seconds()}s")

        return logs
  
    # ---- 0.1.2 Summarise ELVR Logs ----
    def summarise_elvr_logs(elvr_logs: list[dict]) -> pd.DataFrame:
        # ---- Initialize Summary Dataframe ----
        elvr_logs_metadata = pd.DataFrame(elvr_logs)[["simulation_id", "run", "category", "lift_count"]]
        # ---- Group by Simulation ID and Aggregate rest into list ----
        elvr_logs_summary = elvr_logs_metadata.groupby("simulation_id").agg(list).reset_index()
        elvr_logs_summary["run"] = elvr_logs_summary["run"].apply(lambda x: len(set(x)))
        elvr_logs_summary["category"] = elvr_logs_summary["category"].apply(lambda x: list(set(x)))
        elvr_logs_summary["lift_count"] = elvr_logs_summary["lift_count"].apply(lambda x: x[0] if x else 0)
        elvr_logs_summary["log_count"] = elvr_logs_summary.apply(lambda row: len(row["category"]) * int(row["run"]), axis=1)
        #lift_range = (min(lift_counts), max(lift_counts)) if lift_counts else (0, 0)
        return elvr_logs_summary
    
    
    # -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    #### 0.2 Parse ELVR Logs to Dictionary
    # ---- 0.2.1 Get Elevator Logbook Dataframe ----
    def parse_lift_elvr(df_lift_elvr:pd.DataFrame) -> dict[str, pd.DataFrame]:
        # ---- Fetch Passenger Dataframe ----
        df_lift = df_lift_elvr[["lift_id", "lobby_id", "time", "load", "area"]].copy()
        df_lift_dict = {}
        # ---- Log Lift Status ----
        for lift_id, df_lift_split in df_lift.groupby("lift_id"):
            # ---- Sort by Time and Reset Index ----
            lift_logbook = df_lift_split.copy()
            lift_logbook = lift_logbook.sort_values(by="time").reset_index(drop=True)

            status_series = []
            for log in lift_logbook.itertuples(index=True):
                # ---- Initialize Variables ----
                status = "unknown"
                # ---- Even Index: Arrival ----
                if log.Index % 2 == 0: 
                    status = "arriving"                
                # ---- Odd Index: Departure ----
                else:
                    if log.Index + 1 < len(lift_logbook):  # Check if further depature log exists
                        cur_lobby_id = log.lobby_id
                        next_lobby_id = lift_logbook.at[log.Index+1, "lobby_id"]
                        if next_lobby_id > cur_lobby_id:
                            status = "ascending"
                        else:
                            status = "descending"
                    # ---- Last Index: Termination ----
                    else: 
                        status = "terminating"
                status_series.append(status)
            lift_logbook.insert(3, "status", status_series, allow_duplicates=False)

            # ---- Add to Dictionary ----
            df_lift_dict[lift_id] = lift_logbook

        df_lift = pd.concat(list(df_lift_dict.values()), axis=0).reset_index(drop=True)

        return df_lift
    # ---- 0.2.2 Get Passenger Logbook Dataframe ----
    def parse_passenger_elvr(df_passenger_elvr:pd.DataFrame) -> dict[str, pd.DataFrame]:
        # ---- Fetch Passenger Dataframe ----
        df_passenger = df_passenger_elvr[["lobby_id", "destination_id", "lift_id", "time_arrived", "tbc_wait_time_end", "tbc_transit_time_end", "tbc_time_disembarked"]].copy()
        df_passenger.insert(0, "passenger_id", range(len(df_passenger)), allow_duplicates=False)
        # ---- Calculate KPI Metrics Part 1 ----
        adjusted_wait_time_end = df_passenger[['tbc_wait_time_end', 'time_arrived']].astype(float).max(axis=1)
        df_passenger['wait_time'] = adjusted_wait_time_end - df_passenger['time_arrived']
        df_passenger['transit_time'] = df_passenger['tbc_transit_time_end'] - adjusted_wait_time_end
        df_passenger['travel_time'] = df_passenger['wait_time'] + df_passenger['transit_time']

        return df_passenger
    
    
    # -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    #### 0.3 Parse ELVR Logs to Dictionary
    # ---- 0.3.1 Generate Timeline ----
    def get_timeline_logbooks(passenger_logbook: pd.DataFrame) -> dict:
        timeline_logbooks = {}

        for lobby_id, df_passenger_split in passenger_logbook.groupby("lobby_id"):
            start_time = math.floor(df_passenger_split['time_arrived'].min())
            finish_time = math.ceil(df_passenger_split['tbc_time_disembarked'].max())
            times = np.arange(start_time, finish_time)

            # Prepare intervals for each passenger (wait interval)
            pas_wait_time_start = df_passenger_split['time_arrived'].values
            pas_wait_time_end = df_passenger_split[['tbc_wait_time_end', 'time_arrived']].max(axis=1).values

            # Build a 2D boolean mask: rows are times, columns are passengers
            # mask[t, p] = True if passenger p is waiting at time t
            mask = (times[:, None] >= pas_wait_time_start[None, :]) & (times[:, None] <= pas_wait_time_end[None, :])

            # Pre-fetch required columns as arrays for fast slicing
            passenger_ids = df_passenger_split['passenger_id'].values
            wait_times = df_passenger_split['wait_time'].values
            transit_times = df_passenger_split['transit_time'].values
            travel_times = df_passenger_split['travel_time'].values

            # Alternative (and faster): build with list comprehensions
            passenger_id_register_series = [passenger_ids[mask[i]].tolist() for i in range(len(times))]
            wait_time_register_series = [wait_times[mask[i]].tolist() for i in range(len(times))]
            transit_time_register_series = [transit_times[mask[i]].tolist() for i in range(len(times))]
            travel_time_register_series = [travel_times[mask[i]].tolist() for i in range(len(times))]

            # KPIs (vectorized)
            queue_length_series = mask.sum(axis=1)
            def safe_stat(arr, func, empty_val=0):
                return func(arr) if len(arr) else empty_val
            mean_wait_time_series = [np.mean(wait_times[mask[i]]) if queue_length_series[i] else 0 for i in range(len(times))]
            max_wait_time_series = [np.max(wait_times[mask[i]]) if queue_length_series[i] else 0 for i in range(len(times))]
            mean_transit_time_series = [np.mean(transit_times[mask[i]]) if queue_length_series[i] else 0 for i in range(len(times))]
            max_transit_time_series = [np.max(transit_times[mask[i]]) if queue_length_series[i] else 0 for i in range(len(times))]
            mean_travel_time_series = [np.mean(travel_times[mask[i]]) if queue_length_series[i] else 0 for i in range(len(times))]
            max_travel_time_series = [np.max(travel_times[mask[i]]) if queue_length_series[i] else 0 for i in range(len(times))]

            # Build DataFrame
            df_timeline = pd.DataFrame({
                'time': times,
                'passenger_register': passenger_id_register_series,
                'queue_length': queue_length_series,
                'mean_wait_time': mean_wait_time_series,
                'max_wait_time': max_wait_time_series,
                'mean_transit_time': mean_transit_time_series,
                'max_transit_time': max_transit_time_series,
                'mean_travel_time': mean_travel_time_series,
                'max_travel_time': max_travel_time_series,
                'wait_time_register': wait_time_register_series,
                'transit_time_register': transit_time_register_series,
                'travel_time_register': travel_time_register_series,
            })

            timeline_logbooks[lobby_id] = df_timeline

        return timeline_logbooks
    # ---- 0.3.2 Compile Timeline ----
    def compile_timeline(df_timelines:list[pd.DataFrame]) -> pd.DataFrame:
        '''
        Compile timeline logbooks across multiple lobbys and/or runs
        '''
        # ---- Aggregate Timeline Dataframes ----
        df_compiled = pd.concat(df_timelines).groupby('time', as_index=False).agg(list)
        # ---- Drop Fields ----
        df_compiled.drop(columns=['passenger_register'], inplace=True) if 'passenger_register' in df_compiled.columns else None

        # ---- Compile KPI Metrics ----
        # ---- Insert Fields to Passenger Dataframe ----
        df_compiled['queue_length_regiester'] = df_compiled['queue_length']
        df_compiled['queue_length'] = df_compiled['queue_length'].apply(lambda x: max(x) if len(x)!= 0 else 0)

        df_compiled['wait_time_register'] = df_compiled['wait_time_register'].apply(lambda list_of_lists: [item for sublist in list_of_lists for item in sublist])
        df_compiled['transit_time_register'] = df_compiled['transit_time_register'].apply(lambda list_of_lists: [item for sublist in list_of_lists for item in sublist])
        df_compiled['travel_time_register'] = df_compiled['travel_time_register'].apply(lambda list_of_lists: [item for sublist in list_of_lists for item in sublist])

        df_compiled['mean_wait_time_register'] = df_compiled['mean_wait_time']
        df_compiled['mean_transit_time_register'] = df_compiled['mean_transit_time']
        df_compiled['mean_travel_time_register'] = df_compiled['mean_travel_time']
        
        df_compiled['mean_wait_time'] = df_compiled['wait_time_register'].apply(lambda x: round(sum(x)/len(x), 1) if len(x)!= 0 else 0)
        df_compiled['mean_transit_time'] = df_compiled['transit_time_register'].apply(lambda x: round(sum(x)/len(x), 1) if len(x)!= 0 else 0)
        df_compiled['mean_travel_time'] = df_compiled['travel_time_register'].apply(lambda x: round(sum(x)/len(x), 1) if len(x)!= 0 else 0)

        df_compiled['max_wait_time'] = df_compiled['max_wait_time'].apply(lambda x: max(x) if len(x)!= 0 else 0)
        df_compiled['max_transit_time'] = df_compiled['max_transit_time'].apply(lambda x: max(x) if len(x)!= 0 else 0)
        df_compiled['max_travel_time'] = df_compiled['max_travel_time'].apply(lambda x: max(x) if len(x)!= 0 else 0)

        return df_compiled
    
    
    # -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    #### 0.4 Cross Reference Logbook

    # -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    #### 0.5 Get Summary from Dataframes
    # ---- Get Summary Dictionary ----
    def get_summary_kpi(df_passenger_list:list, df_timeline_list:list) -> dict:
        '''
        Get summary metric out of a list of dataframes.
        This should be a combined list of all passenger logbooks and timeline logbooks
        across all lobbys and all runs if specified
        '''
        summary = {}
        # ---- Concatenate all passenger logbooks into a single DataFrame ----
        df_passenger_combined = pd.concat(df_passenger_list, axis=0).reset_index(drop=True)
        df_timeline_combined = pd.concat(df_timeline_list, axis=0).reset_index(drop=True)

        # ---- Calculate Summary KPIs ----
        summary["peak_time"] = df_timeline_combined.loc[df_timeline_combined['queue_length'].idxmax(), 'time']
        summary["queue_length"] = df_timeline_combined['queue_length'].max()
        summary["mean_wait_time"] = round(df_passenger_combined['wait_time'].mean(),1)
        summary["mean_transit_time"] = round(df_passenger_combined['transit_time'].mean(),1)
        summary["mean_travel_time"] = round(df_passenger_combined['travel_time'].mean(),1)
        summary["max_wait_time"] = round(df_passenger_combined['wait_time'].max(),1)
        summary["max_transit_time"] = round(df_passenger_combined['transit_time'].max(),1)
        summary["max_travel_time"] = round(df_passenger_combined['travel_time'].max(),1)
        
        # ---- Calculate Additional Metrics ----
        timespan = 0
        passenger_count = 0
        for i in range(len(df_timeline_list)):
            timespan = max(timespan, df_timeline_list[i]['time'].max() - df_timeline_list[i]['time'].iloc[0])
            passenger_count = max(passenger_count, len(df_passenger_list[i]))

        return summary

    
    # -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    #### 0.9 Master Function
    # ---- 0.9.1 Generate Logbook and Save ----

        # ---- Setup Pogress Bar ----
        # @st.dialog("Verify Uploads", width="large")
        # def verify_uploads(elvr_logs):
        loading_bar = st.progress(0, text="Processing Uploads. This may take a minute for large files...")
        log_counter = 0
        log_sum = len(elvr_logs)

        # ---- Initialize Scenario Logs ----
        scenario_logs = []
        unique_sim_ids = list({log["simulation_id"] for log in elvr_logs})
        # ---- Iterate through each Simulation ID ----
        for sim_id in unique_sim_ids:
            # ---- Collect Log Data for current scenario ----
            matching_elvr_logs = [log for log in elvr_logs if log["simulation_id"] == sim_id]
            # ---- Skip if no logs for this simulation ID ----
            if not matching_elvr_logs: continue 
            # ---- Initialize Log Data----
            scenario_log = {}
            scenario_log["simulation_id"] = sim_id
            scenario_log["lift_count"] = matching_elvr_logs[0]["lift_count"]
            scenario_log["run_count"] = sum(1 for log in matching_elvr_logs if log["category"] == "Person")

            # ---- Initialize Table Logs ----
            lift_table_dicts = []
            passenger_tables = []
            timeline_tables = []
            summary_dicts = []
            # ---- Iterate through each Run ----
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
                lift_table_dict = dataframe_functions.get_elevator_logs_dict(df_lift_elvr, df_passenger_elvr)
                passenger_table = dataframe_functions.get_passenger_logs_dataframe(df_passenger_elvr, df_lift_elvr)
                timeline_table = dataframe_functions.get_timeline_log_dataframe(passenger_table)
                passenger_table = dataframe_functions.update_passenger_logs_with_timeline_data(passenger_table, timeline_table)
                summary_dict = dataframe_functions.get_summary_kpi(passenger_table, timeline_table)
                summary_dict["simulation_id"] = sim_id
                summary_dict["run_id"] = run_id
                summary_dict["lift_count"] = len(lift_table_dict)

                lift_table_dicts.append(lift_table_dict)
                passenger_tables.append(passenger_table)
                timeline_tables.append(timeline_table)
                summary_dicts.append(summary_dict)

                # ---- Update Status ----
                log_counter += 1
                loading_bar.progress((log_counter/log_sum), text = f"Processing Log ({log_counter}/{log_sum})")
            
            # ---- Compile Run Data ----
            timeline_compiled = dataframe_functions.compile_timeline_logs(timeline_tables)
            compiled_summary = dataframe_functions.get_compiled_kpi(timeline_tables, passenger_tables)
            compiled_summary["simulation_id"] = sim_id
            compiled_summary["run_count"] = scenario_log["run_count"]
            compiled_summary["lift_count"] = scenario_log["lift_count"]

            # ---- Log Scenario Dataframes ----
            scenario_log["summary_dicts"] = summary_dicts
            scenario_log["lift_table_dicts"] = lift_table_dicts
            scenario_log["passenger_tables"] = passenger_tables
            scenario_log["timeline_tables"] = timeline_tables
            scenario_log["summary_compiled"] = compiled_summary
            scenario_log["timeline_compiled"] = timeline_compiled

            # ---- Update Log Data with Dataframe Information ----
            scenario_log["floor_count"] = passenger_tables[0]["lobby_id"].nunique() if passenger_tables else 0
            
            # ---- Log Scenario ----
            scenario_logs.append(scenario_log)

            # ---- Close Progress Bar ----
            loading_bar.empty()  # Clear the progress bar after processing is complete

        return scenario_logs
    

    