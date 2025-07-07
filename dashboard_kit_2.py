import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import plotly.graph_objects as go

from general_utilities import general_utilities as gu
from data_utilities import dataframe_functions as dff
from plotly_charts import plot_functions as plf
from echarts import echarts as ec
from database_processor import database_processor as dbp

class dashboard_kit:
    @staticmethod

    # ---------------------------------------------------------------------------------------------------------------------------------------------------------
    def render_lobby_plan_panel(scenario_data:dict, lobby_selected:str, run_selected:str, scenario_timestamps:dict, color_dict:dict) -> None:
        """
        Execute this only if scenario_data exist
        """
        # ---- Fetch Data ----
        scenario_timelines = {
            scenario : content["timeline"][lobby_selected][run_selected] for scenario, content in scenario_data.items()
            }

        # ---- Panel Layouts ----
        h_col1, h_col2 = st.columns([1, 25], gap = "small", vertical_alignment = "top", border = False)
        setting_panel = h_col1.popover(label=str(""), icon = ":material/low_density:", use_container_width =False)
        title = h_col2.empty()
        charts = {
            scenario: st.container() for scenario in scenario_timelines.keys()
            }
        # ---- Render Header ----
        title.markdown(f"##### Lobby Point-in-Time")
        with setting_panel:
            chart_size = st.number_input(
                        "Drawing Size:", min_value=100, max_value=None, 
                        value=1450, 
                        label_visibility = "visible", key=f"chart_size_{lobby_selected}"
                        )
        # ---- Find Chart Size ----
        scenario_lobby_dict = {}
        for scenario in scenario_timelines.keys():
            scenario_lobby_dict.setdefault(scenario, {})
            scenario_lobby_dict[scenario]["width"] = 18.1
            scenario_lobby_dict[scenario]["depth"] = 3.5
        
        max_room_width = max([dim_dict["width"] for dim_dict in scenario_lobby_dict.values()])
        max_room_depth = max([dim_dict["depth"] for dim_dict in scenario_lobby_dict.values()])
        margin_multiplier = 1.8 if len(scenario_timelines.keys()) < 2 else 1.0

        for scenario, df_timeline in scenario_timelines.items():

            timestamp = scenario_timestamps[scenario]
            queue_length = df_timeline.loc[df_timeline['time'] == timestamp, 'queue_length'].iloc[0] if timestamp in df_timeline['time'].tolist() else 0
            
            # ---- Render Elements ----
            with charts[scenario]:
                # ---- Set Layouts ----
                margin, col1, col2= charts[scenario].columns([0.05, 1.2, 6], gap = "small", vertical_alignment = "bottom")
                lobby_crowd_icon = col1.empty()
                lobby_grade_gauge = col1.empty()
                lobby_grade_caption = col1.empty()
                
                lobby_crowd_chart = col2.empty()
                settings_panel = col2.popover(label=str("Lobby Dimensions"), icon = ":material/low_density:", use_container_width =False)
                
                # ---- Set Controls ----
                with settings_panel:
                    room_width = st.number_input(
                        "Lobby Dimensions:", min_value=1.0, max_value=100.0, 
                        value = scenario_lobby_dict[scenario]["width"], step=0.5, icon = ":material/arrow_range:", 
                        label_visibility = "visible", key=f"lobby_width_{scenario}"
                        )
                    room_depth = st.number_input(
                        "Depth:", min_value=1.0, max_value=100.0, 
                        value=scenario_lobby_dict[scenario]["depth"], step=0.5, icon = ":material/height:", 
                        label_visibility = "collapsed", key=f"lobby_depth_{scenario}"
                        )
                max_room_width = max(max_room_width, room_width)
                max_room_depth = max(max_room_depth, room_depth)
                # ---- Get Grade ----
                lobby_evaluation_dict = gu.los_calculator(area=(room_width*room_depth)/queue_length if queue_length > 0 else room_width*room_depth)
                lobby_evaluation = "<b>" + str(lobby_evaluation_dict["grade"]) + " | " + str(lobby_evaluation_dict['tag']) + "</b><br>" + str(lobby_evaluation_dict['description'])
                # ---- Render Elements ----                        
                with lobby_crowd_icon:
                    ec.render_person_plan_icon(icon_size=145, value=queue_length, area=room_width*room_depth, color=color_dict[scenario], margin = 0,  key=f"person_icon_{scenario}")
                with lobby_grade_gauge:
                    ec.grading_gauge(icon_size=180, input_grade=lobby_evaluation_dict["grade"], theme_color=color_dict[scenario], key=f"lobby_gauge_{scenario}")
                with lobby_crowd_chart:
                    
                    ec.render_lobby(
                        passengers=[0]*queue_length, room_x=room_width, room_y=room_depth,
                        room_x_max = max_room_width, room_y_max = max_room_depth,
                        theme_color=color_dict[scenario], chart_width=chart_size, 
                        margin_top = int(40*margin_multiplier), margin_bottom = int(20*margin_multiplier), margin_side=25, 
                        key= f"lobby_{scenario}"
                        )
                lobby_grade_caption.caption(lobby_evaluation, unsafe_allow_html=True)                    
    
    def render_queue_length_panel(scenario_data:dict, lobby_selected:str, run_selected:str, scenario_timestamps:dict, color_dict:dict, metadata_table:pd.DataFrame) -> None:
        # ---- Render Char Layout ----
        h_col1, h_col2 = st.columns([1, 25], gap = "small", vertical_alignment = "top", border = False)
        setting_panel = h_col1.popover(label=str(""), icon = ":material/search_activity:", use_container_width =False)
        title = h_col2.empty()
        chart = st.empty()
        with setting_panel:
            chart_element_toggle = st.pills(
                label = "Show Annotation:",
                selection_mode = "multi",
                options  = ["Peak", "Trend"],
                default = ["Peak"],
                label_visibility = "visible",
                key= f"chart_element_toggle_ql_{lobby_selected}",
            )
            y_ref = st.number_input(
                f"Set Y Reference Line:", 
                min_value=0, max_value=None, value=None, step=10, 
                key=f"threshold_ql_{lobby_selected}", label_visibility = "visible", 
                help=f"Plot a refrence line along  y axis."
                )
            chart_height = st.number_input(
                f"Chart Height:", 
                min_value=100, max_value=None, value=300, step=None, 
                key=f"chart_height_ql_{lobby_selected}", label_visibility = "visible", 
                help=f"Set the height of the chart in pixels. Default is 400px."
                )
        if len(set(scenario_timestamps.values())) == 1: #this doesn behave when there is only one scenario
            x_ref = list(scenario_timestamps.values())[0] # Make sure to pass as int here or upstream or it's not JSON serializable
            enable_click = True
        else:
            x_ref = None
            enable_click = False
        title.markdown(f"##### Passenger Queue Length")
        with chart: 
            timestamp = ec.render_queue_length_chart_v2(scenario_data, color_dict, metadata_table, run_selected, lobby_selected, y_ref, x_ref, enable_click, chart_height, 40, 30, key=f"ql_chart_{lobby_selected}")
            
        return {"timestamp": timestamp}

    def render_wait_time_panel(scenario_data:dict, lobby_selected:str, run_selected:str, scenario_timestamps:dict, color_dict:dict, metadata_table:pd.DataFrame) -> None:
        # ---- Render Char Layout ----
        h_col1, h_col2 = st.columns([1, 25], gap = "small", vertical_alignment = "top", border = False)
        setting_panel = h_col1.popover(label=str(""), icon = ":material/search_activity:", use_container_width =False)
        title = h_col2.empty()
        chart = st.empty()
        with setting_panel:
            chart_element_toggle = st.pills(
                label = "Show Annotation:",
                selection_mode = "multi",
                options  = ["Peak", "Trend"],
                default = ["Peak"],
                label_visibility = "visible",
                key= f"chart_element_toggle_wt_{lobby_selected}",
            )
            y_ref = st.number_input(
                f"Set Y Reference Line:", 
                min_value=0, max_value=None, value=None, step=10, 
                key=f"threshold_wt_{lobby_selected}", label_visibility = "visible", 
                help=f"Plot a refrence line along  y axis."
                )
            chart_height = st.number_input(
                f"Chart Height:", 
                min_value=100, max_value=None, value=300, step=None, 
                key=f"chart_height_wt_{lobby_selected}", label_visibility = "visible", 
                help=f"Set the height of the chart in pixels. Default is 400px."
                )
        if len(set(scenario_timestamps.values())) == 1: 
            x_ref = list(scenario_timestamps.values())[0] # Make sure to pass as int here or upstream or it's not JSON serializable
        else:
            x_ref = None
        title.markdown(f"##### Average Wait Time")
        with chart: 
            timestamp = ec.render_wait_time_chart_v2(scenario_data, color_dict, run_selected, lobby_selected, y_ref, x_ref, chart_height, 40, 30, key=f"wt_chart_{lobby_selected}")
            
        return {"timestamp": timestamp}
    
    def render_time_control(timeline_dataframes:dict, key = "time_control") -> float:
        # ---- Set Layout ----
        col1, col2 = st.columns([1.2,4], gap = "medium", vertical_alignment= "top", border = False)
        peak_toggle = st.empty()
        time_slider = st.empty()

        # ---- Construct Time Controls ----
        timestamps = []
        time_series_joint = pd.concat([df["time"] for df in timeline_dataframes.values()])
        for t in range (time_series_joint.min(), time_series_joint.max()): 
            timestamps.append(timedelta(seconds = int(round(t, 0))))
        peak_times = {
            name: int(df.loc[df['queue_length'].idxmax(), 'time']) # Make sure to pass as int or it's not JSON serializable
            for name, df in timeline_dataframes.items()
            }
        # ---- Set Peak Toggle  ----
        mode_list = ["Show Peak"]
        mode = peak_toggle.pills(
                label = "Show Peak:",
                selection_mode = "single",
                options  = mode_list,
                default = mode_list[0],
                label_visibility = "collapsed",
                key=key+"_mode_selector"
            )
        enable_timeslider = False if mode in mode_list else True
        # ---- Intialize Time Slider ----
        timestamp_selected = time_slider.select_slider(
            label = "Time:", 
            options = timestamps, 
            value = timestamps[0],
            disabled = not enable_timeslider, 
            label_visibility="collapsed",
            key=key+"_time_slider"
            ).total_seconds()
        
        # ---- Return Timestamp ----
        scenario_timestamp = {name: int(timestamp_selected) for name in timeline_dataframes.keys()} if enable_timeslider else peak_times
        return scenario_timestamp
        
    def render_lobby_panel(scenario_data:dict, run_selected:str, scenario_timestamps:dict, color_dict:dict, metadata_table:dict) -> None:
        """
        Execute this only if scenario_data exist
        """
        # ---- Panel Layouts ----
        h_col1, h_col2 = st.columns([1, 25], gap = "small", vertical_alignment = "top", border = False)
        settings_panel = h_col1.popover(label=str(""), icon = ":material/filter_center_focus:", use_container_width =True)
        setting_form = settings_panel.form(key="lobby_settings_form", clear_on_submit=False, enter_to_submit= True, border=False)
        title = h_col2.empty()
        content_panel = st.container()

        # ---- Setting Panel ----
        with settings_panel:
            #update_scope = st.form_submit_button(label="Update", type="primary", icon=":material/autorenew:")
            scope_list = [
                ":material/bar_chart: KPIs Overview", 
                ":material/low_density: Lobby Point-in-Time",
                ":material/search_activity: Passenger Queue Length", 
                ":material/search_activity: Average Wait Time", 
                ":material/man: Passenger Queue Point-in-Time",
                ":material/data_usage: Passenger Wait Time", 
                ]
            selected_scopes = st.pills(
                label = "Select KPI/s: ",
                selection_mode = "multi",
                options  = scope_list,
                default = [scope_list[1], scope_list[2]],
            )
            lobby_selected = dbp.load_lobby_pills(scenario_data)
        

        # ---- Set Title ----
        title.markdown(f"#### {'All Levels' if lobby_selected == 'all' else f'Level {lobby_selected}'}")
        scope_containers = {
            scope.split(": ")[-1]: st.container() for scope in selected_scopes
            }
        
        if "Passenger Queue Length" in scope_containers.keys():
            with scope_containers["Passenger Queue Length"]:
                click_timestamp_hhmmss = dashboard_kit.render_queue_length_panel(scenario_data, lobby_selected, run_selected, scenario_timestamps, color_dict, metadata_table)["timestamp"]
                click_timestamp = gu.hhmmss_to_seconds(click_timestamp_hhmmss) if click_timestamp_hhmmss is not None else None
                if list(scope_containers.keys()).index("Passenger Queue Length")+1 != len(scope_containers.keys()): st.divider()
        if "Average Wait Time" in scope_containers.keys():
            with scope_containers["Average Wait Time"]:
                dashboard_kit.render_wait_time_panel(scenario_data, lobby_selected, run_selected, scenario_timestamps, color_dict, metadata_table)
                if list(scope_containers.keys()).index("Average Wait Time")+1 != len(scope_containers.keys()): st.divider()
        if "Lobby Point-in-Time" in scope_containers.keys():
            with scope_containers["Lobby Point-in-Time"]:
                # ---- Review below conditions it doesn work at the moment ----
                input_timestamp = scenario_timestamps if click_timestamp is None or (len(set(scenario_timestamps.values())) == 1 and len(scenario_timestamps.keys())>1) else {scenario: click_timestamp for scenario in scenario_timestamps.keys()}
                dashboard_kit.render_lobby_plan_panel(scenario_data, lobby_selected, run_selected, input_timestamp, color_dict)
                if list(scope_containers.keys()).index("Lobby Point-in-Time")+1 != len(scope_containers.keys()): st.divider()