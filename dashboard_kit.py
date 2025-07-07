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
    # ---- Overview Panel ----
    def render_scenario_selector() -> dict:
        # ---- Find Initialize Scenarios ----
        if "metadata_table" in st.session_state and len(st.session_state["metadata_table"]) > 0:
            initial_scenarios = list(st.session_state["metadata_table"]["Scenario"])
        else: 
            initial_scenarios = None
        theme_colors = ['rgb(51, 204, 255)', 'rgb(204, 51, 0)', 'rgb(204, 153, 255)', 'rgb(255, 102, 204)']

        # ---- Inject custom CSS to change tag colors ----
        def colorize_multiselect_options(colors: list[str]) -> None:
            rules = ""
            for i, color in enumerate(colors):
                rules += f""".stMultiSelect div[data-baseweb="select"] span[data-baseweb="tag"]:nth-child({len(colors)}n+{i+1}){{background-color: {color};}}"""
            st.markdown(f"<style>{rules}</style>", unsafe_allow_html=True)
        colorize_multiselect_options(theme_colors)

        # ---- Render Scenario Selector ----
        selected_scenarios = st.multiselect(
            label = "Result Search: ",
            options = st.session_state["df_summary"]['Scenario'],
            default = initial_scenarios,
            placeholder = "Select Core Option/s to Visualize",
            key="scenario_multiselect",
            max_selections = 3,
        )
        # ---- Update Scenario Data ----
        # if initial_scenarios is not None and sorted(selected_scenarios) == sorted(initial_scenarios):
        #     metadata_table = st.session_state["metadata_table"]
        #     data_collections = st.session_state["data_collections"]
        if selected_scenarios is None:
            metadata_table = pd.DataFrame()
            data_collections = {}
            color_dict = {}
        else:
            metadata_table = st.session_state["df_summary"].loc[st.session_state["df_summary"]['Scenario'].isin(selected_scenarios)]
            
            data_collections = dbp.load_scenarios_multiple(
                metadata_table = metadata_table,
                database_dir = st.session_state["Temporary Filing Directory"],
                scope = ["timeline", "passenger"]
            )
            color_dict = {
                scenario: theme_colors[i] for i, scenario in enumerate(data_collections.keys())
            }
        scenario_data = {"names": selected_scenarios, "metadata_table": metadata_table, "data_collections": data_collections, "color_dict": color_dict}

        return scenario_data

    def render_overview(scenario_data:dict) -> dict:
        # ---- Get Colors ----
        color_dict = scenario_data["color_dict"]
        # ---- Render Summary Table ----
        df_snapshot = dbp.get_snapshot(metadata_table = scenario_data["metadata_table"], color_dict = color_dict)
        # ---- Set Radar Chart Control ----
        radar_chart_display_controls = st.pills(
            label = "Show KPI Comparison Map:",
            selection_mode = "single",
            options  = {":material/data_usage:"},
            default = [":material/data_usage:"] if scenario_data["names"] else None,
            label_visibility = "collapsed",
        )
        # ---- Render Radar Chart ----
        if radar_chart_display_controls:
            ec.render_radar(df_snapshot = df_snapshot, theme_colors=color_dict, chart_size=400, key="radar_chart")

        return None
    
    def render_tower(scenario_data:dict) -> None:
        st.markdown("###### Tower Passenger Load Distribution")
        tower_graph = st.empty
        if len(scenario_data["metadata_table"]) == 1: st.image(os.path.dirname(os.path.abspath(__file__)) + r"\resource\temp_img\1-01.png", use_container_width=True)
        if len(scenario_data["metadata_table"]) == 2: st.image(os.path.dirname(os.path.abspath(__file__)) + r"\resource\temp_img\2-01.png", use_container_width=True)
        if len(scenario_data["metadata_table"]) == 3: st.image(os.path.dirname(os.path.abspath(__file__)) + r"\resource\temp_img\3-01.png", use_container_width=True)

    # ---------------------------------------------------------------------------------------------------------------------------------------------------------
    # ---- Timeline Charts ----
    def render_timeline_charts(scenario_data:dict, run_selected:str,) -> None:
        """
        Execute this only if scenario_data exist
        """
        # ---- Panel Layouts ----
        selected_charts = st.pills(
            label = "Select KPI/s: ",
            selection_mode = "multi",
            options  = ["Queue Length", "Wait Time", "Transit Time", "Travel Time"],
            default = ["Queue Length"],
        )
        with st.popover(label=str("Select Floor"), icon = ":material/filter_center_focus:", use_container_width =False):
            lobby_selected = dbp.load_lobby_selection(scenario_data["data_collections"])
        section_chart_display = st.container()

        # ---- Terminate if no chart is selected ----
        if not selected_charts: return None
        # ---- Get Dataframes ----
        timeline_dataframes = dbp.fetch_timelines(scenario_data["data_collections"], run_selected, lobby_selected)
        timeline_df_sorted = dff.sort_df_by_key("queue_length", timeline_dataframes)
        scenario_color_sorted = [scenario_data["color_dict"][scenario] for scenario in timeline_df_sorted.keys()]
        # ---- Get Time Range ----
        series_joint = pd.concat([df["time"] for key, df in timeline_df_sorted.items()]) 
        time_range = [series_joint.min(), series_joint.max()]

        # ---- Render Char Layout ----
        for i, chart in enumerate(selected_charts):
            section_chart_display.divider()
            chart_title = section_chart_display.empty()
            chart_plot = section_chart_display.empty()
            chart_controls = section_chart_display.popover(label=str(""), icon = ":material/filter_center_focus:", use_container_width =False)
            with chart_controls:
                chart_element_toggle = st.pills(
                    label = "Show Annotation:",
                    selection_mode = "multi",
                    options  = {"Peak", "Trend"},
                    default = ["Peak"],
                    label_visibility = "visible",
                    key= f"chart_element_toggle_{chart}_{i}",
                )
                y_ref = st.number_input(f"Set '{chart}' Threshold:", min_value=0, max_value=None, value=None, step=None, key=f"threshold_{chart}", label_visibility = "visible", help=f"Plot a refrence line for {chart} along  y axis.")

            # ---- Load Queue Length Chart ----
            if chart == "Queue Length":
                chart_title.markdown(f"###### Passenger Queue Length")
                if "timestamp" not in st.session_state: st.session_state["timestamp"] = None
                with chart_plot: st.session_state["timestamp"] = ec.render_queue_length_chart(scenario_data, run_selected, lobby_selected, y_ref, x_ref=st.session_state["timestamp"], key=f"ql_chart_{i}_1")
                # fig_chart = go.Figure()
                # for i, (key, df) in enumerate(timeline_df_sorted.items()):
                #     plf.plot_queue_length(fig_chart, df, scenario_color_sorted[i], len(scenario_data["data_collections"].keys())<=3)
                # if "Peak" in chart_element_toggle: plf.highlight_highiest_all(fig_chart)
                # if y_ref is not None: plf.add_horizontal_trace(fig_chart, y_ref, time_range)
                # chart_plot.plotly_chart(fig_chart)
                
            
            # ---- Load Wait Time Chart ----
            elif chart == "Wait Time":
                chart_title.markdown(f"###### Passenger Wait Time Average")
                with chart_plot: ec.render_wait_time_chart(scenario_data, run_selected, lobby_selected, y_ref)
            
            
        return {"lobby_selected": lobby_selected, "time_range": time_range, "timeline_dataframes": timeline_dataframes, "timestamp": st.session_state["timestamp"]}
    '''
    def render_lobby_panel(scenario_data):
        # ---- Set Containers ----
        lobby_charts = [st.container() for _ in scenario_data["data_collections"].keys()]
        # ---- Find Chart Size ----
        room_widths = [18.1,18.1,18.1,18.1]
        room_depths = [3.5,3.5,3.5,3.5]
        selected_room_widths =[]
        selected_room_depths = []
        for i in range(len(scenario_data["data_collections"].keys())):
            selected_room_widths.append(float(room_widths[i]))
            selected_room_depths.append(float(room_depths[i]))
        max_room_width = max(selected_room_widths)
        max_room_depth = max(selected_room_depths)

        for i, (scenario, content) in enumerate(scenario_data["data_collections"].items()):
            # ---- Set Controls ----
            df = timeline_dataframes[scenario]
            passenger_list = []
            if timer_controls == "Peak":
                passenger_list = list(range(0, df['queue_length'].max())) #df.loc[df['queue_length'].idxmax(), 'passenger_register']
            else:
                try: passenger_list = list(range(0, df.loc[df['time'] == time_slider, 'queue_length'].iloc[0])) # df.loc[df['time'] == t_animate, 'passenger_register'].iloc[0]
                except: passenger_list = []   
            
            # ---- Render Elements ----
            with lobby_charts[i]:
                # ---- Set Layouts ----
                lobby_stat_margin_l, lobby_stat_col1, lobby_stat_col2= lobby_charts[i].columns([0.05,0.8,4.2], gap = "medium", vertical_alignment = "bottom")
                lobby_crowd_icon = lobby_stat_col1.empty()
                lobby_grade_gauge = lobby_stat_col1.empty()
                lobby_crowd_chart = lobby_stat_col2.empty()
                # ---- Set Controls ----
                room_width = lobby_stat_col1.number_input("Room Dimensions:", min_value=1.0, max_value=100.0, value=selected_room_widths[i], step=0.5, icon = ":material/arrow_range:", label_visibility = "visible", key=f"lobby_width_{scenario}")
                room_depth = lobby_stat_col1.number_input("Depth:", min_value=1.0, max_value=100.0, value=selected_room_depths[i], step=0.5, icon = ":material/height:", label_visibility = "collapsed", key=f"lobby_depth_{scenario}")
                max_room_width = max(max_room_width, room_width)
                max_room_depth = max(max_room_depth, room_depth)
                # ---- Get Grade ----
                lobby_evaluation_dict = gu.los_calculator(area=(room_width*room_depth)/len(passenger_list) if len(passenger_list) > 0 else room_width*room_depth)
                lobby_evaluation = "<b>" + str(lobby_evaluation_dict["grade"]) + " | " + str(lobby_evaluation_dict['tag']) + "</b><br>" + str(lobby_evaluation_dict['description'])
                # ---- Render Elements ----                        
                with lobby_crowd_icon:
                    ec.render_person_plan_icon(icon_size=150, value=len(passenger_list), area=room_width*room_depth, color=color_dict[scenario], margin = 0,  key=f"person_icon_{scenario}")

                with lobby_grade_gauge:
                    ec.grading_gauge(input_grade=lobby_evaluation_dict["grade"], theme_color=color_dict[scenario], key=f"lobby_gauge_{scenario}_{i}")
                with lobby_crowd_chart:
                    ec.render_lobby(
                        passengers=passenger_list, room_x=room_width, room_y=room_depth,
                        room_x_max = max_room_width, room_y_max = max_room_depth,
                        theme_color=color_dict[scenario], chart_width=950, margin_top = 80, margin_bottom = 40, margin_side=25, key= f"lobby_{scenario}"
                        )
                with lobby_stat_col2.popover(label=str(lobby_evaluation_dict["tag"]), use_container_width =False):
                    st.caption(lobby_evaluation, unsafe_allow_html=True)
                    
                st.divider()
    '''
    def render_spatial_charts(timeline_dataframes:dict, color_dict:dict, run_selected:str, lobby_selected:str, time_selected:str = None) -> None:
        """
        Execute this only if scenario_data exist
        """
        # ---- Panel Layouts ----
        selected_grading = st.pills(
            label = "Select Grading/s: ",
            selection_mode = "multi",
            options  = ["Passengers in Lobby", "Crowding Simulation"],
            default = ["Crowding Simulation"],
        )
        #with st.popover(label=str("Select Time"), icon = ":material/filter_center_focus:", use_container_width =False):
        #st.divider()
        container_grading_charts = st.container()
        st.divider()
        container_graph2_col1, container_graph2_col2, container_graph2_col3 = st.columns([4,6,1], gap = "medium")
        timer_controls = container_graph2_col1.pills(
                label = "Show Peak:",
                selection_mode = "single",
                options  = {"Peak", ":material/schedule:", ":material/select:"},
                default = "Peak",
                label_visibility = "collapsed",
            )
        time_slider_placeholder = container_graph2_col2.empty()
        # ---- Construct Time Controls ----
        timestamps = []
        series_joint = pd.concat([df["time"] for key, df in timeline_dataframes.items()]) 
        time_range = [series_joint.min(), series_joint.max()]
        for t in range (time_range[0], time_range[1]):
            timestamps.append(timedelta(seconds = int(round(t, 0))))
        # ---- Get Peak Times ----
        peak_times = []
        for df in timeline_dataframes.values():
            peak_times.append(df.loc[df['queue_length'].idxmax(), 'time'])
        # ---- Intialize Time Slider ----
        time_slider = time_slider_placeholder.select_slider(
            label = "Time:", 
            options = timestamps, 
            value = timedelta(seconds = int(round(peak_times[0], 0))),
            disabled=(False if timer_controls == ":material/schedule:" else True), 
            label_visibility="collapsed"
            ).total_seconds() 

        # ---- Intialize Time ----
        time_set = []
        if timer_controls == "Peak": 
            time_set = peak_times
        elif timer_controls == ":material/select:" and time_selected is not None: 
            time_set = [gu.hhmmss_to_seconds(time_selected)]*len(timeline_dataframes.keys())
        else: 
            time_set = [time_slider]*len(timeline_dataframes.keys())
    
        # ---- Passenger Queue Over Time Pictorial Plot ----
        # ---- Add Area Grading Graphs ----
        if not selected_grading: return None
        with container_grading_charts:
            # ---- Add Pictorial Stacks ----
            if "Passengers in Lobby" in selected_grading:
                st.divider()
                # ---- Render Elements ----
                ec.render_pictorial_scatter(timeline_dataframes, time=time_set, theme_colors=list(color_dict.values())),
            # ---- Add Lobby Scatter ----
            if "Crowding Simulation" in selected_grading:
                
                # ---- Set Containers ----
                lobby_charts = [container_grading_charts.container() for _ in timeline_dataframes.keys()]
                # ---- Find Chart Size ----
                room_widths = [18.1,18.1,18.1,18.1]
                room_depths = [3.5,3.5,3.5,3.5]
                selected_room_widths =[]
                selected_room_depths = []
                for i in range(len(timeline_dataframes.keys())):
                    selected_room_widths.append(float(room_widths[i]))
                    selected_room_depths.append(float(room_depths[i]))
                max_room_width = max(selected_room_widths)
                max_room_depth = max(selected_room_depths)

                for i, (scenario, df) in enumerate(timeline_dataframes.items()):
                    # ---- Set Controls ----
                    passenger_list = []
                    if timer_controls == "Peak":
                        passenger_list = list(range(0, df['queue_length'].max()))
                    elif timer_controls == ":material/select:" and time_selected is not None:
                        try: passenger_list = list(range(0, df.loc[df['time'] == gu.hhmmss_to_seconds(time_selected), 'queue_length'].iloc[0]))
                        except: passenger_list = []   
                    else:
                        try: passenger_list = list(range(0, df.loc[df['time'] == time_slider, 'queue_length'].iloc[0]))
                        except: passenger_list = []   
                    
                    # ---- Render Elements ----
                    with lobby_charts[i]:
                        st.divider()
                        # ---- Set Layouts ----
                        lobby_stat_margin_l, lobby_stat_col1, lobby_stat_col2= lobby_charts[i].columns([0.05,0.8,4.2], gap = "medium", vertical_alignment = "bottom")
                        lobby_crowd_icon = lobby_stat_col1.empty()
                        lobby_grade_gauge = lobby_stat_col1.empty()
                        lobby_crowd_chart = lobby_stat_col2.empty()
                        # ---- Set Controls ----
                        room_width = lobby_stat_col1.number_input("Room Dimensions:", min_value=1.0, max_value=100.0, value=selected_room_widths[i], step=0.5, icon = ":material/arrow_range:", label_visibility = "visible", key=f"lobby_width_{scenario}")
                        room_depth = lobby_stat_col1.number_input("Depth:", min_value=1.0, max_value=100.0, value=selected_room_depths[i], step=0.5, icon = ":material/height:", label_visibility = "collapsed", key=f"lobby_depth_{scenario}")
                        max_room_width = max(max_room_width, room_width)
                        max_room_depth = max(max_room_depth, room_depth)
                        # ---- Get Grade ----
                        lobby_evaluation_dict = gu.los_calculator(area=(room_width*room_depth)/len(passenger_list) if len(passenger_list) > 0 else room_width*room_depth)
                        lobby_evaluation = "<b>" + str(lobby_evaluation_dict["grade"]) + " | " + str(lobby_evaluation_dict['tag']) + "</b><br>" + str(lobby_evaluation_dict['description'])
                        # ---- Render Elements ----                        
                        with lobby_crowd_icon:
                            ec.render_person_plan_icon(icon_size=150, value=len(passenger_list), area=room_width*room_depth, color=color_dict[scenario], margin = 0,  key=f"person_icon_{scenario}")

                        with lobby_grade_gauge:
                            ec.grading_gauge(input_grade=lobby_evaluation_dict["grade"], theme_color=color_dict[scenario], key=f"lobby_gauge_{scenario}_{i}")
                        with lobby_crowd_chart:
                            ec.render_lobby(
                                passengers=passenger_list, room_x=room_width, room_y=room_depth,
                                room_x_max = max_room_width, room_y_max = max_room_depth,
                                theme_color=color_dict[scenario], chart_width=950, margin_top = 80, margin_bottom = 40, margin_side=25, key= f"lobby_{scenario}"
                                )
                        with lobby_stat_col2.popover(label=str(lobby_evaluation_dict["tag"]), use_container_width =False):
                            st.caption(lobby_evaluation, unsafe_allow_html=True)
                            