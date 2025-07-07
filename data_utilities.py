import os
import json
import pandas as pd
from datetime import datetime, timedelta
import math
import random
import streamlit as st
from general_utilities import general_utilities as gu
from io import BytesIO
import base64

class dataframe_functions:

    @staticmethod
    # ---- Sort Dataframes with KPI as Keys ----
    def sort_df_by_key(key: str, dataframes: dict[str, pd.DataFrame]) -> tuple[dict[str, pd.DataFrame], list[str]]:
        sorted_items = sorted(dataframes.items(), key=lambda item: item[1][key].mean(), reverse=True)
        sorted_dataframes = dict(sorted_items)
        return sorted_dataframes