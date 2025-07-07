import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from data_utilities import dataframe_functions as dff
from general_utilities import general_utilities as gu


class plot_functions:
    @staticmethod

    # ---- Plot Queue Length -----
    def plot_queue_length(fig = go.Figure(), df_timeline = pd.DataFrame(), theme_color = 'rgb(51, 204, 255)', enable_threshold = False):
        # ---- Base Plot ----
        fig.add_trace(go.Scatter(
            name='Queue Length (Persons)',
            x=df_timeline['time'], 
            y=df_timeline['queue_length'], 
            mode="lines", 
            line=dict(color = theme_color, width=1.4), #dash='2px,1px'
            #mode="markers", 
            #marker=dict(size=4, color = theme_color, opacity=0.0, line_width = 0.2),#
            fill = "tozeroy",
            fillcolor= gu.add_alpha(gu.make_color_brighter(theme_color, 0.6), 1.0), #f"rgba({theme_color[4:-1]}, 0.4)", #"rgba(255, 0, 0, 0.1)",
        ))
        # ---- Format Plot ----
        fig.update_layout(
            height= 500,
            template="plotly_white", 
            margin=dict(l=100, r=100, t=40, b=100),
            # Range Slider
            xaxis=dict(rangeslider=dict(visible = True, thickness=0.1)),
            # Legend
            legend=dict(
            orientation = "h",
            x=0.5,  # Horizontal position of the legend (0 to 1, where 0 is far left and 1 is far right)
            y=1,    # Vertical position of the legend (0 to 1, where 0 is bottom and 1 is top)
            xanchor="center",  # Horizontal alignment of legend relative to `x`
            yanchor="bottom"      # Vertical alignment of legend relative to `y`
            ),
        )
        fig.update_xaxes(dtick=200, autorange = True, tickformat='%H:%M', title='Time')
        if enable_threshold:
            plot_functions.plot_queue_threshold(fig, df_timeline['wait_time_register'].apply(lambda lst: sorted(lst)))

    def plot_queue_threshold(fig, series, threshold_step = 30):
        set_start = len(fig.data)-1
        x_series = pd.Series(fig.data[-1].x)
        y_series = pd.Series(fig.data[-1].y)    
        if "lines" in fig.data[-1].mode:
            theme_color = fig.data[-1].line.color
        else:
            theme_color = fig.data[-1].marker.color

        # ---- Set Threshold Range ----
        thresholds = []
        for t in range(0, 120, threshold_step):
            thresholds.append(t) 
        # ---- Base Plot ----
        for i, threshold in enumerate(thresholds):
            # Convert the series of lists into a 2D numpy array (object dtype if lists have different lengths)
            arr = series.apply(np.array)
            # Get mask of valid (non-empty) lists
            non_empty_mask = arr.apply(len) > 0
            # Only process non-empty lists
            fraction_series = np.zeros(len(series))
            fraction_series[non_empty_mask] = arr[non_empty_mask].apply(lambda x: np.mean(np.array(x) > threshold))
            # ---- Below is orginal code ----
            #fraction_series = series.apply(lambda lst: sum(x > threshold for x in lst)/len(lst) if len(lst) > 0 else 0)
            fig.add_trace(go.Scatter(
                name=f'Persons Waiting Longer than {threshold}s',
                x=x_series, 
                y=fraction_series*y_series, 
                mode="lines", 
                line=dict(color = gu.make_color_brighter(theme_color, 0.0), width=1.0, dash='4px,2px'), #dash='2px,1px'
                fill = "tozeroy",
                fillcolor= gu.add_alpha(gu.make_color_brighter(theme_color, 0.5), 1.0), #f"rgba({theme_color[4:-1]}, 0.4)",
                visible = False, #True if show else 'legendonly' # Hide this trace by default
                showlegend = False
            ))
        fig.data[set_start].visible = None  # Base trace always visible
        fig.data[set_start+3].visible = True
        fig.data[set_start+3].showlegend = True

        # ---- Set Slider ---- #THERE IS S SIMPLER VERSION OF THIS WITHOUT APPLYING SLIDER TO MULTIPLE TRACES
        steps = []
        set_count = round(set_start/len(thresholds))+1
        for i, threshold in enumerate(thresholds):
            visible_index_set = []
            for set_index in range(0, set_count):
                visible_index = [True] + [False]*len(thresholds)
                visible_index[i+1] = True  # Only show the ith threshold trace
                visible_index_set.extend(visible_index)  # Combine list (cannot use append as it would create nested lists)
            step = dict(
                method="update",
                args=[{"visible": visible_index_set, "showlegend": visible_index_set},
                    {"title": f"Persons Waiting Longer than: {threshold}s"}],
                label=f"{threshold}s"  # layout attribute
            )
            steps.append(step)
            
        sliders = [dict(
            active= 2, #Account for base trace
            currentvalue={"prefix": "Show Persons Waiting Longer than: "},
            pad={"t": 100},
            steps=steps
        )]
        fig.update_layout(sliders=sliders)

    # ---- Plot Wait Time -----    
    def plot_wait_time(fig, df_timeline, theme_color = 'rgb(51, 204, 255)', show_highiest_plot = False):
        # ---- Base Plot ----
        fig.add_trace(go.Scatter(
            name='Mean Wait Time',
            x=df_timeline['time'], 
            y=df_timeline['mean_wait_time'], 
            mode="lines", #"lines+markers"
            line=dict(color=theme_color, width=2),
            #fill = "tozeroy",
            #fillcolor= gu.add_alpha(gu.make_color_brighter(theme_color, 0.5), 1.0)#f"rgba({theme_color[4:-1]}, 1.0)",
            #marker=dict(size=4, color=theme_color, opacity=1.0)
        ))


        fig.add_trace(go.Scatter(
            name='Highiest Wait Time',
            x=df_timeline['time'], 
            y=df_timeline['max_wait_time'], 
            mode="lines", #"lines+markers"
            line=dict(color=theme_color, width=0.5, dash='dot'),
            #marker=dict(size=4, color=theme_color, opacity=1.0)
            visible = None if show_highiest_plot else 'legendonly' # Hide this trace by default
        ))

        # ---- Format Plot ----
        fig.update_xaxes(
            dtick=200,  # Tick interval in milliseconds (e.g., 3600 seconds = 1 hour)
            autorange = True, 
            tickformat='%H:%M',  # Format for time display
            title='Time'  # Optional: Add an x-axis title
        )
        fig.update_yaxes(
            #autorange = False,
            #range=[df_timeline['average_wait_time'].min(), df_timeline['average_wait_time'].max()+10],
            title='Mean Wait Time(s)'
        )  
        fig.update_layout(
            height= 500,
            #title="                           Passenger Queue Length over Time",
            template="plotly_white",  # Optional: Set a template
            margin=dict(l=100, r=100, t=40, b=100),
            # Range Slider
            xaxis=dict(rangeslider=dict(visible = True, thickness=0.1)),
            # Legend
            legend=dict(
                orientation = "h",
                x=0.5,  # Horizontal position of the legend (0 to 1, where 0 is far left and 1 is far right)
                y=1,    # Vertical position of the legend (0 to 1, where 0 is bottom and 1 is top)
                xanchor="center",  # Horizontal alignment of legend relative to `x`
                yanchor="bottom"      # Vertical alignment of legend relative to `y`
            ),
        )
        
    # ---- Highlight Highiest -----
    def highlight_highiest(fig):
        x_series = pd.Series(fig.data[-1].x)
        y_series = pd.Series(fig.data[-1].y)
        if "lines" in fig.data[-1].mode:
            theme_color = fig.data[-1].line.color
        else:
            theme_color = fig.data[-1].marker.color
        # ---- Highlight the highest data point ----
        max_y = y_series.max()
        df_fig = pd.DataFrame({'x': x_series, 'y': y_series})
        max_x = df_fig.loc[df_fig['y'].idxmax(), 'x']

        # ---- Annotate Highiest ----
        fig.add_annotation(
            x=max_x,
            y=max_y,
            text=f" Peak: <b>{max_y:.0f}</b> ",
            showarrow=True,
            arrowhead=0,
            arrowcolor="white",
            arrowsize=3,
            arrowwidth=0.2,
            #arrowdash="dash",
            ax=0,
            ay=-24,
            font=dict(color="white", size=14),
            bgcolor=theme_color,
            bordercolor="black",
            borderwidth=0.2,
        )

    def highlight_highiest_all(fig): #theme_color = 'rgb(51, 204, 255)'
        # ---- Highlight the highest data point ----
        for i in range (0, len(fig.data)):
            if fig.data[i].visible != None: continue #"legendonly"
            y_series_index = i
            if "lines" in fig.data[y_series_index].mode:
                theme_color = fig.data[y_series_index].line.color
            else:
                theme_color = fig.data[y_series_index].marker.color
            x_series = pd.Series(fig.data[y_series_index].x)
            y_series = pd.Series(fig.data[y_series_index].y)
            max_y = y_series.max()
            df_fig = pd.DataFrame({'x': x_series, 'y': y_series})
            max_x = df_fig.loc[df_fig['y'].idxmax(), 'x']

            # ---- Annotate Highiest ----
            fig.add_annotation(
                x=max_x,
                y=max_y,
                text=f" Peak: <b>{max_y:.0f}</b> ",
                showarrow=True,
                arrowhead=0,
                arrowcolor="white",
                arrowsize=3,
                arrowwidth=0.2,
                #arrowdash="dash",
                ax=0,
                ay=-24,
                font=dict(color="white", size=14),
                bgcolor=theme_color,
                bordercolor="black",
                borderwidth=0.2,
            )


    # ---- Plot Trend -----
    def add_trend_lines(fig, df_timeline, sample_size = 100, theme_color = 'rgb(51, 204, 255)', show_peak_trend = False):
        fig.add_trace(go.Scatter(
            x= df_timeline['time'], 
            y= dff.get_trend_series(df_timeline, 'queue_length', sample_size, type = "average"),
            mode='lines', 
            name=f'Trend (Queue Length)',
            line=dict(color = theme_color, width=3)
        ))
        if show_peak_trend:
            fig.add_trace(go.Scatter(
                x= df_timeline['time'], 
                y= dff.get_trend_series(df_timeline, 'queue_length', sample_size, type = "peak"),
                mode='lines', 
                name=f'Trending Peak',
                line=dict(color = theme_color, dash='dot', width=1)
            ))
    
    def add_vertical_trace(fig, t, height = 100):
        # ---- Add a vertical line that animates across the x-axis ----
        fig.add_shape(
                    type="line",
                    x0= t,
                    x1= t,
                    y0= 0,
                    y1= height,  # Extend slightly above the max y to ensure visibility
                    line=dict(color="red", width=1,),
                    xref="x",
                    yref="y",
                )
    
    def add_horizontal_trace(fig, y, x_range = [0,100], color = "red"):
        # ---- Add a vertical line that animates across the x-axis ----
        fig.add_shape(
                    type="line",
                    x0= x_range[0],
                    x1= x_range[1],
                    y0= y,
                    y1= y,  # Extend slightly above the max y to ensure visibility
                    line=dict(color=color, width=1,),
                    xref="x",
                    yref="y",
                )