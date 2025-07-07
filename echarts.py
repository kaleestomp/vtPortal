import os
import math
import random
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import streamlit as st
from streamlit_echarts import st_echarts
from data_utilities import dataframe_functions as dff
from general_utilities import general_utilities as gu
from database_processor import database_processor as dbp


class echarts:
    @staticmethod
    #------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # ---- Render Time Chart ----

    def render_queue_length_chart(scenario_data:dict, run_selected, lobby_selected, y_ref = None, x_ref = "None", key = "ql_chart") -> None:
        # ---- Unpack Scenario Data ----
        data_collections = scenario_data["data_collections"]
        color_dict = scenario_data["color_dict"]
        metadata_table = scenario_data["metadata_table"]
        display_threshold = True if len(data_collections.keys()) < 2 else False
        thresholds = [60, 120, 180, 240]
        # ---- Sort Data ----
        data_dict = dbp.sort_data_collections(data_collections)
        # data_dict = dbp.order_data_collections(data_dict)
        # print(color_dict.keys())
        # print(data_dict.keys())
        # ---- Construct Series Data ----
        series = []
        z_height = 0
        for i, (scenario, content) in enumerate(data_dict.items()):
            color = color_dict[scenario]
            brightness = 0.8
            # ---- Add Domain Series ----
            df_timeline = content["timeline"][lobby_selected][run_selected]
            ql_data = df_timeline["queue_length"]
            peak_value = int(ql_data.max())
            peak_time = gu.seconds_to_hhmmss(int(df_timeline["time"][ql_data.idxmax()]))
            ql_series = [
                {
                "name": "Queue Length",
                "data": ql_data.astype(int).tolist(),
                "type": "line",
                "symbol": "none",
                "lineStyle": {"opacity": 1, "color": color, "width": 0.5, },
                "areaStyle": {"color": gu.make_color_brighter(color,brightness), "opacity": 1},
                "emphasis": {"disabled": True, "focus": "none"},
                "tooltip": {"show": False},
                "z": z_height,
                "markPoint": {
                    "data": [{
                        "name": "Peak",
                        "coord": [peak_time, peak_value],
                        "value": f"Peak: {peak_value}",
                        "label": {
                            "show": True,
                            "formatter": f"Peak: {peak_value}",
                            "fontSize": 14,
                            "color": "rgb(255,255,255)",
                            "fontWeight": "bold",
                            "align": "center",
                        },
                        "symbol": "rect",
                        "symbolSize": [100, 24],
                        "itemStyle": {"color": color}
                    }],
                    "symbolOffset": [0, -36], 
                    }
                },
                {
                "name": "Queue Length",
                "data": ql_data.astype(int).tolist(),
                "type": "line",
                "itemStyle": {"color": gu.make_color_brighter(color,brightness)},
                "lineStyle": {"opacity": 0},
                "emphasis": {"disabled": True, "focus": "none"},
                "tooltip": {"show": True},
                "z": z_height,
                },
            ]
            series.extend(ql_series)
            z_height += 1
            # ---- Fetch Threshold Data ----
            dataframe_updated = False
            for k, threshold in enumerate(thresholds):
                # ---- Check for Threshold Data ----
                if f"threshold_{threshold}" not in list(df_timeline.columns):
                    if run_selected == "compiled" or lobby_selected == "all":
                        fraction_data = df_timeline['wait_time_register'].apply(lambda lst: sum(x > threshold for x in lst)/len(lst) if len(lst) > 0 else 0)
                        theshold_data = round(ql_data * fraction_data, 1)
                    else:
                        theshold_data = df_timeline['wait_time_register'].apply(lambda lst: sum(x > threshold for x in lst) if len(lst) > 0 else 0)
                    df_timeline[f"threshold_{threshold}"] = theshold_data
                    dataframe_updated = True
                    print( f"threshold data updated for {scenario}: {threshold} s")
                theshold_data = df_timeline[f"threshold_{threshold}"]           
                # ---- Construct Threshold Series ----     
                area_color = gu.make_color_brighter(color, brightness - (brightness*((k+1)/len(thresholds))))
                fraction_series = [
                    {
                    "name": f"{threshold}s+",
                    "data": theshold_data.astype(int).tolist(),
                    "type": "line",
                    "symbol": "none",
                    "itemStyle": {"opacity": 0},
                    "lineStyle": {"color": color, "width": 0.5, "type": "dashed"},
                    "areaStyle": {"color": area_color, "opacity": 1},
                    "emphasis": {"disabled": True, "focus": "none"},
                    "tooltip": {"show": False},
                    "z": z_height,
                    },
                    {
                    "name": f"{threshold}s+",
                    "data": theshold_data.astype(int).tolist(),
                    "type": "line",
                    "itemStyle": {"color": area_color, "opacity": 1},
                    "lineStyle": {"opacity": 0},
                    "emphasis": {"disabled": True, "focus": "none"},
                    "tooltip": {"show": True if display_threshold and theshold_data.sum() > 0 else False},
                    "z": z_height,
                    },
                ]
                series.extend(fraction_series)
                z_height += 1
            
            # ---- Save Threshold Data ----
            metadata_row = metadata_table[metadata_table["Scenario"] == scenario].iloc[0]
            file_name = metadata_row["File"]
            sim_id = metadata_row["ID"]
            feather_name = "timeline_logbook.feather" if lobby_selected == "all" else f"timeline_logbook_{lobby_selected}.feather"
            if "Temporary Filing Directory" in st.session_state and dataframe_updated:
                base_dir = st.session_state["Temporary Filing Directory"] 
                save_dir = os.path.join(base_dir, file_name, sim_id, run_selected, feather_name)
                df_timeline.to_feather(save_dir)
                print(f"Updated Dataframe: {os.path.join(file_name, sim_id, run_selected, feather_name)}")
            else: print("Dataframe remain the same")

        # ---- Get x y Range ----
        time_series_list = []
        y_series_list = []
        for scenario, content in data_dict.items():
            time_series_list.append(content["timeline"][lobby_selected]["compiled"]["time"])
            ql = content["timeline"][lobby_selected]["compiled"]["queue_length"]
            y_series_list.append(ql)
        series_joint = pd.concat(time_series_list)
        time_range = [math.ceil(float(series_joint.min())), math.ceil(float(series_joint.max()))]
        timestamps = list(range(time_range[0], time_range[1]))
        timestamps = [gu.seconds_to_hhmmss(s) for s in timestamps]
        # ---- Get Y Range ----
        y_series_joint = pd.concat(y_series_list)
        y_max = math.ceil(float(y_series_joint.max()))
        # ---- Get Legend Data ----
        legend_data = ["Queue Length"] + [f"{threshold}s+" for threshold in thresholds]
        legend_mask = {
            series_name : True if (i == 0) or (i <= 4 and display_threshold) else False 
            for i, series_name in enumerate(legend_data)
            }
        # ---- Add Reference Line ----
        if y_ref is not None:
            series.append({
                "name": "Y Reference Line",
                "type": "line",
                "data": [y_ref] * len(timestamps),
                "symbol": "none",
                "lineStyle": {"color": "red", "width": 0.5, "type": "dashed"},
                "emphasis": {"disabled": True},
                "tooltip": {"show": False},
                "z": z_height,
            })
        if x_ref is not None:
            series.append({
                "name": "X Reference Line",
                "type": "line",
                "data": [[x_ref,0],[x_ref,y_max]],
                "symbol": "none",
                "lineStyle": {"color": "red", "width": 0.5, "type": "dashed"},
                "emphasis": {"disabled": True},
                "tooltip": {"show": False},
                "z": z_height,
            })
        # ---- Construct Options ----
        option = {
            "title": {"show": False, "text": "Passenger Queue Length Timeline", },#"left": "center"
            "toolbox": {
                "feature": {
                "dataZoom": {"yAxisIndex": 'none'},
                "restore": {},
                "saveAsImage": {}
                }
            },
            "grid": {"show": False, "left": 40, "right": 40, "top": 40},
            "tooltip": {
                "trigger": "axis",
                "position": [50, 5],
                "axisPointer": {"type": "cross"},
                "snap": True,
                "z": 25,
            },
            "legend": {
                "show": True,
                "top": 5,
                "data": legend_data,
                "selected": legend_mask,
                "itemStyle": {"color": "rgb(200,200,200)", "borderColor": "rgb(200,200,200)"}
                },
            "xAxis": {
                "type": "category",
                "data": timestamps,
                "z": 2,
                },
            "yAxis": {
                "type": "value",
                "min": 0,
                "max": int(y_max*1.2),
                "z": 2,
                },
            "series": series,
            "dataZoom": [
                {"type": 'inside'},
                {
                "type": 'slider',
                "showDataShadow": True,
                "handleIcon":'path://M10.7,11.9v-1.3H9.3v1.3c-4.9,0.3-8.8,4.4-8.8,9.4c0,5,3.9,9.1,8.8,9.4v1.3h1.3v-1.3c4.9-0.3,8.8-4.4,8.8-9.4C19.5,16.3,15.6,12.2,10.7,11.9z M13.3,24.4H6.7V23h6.6V24.4z M13.3,19.6H6.7v-1.4h6.6V19.6z',
                "handleSize": '80%'
                },
                {
                "type": 'slider',
                "orient": 'vertical',
                "filterMode": "none",
                "showDataShadow": False,
                "handleIcon":'path://M10.7,11.9v-1.3H9.3v1.3c-4.9,0.3-8.8,4.4-8.8,9.4c0,5,3.9,9.1,8.8,9.4v1.3h1.3v-1.3c4.9-0.3,8.8-4.4,8.8-9.4C19.5,16.3,15.6,12.2,10.7,11.9z M13.3,24.4H6.7V23h6.6V24.4z M13.3,19.6H6.7v-1.4h6.6V19.6z',
                "handleSize": '80%'
                },
            ],
        }

        # ---- On Click ---- 
        events = {
            "click": "function(params) { console.log(params.name); return params.name }",
        }
        return st_echarts(option, width="100%", height="500px", key=key, renderer="svg", events=events,)

    def render_wait_time_chart(scenario_data:dict, run_selected, lobby_selected, y_ref = None) -> None:
        '''
        Note: x axis (time) is currently as 'category' instead of value due to a bug with stack area chart in echart
        '''
        # ---- Unpack Scenario Data ----
        data_collections = scenario_data["data_collections"]
        color_dict = scenario_data["color_dict"]
        display_threshold = True if len(data_collections.keys()) < 2 else False
        
        # ---- Construct Series Data ----
        series_dict = {}
        data_dict = dbp.sort_data_collections(data_collections)
        for i, (scenario, content) in enumerate(data_dict.items()):
            color = color_dict[scenario]
            series_dict[scenario] = {}

            # ---- Add Domain Series ----
            timeline_compiled = content["timeline"][lobby_selected]["compiled"]
            domain_min_series = timeline_compiled['mean_wait_time_register'].apply(lambda lst: min(lst) if len(lst)!= 0 else 0)
            domain_diff_series = timeline_compiled['mean_wait_time_register'].apply(lambda lst: max(lst) - min(lst) if len(lst)!= 0 else 0)
            opacity = 1.0 if display_threshold else 0.75
            series_dict[scenario]["domain"] = [
                {
                "name": "Domain",
                "data": round(domain_min_series.astype(float),1).tolist(),
                "type": "line",
                "stack": f"domain_{i}",
                "symbol": "none",
                "lineStyle": {"color": color, "width": 0.25, "type": "dashed", "opacity": 1 if display_threshold else 0}, 
                "areaStyle": {"color": "transparent"},
                "emphasis": {"disabled": True, "focus": "none"},
                "visualMap": False,
                "hoverLink": False,
                "tooltip": {"show": False},
                "z": 1,
                },
                {
                "name": "Domain",
                "data": round(domain_diff_series.astype(float),1).tolist(),
                "type": "line",
                "stack": f"domain_{i}",
                "symbol": "none",
                "lineStyle": {"color": color, "width": 0.25, "type": "dashed", "opacity": 1 if display_threshold else 0},
                "areaStyle": {"color": gu.make_color_brighter(color,0.8), "opacity": opacity},
                "emphasis": {"disabled": True, "focus": "none"},
                "hoverLink": False,
                "tooltip": {"show": False},
                "z": 1,
                },
                ]
            series_dict[scenario]["domain_ref"] = [
                {
                "name": "Low Average",
                "data": round(domain_min_series.astype(float),1).tolist(),
                "type": "line",
                "symbol": "none",
                "lineStyle": {"opacity": 0},#{"color": color, "width": 0.5},
                "itemStyle": {"color": gu.make_color_brighter(color,0.8)}, # This controls the symbol in tooltip panel
                "emphasis": {"disabled": True},
                "z": 0,
                },
                {
                "name": "High Average",
                "data": round((domain_min_series+domain_diff_series).astype(float),1).tolist(),
                "type": "line",
                "symbol": "none",
                "lineStyle": {"opacity": 0}, #"opacity": 0
                "itemStyle": {"color": gu.make_color_brighter(color,0.8)}, # This controls the symbol in tooltip panel
                "emphasis": {"disabled": True},
                "z": 0,
                },
                ] if display_threshold else []
            
            # ---- Add Average Series ----
            series_dict[scenario]["average"] = {}
            for run_id, df_timeline in content["timeline"][lobby_selected].items():
                # ---- Add Average Series ----
                line_data = df_timeline["mean_wait_time"].astype(float).round(1).tolist()
                # ---- Add Series ----
                series_dict[scenario]["average"][run_id] = {
                    "name": "Average",
                    "data": line_data,
                    "type": "line",
                    "symbol": "none",
                    "lineStyle": {"color": color, "width": 2.0},
                    "itemStyle": {"color": color}, # This controls the symbol in tooltip panel
                    "emphasis": {"focus": None, "scale": True,},
                    "z": 2,
                }
            
            # ---- Add Scatter Series ----
            series_dict[scenario]["scatter"] = {}
            for run_id, df_passenger in content["passenger"][lobby_selected].items():
                if run_id == "compiled": continue
                scatter_data = [[str(gu.seconds_to_hhmmss(int(x))), round(float(y),1)] for x, y in zip(df_passenger["tbc_wait_time_end"], df_passenger["wait_time"])]
                series_dict[scenario]["scatter"][run_id] = {
                    "name": "Individual Wait Time",
                    "type": "scatter",
                    "data": scatter_data,
                    "symbol": "rect",
                    "symbolSize": 4,
                    "itemStyle": {"opacity": 0.5, "color": color},
                    "blendMode": 'source-over',
                    "large": True,
                    "largeThreshold": 200,
                    "emphasis": {"focus": None, "scale": True},
                    "tooltip": {"show": False},
                    "z": 2,
                }

        # ---- Get Time Range ----
        time_series_list = []
        for scenario, content in data_dict.items():
            time_series_list.append(content["timeline"][lobby_selected]["compiled"]["time"])
        series_joint = pd.concat(time_series_list)
        time_range = [math.ceil(float(series_joint.min())), math.ceil(float(series_joint.max()))]
        timestamps = list(range(time_range[0], time_range[1]))
        timestamps = [gu.seconds_to_hhmmss(s) for s in timestamps]
        
        # ---- Get Y Range ----
        y_series_list = []
        for scenario, content in data_dict.items():
            for run_id in content["passenger"][lobby_selected].keys():
                wait_time_end = content["passenger"][lobby_selected][run_id]["wait_time"]
                y_series_list.append(wait_time_end)
        y_series_joint = pd.concat(y_series_list)
        y_max = math.ceil(float(y_series_joint.max()))

        # ---- Add Global Average Line Series ----
        for i, (scenario, content) in enumerate(data_dict.items()):
            color = color_dict[scenario]
            series_dict[scenario]["global_average"] = {}
            wt_register = []
            for run_id, df_passenger in content["passenger"][lobby_selected].items():
                if run_id == "compiled": continue
                wt_register.append(df_passenger["wait_time"])
                mean_wt = df_passenger["wait_time"].mean()
                ref_line_data = [mean_wt]*(time_range[1]-time_range[0])
                series_dict[scenario]["global_average"][run_id] = {
                    "name": "Global Average",
                    "type": "line",
                    "data": ref_line_data,
                    "type": "line",
                    "symbol": "none",
                    "lineStyle": {"color": color, "width": 2.4, "type": [10, 5],},
                    "emphasis": {"disabled": True},
                    "tooltip": {"show": False},
                    "z": 1,
                }
            
            mean_wt = pd.concat(wt_register).mean()
            ref_line_data = [mean_wt]*(time_range[1]-time_range[0])
            series_dict[scenario]["global_average"]["compiled"] = {
                "name": "Global Average",
                "type": "line",
                "data": ref_line_data,
                "type": "line",
                "symbol": "none",
                "lineStyle": {"color": color, "width": 2.4, "type": [10, 5],},
                "emphasis": {"disabled": True},
                "tooltip": {"show": False},
                "z": 1,
            }
        
        # ---- Construct Series ----
        series = []
        domain_series = []
        domain_ref_series = []
        scatter_series = []
        average_series = []
        global_average_series = []
        for scenario, content in series_dict.items():
            domain_series.extend(content["domain"])
            average_series.append(content["average"][run_selected])
            domain_ref_series.extend(content["domain_ref"])
            global_average_series.append(content["global_average"][run_selected])
            if run_selected != "compiled":
                scatter_series.append(content["scatter"][run_selected])
            else:
                scatter_series.extend(list(content["scatter"].values()))
        series.extend(average_series)
        series.extend(domain_series)
        series.extend(domain_ref_series)
        series.extend(scatter_series)
        series.extend(global_average_series)
        
        # ---- Add Reference Line ----
        if y_ref is not None:
            series.append({
                "name": "Reference Line",
                "type": "line",
                "data": [y_ref] * len(timestamps),
                "symbol": "none",
                "lineStyle": {"color": "red", "width": 0.5, "type": "dashed"},
                "emphasis": {"disabled": True},
                "tooltip": {"show": False},
                "z": 25,
            })
        # ---- Construct Options ----
        options = {
            "title": {"show": False, "text": "Passenger Wait Time Timeline", },#"left": "center"
            "toolbox": {
                "feature": {
                "dataZoom": {"yAxisIndex": 'none'},
                "restore": {},
                "saveAsImage": {}
                }
            },
            "grid": {"show": False, "top":40, "left": 40, "right": 40},
            "tooltip": {
                "trigger": "axis",
                "axisPointer": {"type": "cross"},
                "position":[50,5],
                # Disable formatter to trigger default panel #"formatter": "{a}: {b} seconds",
                "snap": True,
                "z": 25,
            },
            "legend": {
                "show": True,
                "top": 5,
                "data": [
                    {"name": "Domain", "icon": "rect",},
                    {"name": "Average",},
                    {"name": "Individual Wait Time", "icon": "circle", },
                    {"name": "Global Average",},
                    ],
                "selected": {
                    "Domain": True,  
                    "Average": True,
                    "Global Average": display_threshold,     
                    "Individual Wait Time": False,
                    },
                "itemStyle": {"color": "rgb(200,200,200)"},
                },
            "xAxis": {
                "type": "category",
                "data": timestamps,
                "z": 2,
                },
            "yAxis": {
                "type": "value",
                "min": 0,
                "max": y_max,
                "z": 2,
                },
            "series": series,
            "dataZoom": [
                {"type": 'inside'},
                {
                "type": 'slider', # "height": 40, # "bottom": 20,
                "showDataShadow": True,
                "handleIcon":'path://M10.7,11.9v-1.3H9.3v1.3c-4.9,0.3-8.8,4.4-8.8,9.4c0,5,3.9,9.1,8.8,9.4v1.3h1.3v-1.3c4.9-0.3,8.8-4.4,8.8-9.4C19.5,16.3,15.6,12.2,10.7,11.9z M13.3,24.4H6.7V23h6.6V24.4z M13.3,19.6H6.7v-1.4h6.6V19.6z',
                "handleSize": '80%'
                },
                {
                "type": 'slider',
                "orient": 'vertical',
                "filterMode": "none",
                "showDataShadow": False,
                "handleIcon":'path://M10.7,11.9v-1.3H9.3v1.3c-4.9,0.3-8.8,4.4-8.8,9.4c0,5,3.9,9.1,8.8,9.4v1.3h1.3v-1.3c4.9-0.3,8.8-4.4,8.8-9.4C19.5,16.3,15.6,12.2,10.7,11.9z M13.3,24.4H6.7V23h6.6V24.4z M13.3,19.6H6.7v-1.4h6.6V19.6z',
                "handleSize": '80%'
                },
            ],
        }
        st_echarts(options = options, width="100%", height="500px", key="wait_time_chart", renderer="svg")
    
    # ---- Render Time Chart V2 ----
    def render_queue_length_chart_v2(scenario_data:dict, color_dict:dict, metadata_table:pd.DataFrame, run_selected, lobby_selected, y_ref = None, x_ref = None, enable_click = False, chart_height = 500, margin_side = 40, margin_top = 40, key = "ql_chart") -> None:
        # ---- Unpack Scenario Data ----
        display_threshold = True if len(scenario_data.keys()) < 2 else False
        thresholds = [60, 120, 180, 240]
        # ---- Construct Series Data ----
        series = []
        z_height = 0
        for i, (scenario, content) in enumerate(scenario_data.items()):
            color = color_dict[scenario]
            brightness = 0.8
            # ---- Add Domain Series ----
            df_timeline = content["timeline"][lobby_selected][run_selected]
            ql_data = df_timeline["queue_length"]
            peak_value = int(ql_data.max())
            peak_time = gu.seconds_to_hhmmss(int(df_timeline["time"][ql_data.idxmax()]))
            ql_series = [
                {
                "name": "Queue Length",
                "data": ql_data.astype(int).tolist(),
                "type": "line",
                "symbol": "none",
                "lineStyle": {"opacity": 1, "color": color, "width": 0.5, },
                "areaStyle": {"color": gu.make_color_brighter(color,brightness), "opacity": 1},
                "emphasis": {"disabled": True, "focus": "none"},
                "tooltip": {"show": False},
                "z": z_height,
                "markPoint": {
                    "data": [{
                        "name": "Peak",
                        "coord": [peak_time, peak_value],
                        "value": f"Peak: {peak_value}",
                        "label": {
                            "show": True,
                            "formatter": f"Peak: {peak_value}",
                            "fontSize": 12,
                            "color": "rgb(255,255,255)",
                            "fontWeight": "bold",
                            "align": "center",
                        },
                        "symbol": "rect",
                        "symbolSize": [80, 18],
                        "itemStyle": {"color": color}
                    }],
                    "symbolOffset": [0, -14], 
                    }
                },
                {
                "name": "Queue Length",
                "data": ql_data.astype(int).tolist(),
                "type": "line",
                "itemStyle": {"color": gu.make_color_brighter(color,brightness)},
                "lineStyle": {"opacity": 0},
                "emphasis": {"disabled": True, "focus": "none"},
                "tooltip": {"show": True},
                "z": z_height,
                },
            ]
            series.extend(ql_series)
            z_height += 1
            # ---- Fetch Threshold Data ----
            dataframe_updated = False
            for k, threshold in enumerate(thresholds):
                # ---- Check for Threshold Data ----
                if f"threshold_{threshold}" not in list(df_timeline.columns):
                    if run_selected == "compiled" or lobby_selected == "all":
                        fraction_data = df_timeline['wait_time_register'].apply(lambda lst: sum(x > threshold for x in lst)/len(lst) if len(lst) > 0 else 0)
                        theshold_data = round(ql_data * fraction_data, 1)
                    else:
                        theshold_data = df_timeline['wait_time_register'].apply(lambda lst: sum(x > threshold for x in lst) if len(lst) > 0 else 0)
                    df_timeline[f"threshold_{threshold}"] = theshold_data
                    dataframe_updated = True
                    print( f"threshold data updated for {scenario}: {threshold} s")
                theshold_data = df_timeline[f"threshold_{threshold}"]           
                # ---- Construct Threshold Series ----     
                area_color = gu.make_color_brighter(color, brightness - (brightness*((k+1)/len(thresholds))))
                fraction_series = [
                    {
                    "name": f"{threshold}s+",
                    "data": theshold_data.astype(int).tolist(),
                    "type": "line",
                    "symbol": "none",
                    "itemStyle": {"opacity": 0},
                    "lineStyle": {"color": color, "width": 0.5, "type": "dashed"},
                    "areaStyle": {"color": area_color, "opacity": 1},
                    "emphasis": {"disabled": True, "focus": "none"},
                    "tooltip": {"show": False},
                    "z": z_height,
                    },
                    {
                    "name": f"{threshold}s+",
                    "data": theshold_data.astype(int).tolist(),
                    "type": "line",
                    "itemStyle": {"color": area_color, "opacity": 1},
                    "lineStyle": {"opacity": 0},
                    "emphasis": {"disabled": True, "focus": "none"},
                    "tooltip": {"show": True if display_threshold and theshold_data.sum() > 0 else False},
                    "z": z_height,
                    },
                ]
                series.extend(fraction_series)
                z_height += 1
            
            # ---- Save Threshold Data ----
            metadata_row = metadata_table[metadata_table["Scenario"] == scenario].iloc[0]
            file_name = metadata_row["File"]
            sim_id = metadata_row["ID"]
            feather_name = "timeline_logbook.feather" if lobby_selected == "all" else f"timeline_logbook_{lobby_selected}.feather"
            if "Temporary Filing Directory" in st.session_state and dataframe_updated:
                base_dir = st.session_state["Temporary Filing Directory"] 
                save_dir = os.path.join(base_dir, file_name, sim_id, run_selected, feather_name)
                df_timeline.to_feather(save_dir)
                print(f"Updated Dataframe: {os.path.join(file_name, sim_id, run_selected, feather_name)}")
            else: print("Dataframe remain the same")

        # ---- Get x y Range ----
        time_series_list = []
        y_series_list = []
        for scenario, content in scenario_data.items():
            time_series_list.append(content["timeline"][lobby_selected]["compiled"]["time"])
            ql = content["timeline"][lobby_selected]["compiled"]["queue_length"]
            y_series_list.append(ql)
        series_joint = pd.concat(time_series_list)
        time_range = [math.ceil(float(series_joint.min())), math.ceil(float(series_joint.max()))]
        timestamps = list(range(time_range[0], time_range[1]))
        timestamps = [gu.seconds_to_hhmmss(s) for s in timestamps]
        # ---- Get Y Range ----
        y_series_joint = pd.concat(y_series_list)
        y_max = math.ceil(float(y_series_joint.max()))
        # ---- Get Legend Data ----
        legend_data = ["Queue Length"] + [f"{threshold}s+" for threshold in thresholds]
        legend_mask = {
            series_name : True if (i == 0) or (i <= 4 and display_threshold) else False 
            for i, series_name in enumerate(legend_data)
            }
        # ---- Add Reference Line ----
        if y_ref is not None:
            series.append({
                "name": "Y Reference Line",
                "type": "line",
                "data": [y_ref] * len(timestamps),
                "symbol": "none",
                "lineStyle": {"color": "red", "width": 0.5, "type": "dashed"},
                "emphasis": {"disabled": True},
                "tooltip": {"show": False},
                "z": z_height,
            })
        if x_ref is not None:
            series.append({
                "name": "X Reference Line",
                "type": "line",
                "data": [[x_ref,0],[x_ref,y_max]],
                "symbol": "none",
                "lineStyle": {"color": "red", "width": 0.5, "type": "dashed"},
                "emphasis": {"disabled": True},
                "tooltip": {"show": False},
                "z": z_height,
            })
        # ---- Construct Options ----
        option = {
            "title": {"show": False, "text": "Passenger Queue Length Timeline", },#"left": "center"
            "toolbox": {
                "feature": {
                "dataZoom": {"yAxisIndex": 'none'},
                "restore": {},
                "saveAsImage": {}
                }
            },
            "grid": {"show": False, "left": margin_side, "right": margin_side, "top": margin_top},
            "tooltip": {
                "trigger": "axis",
                "position": [50, 5],
                "axisPointer": {"type": "cross"},
                "snap": True,
                "z": 25,
            },
            "legend": {
                "show": True,
                "top": 5,
                "data": legend_data,
                "selected": legend_mask,
                "itemStyle": {"color": "rgb(200,200,200)", "borderColor": "rgb(200,200,200)"}
                },
            "xAxis": {
                "type": "category",
                "data": timestamps,
                "z": 2,
                },
            "yAxis": {
                "type": "value",
                "min": 0,
                "max": int(y_max*1.2),
                "z": 2,
                },
            "series": series,
            "dataZoom": [
                {"type": 'inside'},
                {
                "type": 'slider',
                "showDataShadow": True,
                "handleIcon":'path://M10.7,11.9v-1.3H9.3v1.3c-4.9,0.3-8.8,4.4-8.8,9.4c0,5,3.9,9.1,8.8,9.4v1.3h1.3v-1.3c4.9-0.3,8.8-4.4,8.8-9.4C19.5,16.3,15.6,12.2,10.7,11.9z M13.3,24.4H6.7V23h6.6V24.4z M13.3,19.6H6.7v-1.4h6.6V19.6z',
                "handleSize": '80%'
                },
                {
                "type": 'slider',
                "orient": 'vertical',
                "filterMode": "none",
                "showDataShadow": False,
                "handleIcon":'path://M10.7,11.9v-1.3H9.3v1.3c-4.9,0.3-8.8,4.4-8.8,9.4c0,5,3.9,9.1,8.8,9.4v1.3h1.3v-1.3c4.9-0.3,8.8-4.4,8.8-9.4C19.5,16.3,15.6,12.2,10.7,11.9z M13.3,24.4H6.7V23h6.6V24.4z M13.3,19.6H6.7v-1.4h6.6V19.6z',
                "handleSize": '80%'
                },
            ],
        }

        # ---- On Click ---- 
        events = {
            "click": "function(params) { console.log(params.name); return params.name }",
        }
        return st_echarts(option, width="100%", height=chart_height, key=key, renderer="svg", events= events if enable_click else {"click": ""},)
    
    def render_wait_time_chart_v2(scenario_data:dict, color_dict:dict, run_selected, lobby_selected, y_ref = None, x_ref = None, chart_height = 300, margin_side = 40, margin_top = 40, key=f"wt_chart") -> None:
        '''
        Note: x axis (time) is currently as 'category' instead of value due to a bug with stack area chart in echart
        '''
        display_threshold = True if len(scenario_data.keys()) < 2 else False

        # ---- Construct Series Data ----
        series_dict = {}
        for i, (scenario, content) in enumerate(scenario_data.items()):
            color = color_dict[scenario]
            series_dict[scenario] = {}

            # ---- Add Domain Series ----
            timeline_compiled = content["timeline"][lobby_selected]["compiled"]
            domain_min_series = timeline_compiled['mean_wait_time_register'].apply(lambda lst: min(lst) if len(lst)!= 0 else 0)
            domain_diff_series = timeline_compiled['mean_wait_time_register'].apply(lambda lst: max(lst) - min(lst) if len(lst)!= 0 else 0)
            opacity = 1.0 if display_threshold else 0.75
            series_dict[scenario]["domain"] = [
                {
                "name": "Domain",
                "data": round(domain_min_series.astype(float),1).tolist(),
                "type": "line",
                "stack": f"domain_{i}",
                "symbol": "none",
                "lineStyle": {"color": color, "width": 0.25, "type": "dashed", "opacity": 1 if display_threshold else 0}, 
                "areaStyle": {"color": "transparent"},
                "emphasis": {"disabled": True, "focus": "none"},
                "visualMap": False,
                "hoverLink": False,
                "tooltip": {"show": False},
                "z": 1,
                },
                {
                "name": "Domain",
                "data": round(domain_diff_series.astype(float),1).tolist(),
                "type": "line",
                "stack": f"domain_{i}",
                "symbol": "none",
                "lineStyle": {"color": color, "width": 0.25, "type": "dashed", "opacity": 1 if display_threshold else 0},
                "areaStyle": {"color": gu.make_color_brighter(color,0.8), "opacity": opacity},
                "emphasis": {"disabled": True, "focus": "none"},
                "hoverLink": False,
                "tooltip": {"show": False},
                "z": 1,
                },
                ]
            series_dict[scenario]["domain_ref"] = [
                {
                "name": "Low Average",
                "data": round(domain_min_series.astype(float),1).tolist(),
                "type": "line",
                "symbol": "none",
                "lineStyle": {"opacity": 0},#{"color": color, "width": 0.5},
                "itemStyle": {"color": gu.make_color_brighter(color,0.8)}, # This controls the symbol in tooltip panel
                "emphasis": {"disabled": True},
                "z": 0,
                },
                {
                "name": "High Average",
                "data": round((domain_min_series+domain_diff_series).astype(float),1).tolist(),
                "type": "line",
                "symbol": "none",
                "lineStyle": {"opacity": 0}, #"opacity": 0
                "itemStyle": {"color": gu.make_color_brighter(color,0.8)}, # This controls the symbol in tooltip panel
                "emphasis": {"disabled": True},
                "z": 0,
                },
                ] if display_threshold else []
            
            # ---- Add Average Series ----
            series_dict[scenario]["average"] = {}
            for run_id, df_timeline in content["timeline"][lobby_selected].items():
                # ---- Add Average Series ----
                line_data = df_timeline["mean_wait_time"].astype(float).round(1).tolist()
                # ---- Add Series ----
                series_dict[scenario]["average"][run_id] = {
                    "name": "Average",
                    "data": line_data,
                    "type": "line",
                    "symbol": "none",
                    "lineStyle": {"color": color, "width": 2.0},
                    "itemStyle": {"color": color}, # This controls the symbol in tooltip panel
                    "emphasis": {"focus": None, "scale": True,},
                    "z": 2,
                }
            
            # ---- Add Scatter Series ----
            series_dict[scenario]["scatter"] = {}
            for run_id, df_passenger in content["passenger"][lobby_selected].items():
                if run_id == "compiled": continue
                scatter_data = [[str(gu.seconds_to_hhmmss(int(x))), round(float(y),1)] for x, y in zip(df_passenger["tbc_wait_time_end"], df_passenger["wait_time"])]
                series_dict[scenario]["scatter"][run_id] = {
                    "name": "Individual Wait Time",
                    "type": "scatter",
                    "data": scatter_data,
                    "symbol": "rect",
                    "symbolSize": 4,
                    "itemStyle": {"opacity": 0.5, "color": color},
                    "blendMode": 'source-over',
                    "large": True,
                    "largeThreshold": 200,
                    "emphasis": {"focus": None, "scale": True},
                    "tooltip": {"show": False},
                    "z": 2,
                }

        # ---- Get Time Range ----
        time_series_list = []
        for scenario, content in scenario_data.items():
            time_series_list.append(content["timeline"][lobby_selected]["compiled"]["time"])
        series_joint = pd.concat(time_series_list)
        time_range = [math.ceil(float(series_joint.min())), math.ceil(float(series_joint.max()))]
        timestamps = list(range(time_range[0], time_range[1]))
        timestamps = [gu.seconds_to_hhmmss(s) for s in timestamps]
        
        # ---- Get Y Range ----
        y_series_list = []
        for scenario, content in scenario_data.items():
            for run_id in content["passenger"][lobby_selected].keys():
                wait_time_end = content["passenger"][lobby_selected][run_id]["wait_time"]
                y_series_list.append(wait_time_end)
        y_series_joint = pd.concat(y_series_list)
        y_max = math.ceil(float(y_series_joint.max()))

        # ---- Add Global Average Line Series ----
        for i, (scenario, content) in enumerate(scenario_data.items()):
            color = color_dict[scenario]
            series_dict[scenario]["global_average"] = {}
            wt_register = []
            for run_id, df_passenger in content["passenger"][lobby_selected].items():
                if run_id == "compiled": continue
                wt_register.append(df_passenger["wait_time"])
                mean_wt = df_passenger["wait_time"].mean()
                ref_line_data = [mean_wt]*(time_range[1]-time_range[0])
                series_dict[scenario]["global_average"][run_id] = {
                    "name": "Global Average",
                    "type": "line",
                    "data": ref_line_data,
                    "type": "line",
                    "symbol": "none",
                    "lineStyle": {"color": color, "width": 2.4, "type": [10, 5],},
                    "emphasis": {"disabled": True},
                    "tooltip": {"show": False},
                    "z": 1,
                }
            
            mean_wt = pd.concat(wt_register).mean()
            ref_line_data = [mean_wt]*(time_range[1]-time_range[0])
            series_dict[scenario]["global_average"]["compiled"] = {
                "name": "Global Average",
                "type": "line",
                "data": ref_line_data,
                "type": "line",
                "symbol": "none",
                "lineStyle": {"color": color, "width": 2.4, "type": [10, 5],},
                "emphasis": {"disabled": True},
                "tooltip": {"show": False},
                "z": 1,
            }
        
        # ---- Construct Series ----
        series = []
        domain_series = []
        domain_ref_series = []
        scatter_series = []
        average_series = []
        global_average_series = []
        for scenario, content in series_dict.items():
            domain_series.extend(content["domain"])
            average_series.append(content["average"][run_selected])
            domain_ref_series.extend(content["domain_ref"])
            global_average_series.append(content["global_average"][run_selected])
            if run_selected != "compiled":
                scatter_series.append(content["scatter"][run_selected])
            else:
                scatter_series.extend(list(content["scatter"].values()))
        series.extend(average_series)
        series.extend(domain_series)
        series.extend(domain_ref_series)
        series.extend(scatter_series)
        series.extend(global_average_series)
        
        # ---- Add Reference Line ----
        if y_ref is not None:
            series.append({
                "name": "Reference Line",
                "type": "line",
                "data": [y_ref] * len(timestamps),
                "symbol": "none",
                "lineStyle": {"color": "red", "width": 0.5, "type": "dashed"},
                "emphasis": {"disabled": True},
                "tooltip": {"show": False},
                "z": 25,
            })
        # ---- Construct Options ----
        options = {
            "title": {"show": False, "text": "Passenger Wait Time Timeline", },#"left": "center"
            "toolbox": {
                "feature": {
                "dataZoom": {"yAxisIndex": 'none'},
                "restore": {},
                "saveAsImage": {}
                }
            },
            "grid": {"show": False, "top":margin_top, "left": margin_side, "right": margin_side},
            "tooltip": {
                "trigger": "axis",
                "axisPointer": {"type": "cross"},
                "position":[50,5],
                # Disable formatter to trigger default panel #"formatter": "{a}: {b} seconds",
                "snap": True,
                "z": 25,
            },
            "legend": {
                "show": True,
                "top": 5,
                "data": [
                    {"name": "Domain", "icon": "rect",},
                    {"name": "Average",},
                    {"name": "Individual Wait Time", "icon": "circle", },
                    {"name": "Global Average",},
                    ],
                "selected": {
                    "Domain": True,  
                    "Average": True,
                    "Global Average": display_threshold,     
                    "Individual Wait Time": False,
                    },
                "itemStyle": {"color": "rgb(200,200,200)"},
                },
            "xAxis": {
                "type": "category",
                "data": timestamps,
                "z": 2,
                },
            "yAxis": {
                "type": "value",
                "min": 0,
                "max": y_max,
                "z": 2,
                },
            "series": series,
            "dataZoom": [
                {"type": 'inside'},
                {
                "type": 'slider', # "height": 40, # "bottom": 20,
                "showDataShadow": True,
                "handleIcon":'path://M10.7,11.9v-1.3H9.3v1.3c-4.9,0.3-8.8,4.4-8.8,9.4c0,5,3.9,9.1,8.8,9.4v1.3h1.3v-1.3c4.9-0.3,8.8-4.4,8.8-9.4C19.5,16.3,15.6,12.2,10.7,11.9z M13.3,24.4H6.7V23h6.6V24.4z M13.3,19.6H6.7v-1.4h6.6V19.6z',
                "handleSize": '80%'
                },
                {
                "type": 'slider',
                "orient": 'vertical',
                "filterMode": "none",
                "showDataShadow": False,
                "handleIcon":'path://M10.7,11.9v-1.3H9.3v1.3c-4.9,0.3-8.8,4.4-8.8,9.4c0,5,3.9,9.1,8.8,9.4v1.3h1.3v-1.3c4.9-0.3,8.8-4.4,8.8-9.4C19.5,16.3,15.6,12.2,10.7,11.9z M13.3,24.4H6.7V23h6.6V24.4z M13.3,19.6H6.7v-1.4h6.6V19.6z',
                "handleSize": '80%'
                },
            ],
        }
        st_echarts(options = options, width="100%", height=chart_height, key=key, renderer="svg")
    
    #------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # ---- Render Pictorial Bar ----
    def render_pictorial_scatter(df_set: dict[str: pd.DataFrame], time: list, theme_colors: list):
        svg_person = "path://m62.096 8.5859c-5.208 0-9.424 4.2191-9.424 9.4261 0.001 5.203 4.217 9.424 9.424 9.424 5.202 0 9.422-4.221 9.422-9.424 0-5.208-4.22-9.4261-9.422-9.4261zm-10.41 21.268c-6.672 0-12.131 5.407-12.131 12.07v29.23c0 2.275 1.791 4.123 4.07 4.123 2.28 0 4.127-1.846 4.127-4.123v-26.355h2.102s0.048 68.811 0.048 73.331c0 3.05 2.478 5.53 5.532 5.53 3.052 0 5.525-2.48 5.525-5.53v-42.581h2.27v42.581c0 3.05 2.473 5.53 5.531 5.53 3.054 0 5.549-2.48 5.549-5.53v-73.331h2.127v26.355c0 2.275 1.85 4.123 4.126 4.123 2.28 0 4.073-1.846 4.073-4.123v-29.23c0-6.663-5.463-12.07-12.129-12.07h-20.82z"
        pathSymbols = {"person": svg_person}

        y_category_set = []
        total_row_count = 0
        data_entries = []
        queue_length_max_per_category = []
        max_row_count = 12 #math.ceil(15/len(df_set.items()))#math.ceil(5000/max(100,max_value))
        for i, (key, df) in enumerate(df_set.items()):
            y_category_set.append(key)
            ql_max = int(df['queue_length'].max())
            queue_length_max_per_category.append(ql_max)
        queue_length_max_per_category.sort(reverse=False)
        for ql in queue_length_max_per_category:
            if i == 0: continue
            elif i == 1: max_row_count = max(5, max_row_count - round(ql / 40))
            else: max_row_count = max(7, max_row_count- round(ql / 80))
            #st.write(round(ql_max / 100))
        #max_row_count = max(8, max_row_count) 
        #st.write(queue_length_max_per_category)
        #st.write(max_row_count)

        max_value = max(queue_length_max_per_category)
        max_per_row = round(math.ceil((max_value/max_row_count)/5)*5)
        max_per_row = max(40, max_per_row)
        symbol_with = 18 * (40/max_per_row)
        symbol_height = 40 * (40/max_per_row)

        for i, (key, df) in enumerate(df_set.items()):
            
            try: queue_length = int(df.loc[df['time'] == time[i], 'queue_length'].iloc[0])
            except: queue_length = 0
            row_count = int(min(max_row_count, int(math.ceil(queue_length / max_per_row))))
            total_row_count += row_count
            remaining_value = queue_length
            value_per_row = 0

            vertical_offset = (row_count/2)* -110 # Used in % string
            for r in range(row_count):
                if remaining_value <= max_per_row:
                    value_per_row = remaining_value
                    remaining_value = 0
                else:
                    value_per_row = max_per_row
                    remaining_value -= max_per_row
                
                vertical_offset += 110
                for c in range(1, value_per_row + 1):
                    coordinate = [c, i] # c is the x coodinate (person count), i is y coordinate (scenario index)
                    if r == row_count-1 and c == value_per_row:
                        data_entries.append({
                            "value": coordinate,
                            "itemStyle": {"color": theme_colors[i]},
                            "symbolOffset": ['0%', f"{vertical_offset}%"], 
                            "sum": queue_length,
                            "label": {
                                "normal": {
                                    "show": True,
                                    "position": "right",
                                    "offset": [10, 0],
                                    "textStyle": {"fontSize": 14},
                                    "formatter": f"{queue_length}",
                                }}
                            })
                    else:
                        data_entries.append({"value": coordinate, "itemStyle": {"color": theme_colors[i]},"symbolOffset": ['0%', f"{vertical_offset}%"],"sum": queue_length,})
        
        option = {
            #"title": {"text": "Queue Length in Lobby"},
            #"legend": {"data": ["Total Queue Length"], "itemStyle": {"color": theme_colors[i]}},
            "tooltip": {
                "trigger": "axis",
                "axisPointer": {"type": "none"},
                "formatter": "{b}: Queue in Lobby",
                "snap": True,
            },
            "grid": {
                "show": True,
                "borderColor": "black", 
                "borderWidth": 0, 
                "left": 40,
                "right": 40,
                "top": 0,
                "bottom": 0,
                "containLabel": False,
                "left": 100
            },
            "yAxis": {
                "type": "category",
                "data": y_category_set,
                "inverse": True,
                "axisLine": {"show": False},
                "axisTick": {"show": False},
                "axisLabel": {"margin": 30, "fontSize": 14},
                #"axisPointer": {"label": {"show": True, "margin": 30}},
            },
            "xAxis": {
                "type": "value",
                "min": 0,
                "max": max_per_row,
                "splitLine": {"show": False},
                "axisLabel": {"show": False},
                "axisTick": {"show": False},
                "axisLine": {"show": False},
            },
            "series": {
                "name": f"Total Queue Length",
                "type": "scatter",
                "label": {
                    "normal": {
                        "show": False,
                        "position": "right",
                        "offset": [10, 0],
                        "textStyle": {"fontSize": 16},
                    }
                },
                "symbol": pathSymbols["person"],
                "symbolSize": [symbol_with, symbol_height],
                "data": data_entries,
            },
        }

        #------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
        # ---- On Click ----
        # events = {
        #     "click": "function(params) { console.log(params.name); return params.name }",
        #     #"dblclick": "function(params) { return [params.type, params.name, params.value] }",
        # }
        events = {
            "click": "function(params) { return 'clicked'}"
        }
        #------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
        # ---- Render Chart ----
        #st.write(f"{total_row_count * 65}px")#int(total_row_count * 65)
        return st_echarts(option, width=1200, height= 500, key=f"echarts-r", events=events,)
    #------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # ---- Render Lobby ----
    def render_lobby(passengers:list, room_x:float, room_y:float, room_x_max = None, room_y_max = None, theme_color:str = "black", chart_width = 500, margin_top = 40, margin_side = 40, margin_bottom = 40, key="echart-lobby-scatter-plot"):
        
        svg_path = os.path.dirname(os.path.abspath(__file__)) + r"\resource\img\person_plan_typical_svg\person_plan_typical-02.svg"
        svg_person = gu.get_path_from_svg(svg_path)
        svg_ellipse = "path://M 0,-225 A 300,225 0 1,0 0,225 A 300,225 0 1,0 0,-225" #m20,10 a10,5 0 1,0 20,0 a10,5 0 1,0 -20,0"

        if room_x_max is None: room_x_max = room_x
        if room_y_max is None: room_y_max = room_y
        scale_factor = (chart_width-margin_side) / room_x_max

        queue_length = len(passengers)
        area_pp = room_x*room_y/queue_length if queue_length > 0 else room_x*room_y
        occupied_radius = math.sqrt((area_pp)/ math.pi)
        occupied_diameter = max(0.6, occupied_radius)*2

        points = gu.get_points(queue_length, width=room_x, length=room_y, min_distance= [0.54, 0.4, 0.3, 0.2], max_attempts = 40)
        scatter_person_data = []
        scatter_ellipse_data = []
        scatter_bubble_data = []
        for x, y in points:
            angle_rotate = random.randint(0, 359)
            scatter_person_data.append({"value": [x, y], "symbol": svg_person, "symbolSize": [0.54*scale_factor,0.3*scale_factor], "symbolRotate": angle_rotate})
            scatter_ellipse_data.append({"value": [x, y], "symbol": svg_ellipse, "symbolSize": [0.6*scale_factor,0.45*scale_factor], "symbolRotate": angle_rotate})
            scatter_bubble_data.append({"value": [x, y], "symbol": "circle", "symbolSize": [occupied_diameter*scale_factor,occupied_diameter*scale_factor]})

        option = {
            #"title": {"text": "Queue Length in Lobby"},
            "legend": {
                "show": True,
                "top": margin_top*0.25, 
                "right": margin_side,#"right", 
                #"orient": "horizontal",
                "itemWidth": 0.25*scale_factor,
                "itemHeight": 0.25*scale_factor,
                "data": [
                    {"name":"Minimum Body Area", "icon": svg_ellipse},
                    {"name":f"Passenger x {queue_length}", "icon": svg_person},
                    {"name":"1.2m Personal Space", "icon": "circle"},
                    ], 
                },
            "tooltip": {"show": False},
            "grid": {
                "show": True,
                #"borderColor": "black", 
                "borderWidth": 0, 
                "left": margin_side,
                "right": margin_side,
                "top": margin_top,
                "bottom": margin_bottom,
                #"containLabel": True, "left": 20
            },
            "yAxis": {
                "type": "value",
                #"name": f"{room_y} m",
                #"nameLocation": "center",
                #"nameGap": 10,
                "min": 0,
                "max": room_y_max,
                "interal": 1,
                "minInterval": 1,
                "maxInterval": 1,
                #"inverse": True,
                "axisLine": {"show": False},
                "axisTick": {"show": True},
                "axisLabel": {"show": True},#{"margin": 30, "fontSize": 14},
                "axisPointer": {"label": {"show": True, "margin": 30}},
                "splitLine": {
                    "show": True,
                    #"interval": "function(index, value){return value % 1 === 0;}",
                    "lineStyle": {"color": "#eee","width": 1,"type": "solid"} #"rgb(200,200,200)"
        }
            },
            "xAxis": {
                "type": "value",
                #"name": f"{room_x} m",
                #"nameLocation": "center",
                #"nameGap": 10,
                "min": 0,
                "max": room_x_max,
                "interal": 1,
                "minInterval": 1,
                "maxInterval": 1,
                "axisLabel": {"show": True},
                "axisTick": {"show": True},
                "axisLine": {"show": False},
                "axisPointer": {"label": {"show": True, "margin": 30}},
                "splitLine": {
                    "show": True,
                    #"interval": "function(index, value){return value % 1 === 0;}",
                    "lineStyle": {"color": "#eee","width": 1,"type": "solid"}
                }
            },
            "series": [
                
                {
                    "name": "Minimum Body Area",
                    "type": "scatter",
                    "itemStyle": {
                        "color": "transparent",# gu.add_alpha(theme_color, 0.1)
                        "borderColor": theme_color,
                        "borderWidth": 1,
                        "borderType": "dashed",
                    },
                    #"symbolSize": [0.5*scale_factor,0.5*scale_factor],
                    "data": scatter_ellipse_data,
                },
                {
                    "name": f"Passenger x {queue_length}",
                    "type": "scatter",
                    "itemStyle": {
                        "color": theme_color,
                        #"opacity": 1.0,
                        "borderColor": "white",
                        "borderWidth": 1,
                        },
                    #"symbolSize": [0.5*scale_factor,0.5*scale_factor],
                    "data": scatter_person_data,
                },
                {
                    "name": "1.2m Personal Space",
                    "type": "scatter",
                    "itemStyle": {
                        "color": gu.add_alpha(theme_color, 0.1),# 
                        #"borderColor": theme_color,
                        #"borderWidth": 1,
                        #"borderType": "dashed",
                    },
                    "emphasis": {"disabled": True},
                    "tooltip": {"show": False},
                    #"symbolSize": [0.5*scale_factor,0.5*scale_factor],
                    "data": scatter_bubble_data,
                },
                {
                    "name": f"Lobby Area", #: {room_x * room_y:.2f} m²
                    "type": "scatter",
                    "label": {"normal": {"show": False}},
                    "itemStyle": {"symbol": "square", "color": theme_color},
                    "data": [],
                    "markLine": {
                        "silent": True,
                        "lineStyle": {
                            "color": gu.add_alpha(theme_color, 0.2),
                            "width": 4,
                            "type": "solid"
                        },
                        "symbol": ["none", "none"],
                        "data": [
                            # Four sides of a rectangle: left, right, top, bottom
                            [{"xAxis": 0, "yAxis": 0}, {"xAxis": room_x, "yAxis": 0}],      # bottom
                            [{"xAxis": 0, "yAxis": room_y}, {"xAxis": room_x, "yAxis": room_y}],  # top
                            [{"xAxis": 0, "yAxis": 0}, {"xAxis": 0, "yAxis": room_y}],      # left
                            [{"xAxis": room_x, "yAxis": 0}, {"xAxis": room_x, "yAxis": room_y}],  # right
                        ],
                        "animation": False,
                    }
                },
            ]
        }
        #------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

        st_echarts(option, width=chart_width, height=scale_factor*room_y_max + margin_top + margin_bottom, key=key)#height=f"{room_y*scale_factor}px",
    
    def render_lobby_plan(queue_length:int, room_x:float, room_y:float, room_x_max = None, room_y_max = None, theme_color:str = "black", chart_width = 500, key="echart-lobby-scatter-plot"):
        margin_top = 40
        margin_side = 40
        margin_bottom = 40
        svg_path = os.path.dirname(os.path.abspath(__file__)) + r"\resource\img\person_plan_typical_svg\person_plan_typical-02.svg"
        svg_person = gu.get_path_from_svg(svg_path)
        svg_ellipse = "path://M 0,-225 A 300,225 0 1,0 0,225 A 300,225 0 1,0 0,-225" #m20,10 a10,5 0 1,0 20,0 a10,5 0 1,0 -20,0"

        if room_x_max is None: room_x_max = room_x
        if room_y_max is None: room_y_max = room_y
        scale_factor = (chart_width-margin_side) / room_x_max

        area_pp = room_x*room_y/queue_length if queue_length > 0 else room_x*room_y
        occupied_radius = math.sqrt((area_pp)/ math.pi)
        occupied_diameter = max(0.6, occupied_radius)*2

        points = gu.get_points(queue_length, width=room_x, length=room_y, min_distance= [0.54, 0.4, 0.3, 0.2], max_attempts = 40)
        scatter_person_data = []
        scatter_ellipse_data = []
        scatter_bubble_data = []
        for x, y in points:
            angle_rotate = random.randint(0, 359)
            scatter_person_data.append({"value": [x, y], "symbol": svg_person, "symbolSize": [0.54*scale_factor,0.3*scale_factor], "symbolRotate": angle_rotate})
            scatter_ellipse_data.append({"value": [x, y], "symbol": svg_ellipse, "symbolSize": [0.6*scale_factor,0.45*scale_factor], "symbolRotate": angle_rotate})
            scatter_bubble_data.append({"value": [x, y], "symbol": "circle", "symbolSize": [occupied_diameter*scale_factor,occupied_diameter*scale_factor]})

        option = {
            "legend": {
                "show": True,
                "top": margin_top*0.25, 
                "right": margin_side,#"right", 
                #"orient": "horizontal",
                "itemWidth": 0.25*scale_factor,
                "itemHeight": 0.25*scale_factor,
                "data": [
                    {"name":"Minimum Body Area", "icon": svg_ellipse},
                    {"name":f"Passenger x {queue_length}", "icon": svg_person},
                    {"name":"1.2m Personal Space", "icon": "circle"},
                    ], 
                },
            "tooltip": {
                "trigger": "axis",
                "axisPointer": {"type": "shadow"},#
                "formatter": {
                    "function": """
                        function(params) {
                            var count = params.length;
                            var stripValue = params[0].value[0];
                            var min = Math.floor(stripValue);
                            var max = min + 1;
                            return 'x ∈ [' + min + ', ' + max + ')<br/>People in strip: <b>' + count + '</b>';
                        }
                    """
                }
            },
            "grid": {
                "show": True,
                "borderWidth": 0, 
                "left": margin_side,
                "right": margin_side,
                "top": margin_top,
                "bottom": margin_bottom,
            },
            "yAxis": {
                "type": "value",
                "min": 0,
                "max": room_y_max,
                "interal": 1,
                "minInterval": 1,
                "maxInterval": 1,
                "axisLine": {"show": False},
                "axisTick": {"show": True},
                "axisLabel": {"show": True},#{"margin": 30, "fontSize": 14},
                "axisPointer": {"label": {"show": True, "margin": 30}},
                "splitLine": {
                    "show": True,
                    "lineStyle": {"color": "#eee","width": 1,"type": "solid"} #"rgb(200,200,200)"
        }
            },
            "xAxis": {
                "type": "value",
                "min": 0,
                "max": room_x_max,
                "interal": 1,
                "minInterval": 1,
                "maxInterval": 1,
                "axisLabel": {"show": True},
                "axisTick": {"show": True},
                "axisLine": {"show": False},
                "axisPointer": {"label": {"show": True, "margin": 30}},
                "splitLine": {
                    "show": True,
                    "lineStyle": {"color": "#eee","width": 1,"type": "solid"}
                }
            },
            "series": [
                
                {
                    "name": "Minimum Body Area",
                    "type": "scatter",
                    "itemStyle": {
                        "color": "transparent",# gu.add_alpha(theme_color, 0.1)
                        "borderColor": theme_color,
                        "borderWidth": 1,
                        "borderType": "dashed",
                    },
                    "data": scatter_ellipse_data,
                },
                {
                    "name": f"Passenger x {queue_length}",
                    "type": "scatter",
                    "itemStyle": {
                        "color": theme_color,
                        "borderColor": "white",
                        "borderWidth": 1,
                        },
                    "data": scatter_person_data,
                },
                {
                    "name": "1.2m Personal Space",
                    "type": "scatter",
                    "itemStyle": {
                        "color": gu.add_alpha(theme_color, 0.1),# 
                    },
                    "data": scatter_bubble_data,
                },
                {
                    "name": f"Lobby Area",
                    "type": "scatter",
                    "label": {"normal": {"show": False}},
                    "itemStyle": {"symbol": "square", "color": theme_color},
                    "data": [],
                    "markLine": {
                        "silent": True,
                        "lineStyle": {
                            "color": gu.add_alpha(theme_color, 0.2),
                            "width": 4,
                            "type": "solid"
                        },
                        "symbol": ["none", "none"],
                        "data": [
                            # Four sides of a rectangle: left, right, top, bottom
                            [{"xAxis": 0, "yAxis": 0}, {"xAxis": room_x, "yAxis": 0}],      # bottom
                            [{"xAxis": 0, "yAxis": room_y}, {"xAxis": room_x, "yAxis": room_y}],  # top
                            [{"xAxis": 0, "yAxis": 0}, {"xAxis": 0, "yAxis": room_y}],      # left
                            [{"xAxis": room_x, "yAxis": 0}, {"xAxis": room_x, "yAxis": room_y}],  # right
                        ],
                        "animation": False,
                    }
                },
            ]
        }
        #------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

        st_echarts(option, width=chart_width, height=scale_factor*room_y_max + margin_top + margin_bottom, key=key)#height=f"{room_y*scale_factor}px",

    def grading_gauge(icon_size = 200, input_grade="A", theme_color = "rgb(64, 158, 255)", key="echarts-grading-gauge"):
        highlight_color = theme_color
        normal_color = "#E0E0E0"
        grades = ['F', 'E', 'D', 'C', 'B', 'A']
        grade_index = grades.index(input_grade)
        data = [
            { "value": 1, "name": 'F', "itemStyle": {"color": highlight_color if 0 <= grade_index else normal_color}, "label": {"show": False if 1 == grade_index else False, "color": "rgb(255,255,255)", "formatter": "{b}" }},
            { "value": 1, "name": 'E', "itemStyle": {"color": highlight_color if 1 <= grade_index else normal_color}, "label": {"show": False if 2 == grade_index else False, "color": "rgb(255,255,255)", "formatter": "{b}" }},
            { "value": 1, "name": 'D', "itemStyle": {"color": highlight_color if 2 <= grade_index else normal_color}, "label": {"show": False if 3 == grade_index else False, "color": "rgb(255,255,255)", "formatter": "{b}" }},
            { "value": 1, "name": 'C', "itemStyle": {"color": highlight_color if 3 <= grade_index else normal_color}, "label": {"show": False if 4 == grade_index else False, "color": "rgb(255,255,255)", "formatter": "{b}" }},
            { "value": 1, "name": 'B', "itemStyle": {"color": highlight_color if 4 <= grade_index else normal_color}, "label": {"show": False if 5 == grade_index else False, "color": "rgb(255,255,255)", "formatter": "{b}" }},
            { "value": 1, "name": 'A', "itemStyle": {"color": highlight_color if 5 <= grade_index else normal_color}, "label": {"show": False if 6 == grade_index else False, "color": "rgb(255,255,255)", "formatter": "{b}" }},
            { "value": 1, "name": '', "itemStyle": {"color": "none", "boarderColor": "none"}, "emphasis": {"disabled": True}, "select": {"disabled": True}, "label": {"show": False},"tooltip": {"show": False}},
            { "value": 1, "name": '', "itemStyle": {"color": "none", "boarderColor": "none"}, "emphasis": {"disabled": True}, "select": {"disabled": True}, "label": {"show": False},"tooltip": {"show": False}},
            { "value": 1, "name": '', "itemStyle": {"color": "none", "boarderColor": "none"}, "emphasis": {"disabled": True}, "select": {"disabled": True}, "label": {"show": False},"tooltip": {"show": False}},
            { "value": 1, "name": '', "itemStyle": {"color": "none", "boarderColor": "none"}, "emphasis": {"disabled": True}, "select": {"disabled": True}, "label": {"show": False},"tooltip": {"show": False}},
            { "value": 1, "name": '', "itemStyle": {"color": "none", "boarderColor": "none"}, "emphasis": {"disabled": True}, "select": {"disabled": True}, "label": {"show": False},"tooltip": {"show": False}},
            { "value": 1, "name": '', "itemStyle": {"color": "none", "boarderColor": "none"}, "emphasis": {"disabled": True}, "select": {"disabled": True}, "label": {"show": False},"tooltip": {"show": False}},

        ] 
        option = {
            "title": {
                "text": "Grading",
                "left": "center",
                "top": "47%",
                "textStyle": {
                    "fontSize": 48,
                    "fontWeight": "bold",
                    "color": "theme_color"
                }
            },
            "series": [
                {
                    "name": 'Grading',
                    "type": "pie",
                    "radius": ["80%", "140%"],
                    "center": ["50%", "75%"],
                    "startAngle": 180,
                    "endAngle": 360,
                    "label": {
                        "show": False,
                        "position": "inside",
                        "color": gu.add_alpha("rgb(255,255,255)",0.5),
                        "formatter": "{b}",
                        "fontWeight": "bold",
                        "fontFamily": "sans-serif",
                        "fontSize": 14,
                    },
                    "itemStyle": {
                        "borderColor": "#fff",
                        "borderWidth": 4,
                        "borderRadius": 4,
                    },
                    "data": data
                }
            ],
            "graphic": [
                {
                    "type": "text",
                    "left": "center",
                    "top": "50%",  # visually center in the half-donut
                    "style": {
                        "text": str(input_grade),
                        "font": f"bold {icon_size* 60/200}px sans-serif", #60 was initial default
                        "fill": theme_color,
                        "textAlign": "center",
                        "textVerticalAlign": "middle"
                    }
                }
            ],
            "tooltip": {"show": True, "trigger": "item", "formatter": "{b}"},
        }
        st_echarts(options=option, height=icon_size*0.5, width="100%", key=key)
    #------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # ---- Render Person Icon ----
    def render_person_plan_icon(icon_size:int = 400, value=20, area = 200, color = "rgb(64, 158, 255)", margin:int = 0, key = "echart-person-plan-icon"):
        svg_path = os.path.dirname(os.path.abspath(__file__)) + r"\resource\img\person_plan_typical_svg\person_plan_typical-02.svg"
        svg_person = gu.get_path_from_svg(svg_path)
        svg_ellipse = "path://M 0,-225 A 300,225 0 1,0 0,225 A 300,225 0 1,0 0,-225" #m20,10 a10,5 0 1,0 20,0 a10,5 0 1,0 -20,0"
        personal_space_ref = {
            "Desirable": 1/0.4,
            "Comfortable": 1/1.0,
            "Dense": 1/2.0,
            "Crowded": 1/3.0,
            "Crushed": 1/4.7,
        }
        #A=pi*r1*r2,
        
        max_radius = 0.6 #math.sqrt(personal_space_ref["Desirable"]/ math.pi)
        scale_factor = ((float(icon_size) - float(margin)*2)) / (max_radius*2)
        w_body_ellipse = 0.6 * scale_factor
        h_body_ellipse = 0.45 * scale_factor
        w_person = 0.54 * scale_factor
        h_person = 0.3 * scale_factor

        ps_area = area/value if value > 0 else area # Personal Space Area
        ps_radius = math.sqrt((ps_area)/ math.pi)
        ps_buble_size = min(max_radius, ps_radius)*2*scale_factor #Scale Factor is for symbols to be pixel size adjusted 
        #ps_buble_size = max_radius*2*scale_factor

        option = {
            #"title": {"text": "Queue Length in Lobby"},
            "legend": {"show": False},
            "tooltip": {"show": False, "trigger": "item", "formatter": "{a}"},
            "animation": False,
            "grid": {"show": False,"left": margin,"right": margin,"top": margin,"bottom": margin,},
            "yAxis": {
                "type": "value",
                "min": -max_radius,
                "max": max_radius,
                "axisLine": {"show": False},
                "axisTick": {"show": False},
                "axisLabel": {"show": False},#{"margin": 30, "fontSize": 14},
                #"axisPointer": {"label": {"show": False, "margin": 30}},
                "splitLine": {"show": False,}
                },
            "xAxis": {
                "type": "value",
                "min": -max_radius,
                "max": max_radius,
                "axisLabel": {"show": False},
                "axisTick": {"show": False},
                "axisLine": {"show": False},
                #"axisPointer": {"label": {"show": False, "margin": 30}},
                "splitLine": {"show": False,}
                },
            "series": [
                {
                    "name": "1.2m Personal Space",
                    "type": "scatter",
                    "symbol": "circle",
                    "itemStyle": {"color": gu.add_alpha(color, 0.1),},
                    "symbolSize": ps_buble_size,
                    "emphasis": {"scale": False,"disabled": True, "animation": False  },
                    "data": [[0, 0]], 
                },
                {
                    "name": "Minimum Body Area",
                    "type": "scatter",
                    "symbol": svg_ellipse,
                    "itemStyle": {
                        "color": "transparent", #gu.make_color_brighter(color, 0.8),
                        "borderColor": color,
                        "borderWidth": 1.4,
                        "borderType": "dashed",
                    },
                    "symbolSize": [w_body_ellipse, h_body_ellipse],
                    "emphasis": {"scale": True, "disabled": False, "animation": True  },
                    "data": [[0, 0]], 
                },
                {
                    "name": "Passenger",
                    "type": "scatter",
                    "label": {
                        "normal": {
                            "show": True,
                            "position": "right",
                            "offset": [-w_body_ellipse*1.4, h_person*1.2],
                            "textStyle": {"fontSize": 16},
                            "lineHeight": 20,
                            "formatter": (f"{int(value)}p\n{((area)/float(value)):.1f}m²/p") if value > 0 else "0p\n",#0m²/p
                        }
                    },
                    "symbol": svg_person,
                    "itemStyle": {
                        "color": color, #"white", #gu.make_color_brighter(color, 0.8),
                        "borderColor": "white",
                        "borderWidth": 2,
                    },
                    "symbolSize": [w_person, h_person],
                    "emphasis": {
                        #"itemStyle": {"shadowBlur": 40, "shadowOffsetX": 0, "shadowOffsetY": 0, "shadowColor": "rgba(200,200,200,0.6)"}, #
                        "scale": True,
                        "disabled": False, 
                        "animation": True  
                    },
                    "data": [[0, 0]], 
                },
            ],
        }
        st_echarts(options=option, width="100%", height="150%", key=key)

    def render_person_icon(icon_size = 200, value=20, area = 200, color = "#409EFF", key = "echart-svg-icon"):
        svg_person = "path://m62.096 8.5859c-5.208 0-9.424 4.2191-9.424 9.4261 0.001 5.203 4.217 9.424 9.424 9.424 5.202 0 9.422-4.221 9.422-9.424 0-5.208-4.22-9.4261-9.422-9.4261zm-10.41 21.268c-6.672 0-12.131 5.407-12.131 12.07v29.23c0 2.275 1.791 4.123 4.07 4.123 2.28 0 4.127-1.846 4.127-4.123v-26.355h2.102s0.048 68.811 0.048 73.331c0 3.05 2.478 5.53 5.532 5.53 3.052 0 5.525-2.48 5.525-5.53v-42.581h2.27v42.581c0 3.05 2.473 5.53 5.531 5.53 3.054 0 5.549-2.48 5.549-5.53v-73.331h2.127v26.355c0 2.275 1.85 4.123 4.126 4.123 2.28 0 4.073-1.846 4.073-4.123v-29.23c0-6.663-5.463-12.07-12.129-12.07h-20.82z"
        #svg_person = "M50,0 A50,50 0 1,0 50.0001,0 Z"
        max_size = 38
        scale_factor = icon_size / max_size
        w = 15 * scale_factor
        h = 38 * scale_factor
        option = {
            #"title": {"text": "Queue Length in Lobby"},
            "legend": {"show": False},
            "tooltip": {"show": False},
            "animation": False,
            "grid": {
                "show": False,
                "left": 40,
                "right": 40,
                "top": 40,
                "bottom": 40,
                },
            "yAxis": {
                "type": "value",
                #"name": f"{room_y} m",
                #"nameLocation": "center",
                #"nameGap": 10,
                "min": 0,
                "max": icon_size,
                "axisLine": {"show": False},
                "axisTick": {"show": False},
                "axisLabel": {"show": False},#{"margin": 30, "fontSize": 14},
                "axisPointer": {"label": {"show": False, "margin": 30}},
                "splitLine": {
                    "show": False,
        }
            },
            "xAxis": {
                "type": "value",
                #"name": f"{room_x} m",
                #"nameLocation": "center",
                #"nameGap": 10,
                "min": 0,
                "max": icon_size,
                "axisLabel": {"show": False},
                "axisTick": {"show": False},
                "axisLine": {"show": False},
                "axisPointer": {"label": {"show": False, "margin": 30}},
                "splitLine": {
                    "show": False,
                }
            },
            "series": [
                {
                    "name": "Person",
                    "type": "scatter",
                    "label": {
                        "normal": {
                            "show": True,
                            "position": "right",
                            "offset": [10, h/5],
                            "textStyle": {"fontSize": 18},
                            "lineHeight": 28,
                            "formatter": (f"{int(value)}p\n{((area)/float(value)):.1f}m²/p") if value > 0 else "0p\n",#0m²/p
                        }
                    },
                    "symbol": svg_person,
                    "itemStyle": {
                        "color": color, 
                    },
                    "symbolSize": [w, h],
                    "emphasis": {
                        "scale": False,
                        "disabled": True,   # disables emphasis effect entirely
                        "animation": False  # disables emphasis animation
                    },
                    "data": [[w/5, h/2]], 
                },
            ],
            # "graphic":[
            #     {
            #         "type": "text",
            #         "left": "center",
            #         "top": "middle",
            #         "z": 100,
            #         "style": {
            #             "text": f"{value}",
            #             "font": "30px open-sans",
            #             "fill": "white",
            #             "textAlign": "center",
            #             "textVerticalAlign": "middle"
            #         },
            #     },
            # ]
        }
        st_echarts(options=option, height=icon_size, width= icon_size*(w/h)+icon_size*1.8, key=key)
    #------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # ---- Render Radar ----
    def render_radar(df_snapshot = pd.DataFrame(), theme_colors:dict = {}, chart_size = 500, key = "echarts-radar"):
        
        keys = ["Lifts", "Queue", "Wait Time", "Transit Time", "Travel Time"]#df_snapshot.columns.tolist()
        indicators = []
        for key in keys:
            if key == "Scenario":continue
            try:
                df_snapshot[key] = df_snapshot[key].astype(float)
                range_max = df_snapshot[key].max()
                indicators.append({"name": key, "max": math.ceil(range_max)})
                #st.write(math.ceil(range_max))
            except:
                continue
        data = []
        for index, row in df_snapshot.iterrows():
            scenario_name = row['Scenario']
            data.append({
                "value": row[["Lifts", "Queue", "Wait Time", "Transit Time", "Travel Time"]].to_list(),
                "name": scenario_name,
                "itemStyle": {"color": theme_colors.get(scenario_name)}
            })
        option = {
            "title": {
                "text": 'KPIs',
                "show": False,
            },
            "legend": {
                "show": False,
                "data": df_snapshot["Scenario"].tolist(),
            },
            "radar": {
                "shape": 'circle',
                "indicator": indicators
            },
            "series": [
                {
                "name": 'KPIs Tracking',
                "type": 'radar',
                "data": data,
                }
            ]
        }
        st_echarts(option, height=chart_size, width="100%", key=key)
    
    #------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # ---- Render Parrallel Plot ----
    def render_parallel_plot(df_summary:pd.DataFrame, chart_size = 400, key = "echarts-parallel", highlight_row_indices = []):
        df = df_summary[[
            "File",
            "Lifts",
            "Longest Queue",
            "Average Wait Time",
            "Average Transit Time",
            "Average Travel Time",
            "Max Wait Time",
            "Max Transit Time",
            "Max Travel Time",
        ]].copy()
        keys = df.columns.tolist()
        parallel_axis = []
        for i, key in enumerate(keys):
            if isinstance(df[key].iloc[0], list): continue
            try:
                df[key] = df[key].astype(float)
                parallel_axis.append({"dim": i, "name": key})
            except:
                try: 
                    df[key] = df[key].astype(str)
                    parallel_axis.append({"dim": i, "name": key, "type": "category", "data": df[key].unique().tolist()})
                except:
                    continue

        data = []
        data_hightlight = []
        for i, row in df.iterrows():
            row_data = [row[key] for key in keys]
            data.append({
                    "value": row_data,
                    "lineStyle": {
                        "color": "#ccc",  # Default line color
                        "width": 1,  # Adjust line weight
                        "opacity": 1.0  # Adjust line opacity
                    }
                })
            if i in highlight_row_indices: 
                data_hightlight.append({
                    "value": row_data,
                    "lineStyle": {
                        "color": "rgb(51, 204, 255)",#"rgb(204, 51, 0)" "rgb(51, 204, 255)"
                        "width": 2,  # Adjust line weight
                        "opacity": 1.0  # Adjust line opacity
                    }
                })

        option = {
            "parallelAxis": parallel_axis,
            "series": [
                {
                "type": 'parallel',
                "lineStyle": {
                "width": 4
                },
                "data": data,
                },
                {
                "type": 'parallel',
                "lineStyle": {
                "width": 4
                },
                "data": data_hightlight,
                },
            ],
        }
        
        st_echarts(options=option, height=chart_size, width="100%", key=key)  