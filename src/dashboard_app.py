# -*- coding: utf-8 -*-
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import json
import re
import numpy as np

# ==================================================
# 前置作業：載入資料與映射字典
# ==================================================
data_path = '../data/'
map_path = '../maps/'

def load_csv_data(file_name, file_description):
    try:
        df = pd.read_csv(f"{data_path}{file_name}", low_memory=False)
        print(f"已成功載入{file_description}: {file_name}")
        return df
    except FileNotFoundError:
        print(f"錯誤：找不到{file_description} '{data_path}{file_name}'。將使用空 DataFrame。")
        return pd.DataFrame()

def load_json_map(file_name, map_description, is_value_map=False):
    try:
        with open(f"{map_path}{file_name}", 'r', encoding='utf-8-sig') as f: data = json.load(f)
        print(f"已成功載入{map_description}: {file_name}")
        if is_value_map: return data.get("value_maps", {}), data.get("general_options", {})
        return data
    except FileNotFoundError: print(f"警告：找不到{map_description} '{map_path}{file_name}'。"); return ({}, {}) if is_value_map else {}
    except json.JSONDecodeError: print(f"錯誤：解析{map_description} '{map_path}{file_name}' 時發生錯誤。"); return ({}, {}) if is_value_map else {}

df_s = load_csv_data('TIGPSw1_s_descriptive_labeled.csv', '學生問卷資料')
df_p = load_csv_data('TIGPSw1_p_descriptive_labeled.csv', '家長問卷資料')
df_t = load_csv_data('TIGPSw1_t_descriptive_labeled.csv', '導師問卷資料')
df_st = load_csv_data('TIGPSw1_st_descriptive_labeled.csv', '科任教師問卷資料')
df_sc = load_csv_data('TIGPSw1_sc_descriptive_labeled.csv', '學校問卷資料')


# --- 資料合併 (範例，請根據您的實際需求和欄位名進行調整) ---
df_merged_s_t_st = df_s.copy() if not df_s.empty else pd.DataFrame()
if not df_t.empty and '學校班級 ID' in df_t.columns and '學校班級 ID' in df_merged_s_t_st.columns:
    df_merged_s_t_st = pd.merge(df_merged_s_t_st, df_t, on='學校班級 ID', how='left')
    print("學生資料與導師資料合併完成。")

if not df_st.empty and '學校班級 ID' in df_st.columns and '學校班級 ID' in df_merged_s_t_st.columns:
    df_merged_s_t_st = pd.merge(df_merged_s_t_st, df_st, on='學校班級 ID', how='left', suffixes=('', '_st_dup')) # 處理可能的後續衝突
    print("合併後的資料與科任老師資料再次合併完成。")

df_merged_s_p_sc = df_s.copy() if not df_s.empty else pd.DataFrame()
if not df_p.empty and '學生 ID' in df_p.columns and '學生 ID' in df_merged_s_p_sc.columns:
    df_merged_s_p_sc = pd.merge(df_merged_s_p_sc, df_p, on='學生 ID', how='left')
    print(df_merged_s_p_sc.columns)
    print("學生資料與家長資料合併完成。")
if not df_sc.empty and '學校 ID' in df_sc.columns and '學校 ID_x' in df_merged_s_p_sc.columns:
    df_sc_prefixed = df_sc.rename(columns=lambda c: f"{c}_x" if c == '學校 ID' else c)
    print(df_sc_prefixed.columns)
    print(df_merged_s_p_sc.columns)
    df_merged_s_p_sc = pd.merge(df_merged_s_p_sc, df_sc_prefixed, on='學校 ID_x', how='left')
    print("合併後的資料與學校資料再次合併完成。")

# --- 載入並合併映射表 ---
id_map_s = load_json_map('tigps_w1_s_id_map.json', '學生問卷ID Map')
value_map_s, general_options_s = load_json_map('tigps_w1_s_value_maps.json', '學生問卷Value Map', is_value_map=True)
id_map_t = load_json_map('tigps_w1_t_id_map.json', '導師問卷ID Map')
value_map_t, _ = load_json_map('tigps_w1_t_value_maps.json', '導師問卷Value Map', is_value_map=True)
id_map_p = load_json_map('tigps_w1_p_id_map.json', '家長問卷ID Map')
value_map_p, _ = load_json_map('tigps_w1_p_value_maps.json', '家長問卷Value Map', is_value_map=True)
id_map_st = load_json_map('tigps_w1_st_id_map.json', '科任教師問卷ID Map')
value_map_st, _ = load_json_map('tigps_w1_st_value_maps.json', '科任教師問卷Value Map', is_value_map=True)
id_map_sc = load_json_map('tigps_w1_sc_id_map.json', '學校問卷ID Map')
value_map_sc, _ = load_json_map('tigps_w1_sc_value_maps.json', '學校問卷Value Map', is_value_map=True)

master_id_map = {}
master_id_map.update(id_map_s)
master_id_map.update(id_map_t)
master_id_map.update(id_map_p)
master_id_map.update(id_map_st)
master_id_map.update(id_map_sc)
# for k, v in id_map_t.items(): master_id_map[f"t_{k}"] = v # 導師變項加 t_ 前綴
# for k, v in id_map_p.items(): master_id_map[f"p_{k}"] = v # 家長變項加 p_ 前綴
# for k, v in id_map_st.items(): master_id_map[f"st_{k}"] = v # 科任變項加 st_ 前綴
# for k, v in id_map_sc.items(): master_id_map[f"sc_{k}"] = v # 學校變項加 sc_ 前綴

master_value_map = {}
master_value_map.update(value_map_s)
master_value_map.update(value_map_t)
master_value_map.update(value_map_p)
master_value_map.update(value_map_st)
master_value_map.update(value_map_sc)
# for k, v in value_map_t.items(): master_value_map[f"t_{k}"] = v
# for k, v in value_map_p.items(): master_value_map[f"p_{k}"] = v
# for k, v in value_map_st.items(): master_value_map[f"st_{k}"] = v
# for k, v in value_map_sc.items(): master_value_map[f"sc_{k}"] = v

values_to_exclude = ["不適用", "跳答", "不知道、不清楚、忘記了", "拒答", "我不清楚", "系統遺漏值", "無意義作答/邏輯矛盾", "此卷未答"]
if general_options_s: # 假設通用排除項主要來自學生問卷
    for code, label in general_options_s.items():
        try:
            if int(code) < 0 and label not in values_to_exclude: values_to_exclude.append(label)
        except ValueError: pass
values_to_exclude = list(set(values_to_exclude))
print(f"將從分析中排除以下標籤: {values_to_exclude}")

# ==================================================
# 輔助函數定義 (使用 master_id_map 和 master_value_map)
# ==================================================
def get_option_order(variable_code_with_prefix):
    options = master_value_map.get(variable_code_with_prefix, {})
    if not options: return []
    sorted_items = []
    try:
        numeric_keys = [(float(k), v) for k, v in options.items()]
        sorted_items = sorted(numeric_keys)
    except (ValueError, TypeError):
         try: return sorted([v for v in options.values() if v not in values_to_exclude])
         except TypeError: return [v for v in list(options.values()) if v not in values_to_exclude]
    return [label for val, label in sorted_items if label not in values_to_exclude]

def get_label_to_score_map(variable_code_with_prefix, reverse_score=False):
    options = master_value_map.get(variable_code_with_prefix, {})
    if not options: return None
    valid_options = {k: v for k, v in options.items() if v not in values_to_exclude}
    if not valid_options: return None
    sorted_items = []
    try:
        numeric_keys = [(float(k), v) for k, v in valid_options.items()]
        sorted_items = sorted(numeric_keys)
    except (ValueError, TypeError):
         print(f"警告(輔助函數)：變項 {variable_code_with_prefix} 的有效選項鍵無法轉為數值排序。")
         return None
    score_map = {}
    num_options = len(sorted_items)
    for i, (original_value, label) in enumerate(sorted_items):
        score = (num_options - i) if reverse_score else (i + 1)
        score_map[label] = score
    return score_map

# ==================================================
# Dash App 初始化
# ==================================================
app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server

# ==================================================
# 為每個目標定義 custom_topics (使用您提供的版本)
# 變項代碼需與合併後 DataFrame 中的欄位名一致 (可能包含前綴)
# ==================================================
# --- 目標一 (學生變項，假設無前綴或 's_' 前綴已在 df_s 欄位名中) ---
custom_topics_target1 = {
    "主題: 數位學習行為": ['as35a', 'as35b', 'as56a', 'as56b', 'as56d', 'as59a', 'as59b', 'as59c', 'as59d'],
    "主題: 數位素養": ['as60a', 'as60b', 'as60c', 'as61a', 'as61b', 'as61c', 'as61d', 'as61e', 'as61f', 'as61g', 'as61h', 'as61i'],
    "主題: 學習動機/興趣 (代理)": ['as14a', 'as19'],
    "主題: 學業表現 (代理)": ['as20'],
    "主題: 上網時間分配": ['as35a', 'as35b', 'as35c', 'as35d', 'as35e', 'as35f'],
    "主題: 網路沉迷風險": ['as41a', 'as41b', 'as41c', 'as41d', 'as41e', 'as41f', 'as41g', 'as41h', 'as41i', 'as41j'],
}

# --- 目標二 (假設導師變項前綴 't_', 科任 'st_', 學生無前綴或 's_') ---
custom_topics_target2 = {
    "主題: 導師-媒體科技使用情形": ['at27a', 'at27b', 'at27c', 'at27d', 'at27e', 'at27f', 'at27g'],
    "主題: 導師-數位教學實踐與信念": ['at29a', 'at29b', 'at29c', 'at29d', 'at29e', 'at29f', 'at29g', 'at29h', 'at29i', 'at29j', 'at29k', 'at29l', 'at29m', 'at29n', 'at29o', 'at29p', 'at29q', 'at29r', 'at29s', 'at29t', 'at29u', 'at29v', 'at29w', 'at29x' ],
    "主題: 導師-數位教學與儀表板使用時數": ['at34', 'at35', 'at36'],
    "主題: 導師-教學阻礙因素": ['at43a', 'at43b', 'at43c', 'at43d', 'at43e', 'at43f', 'at43g'],
    "主題: 科任-教學阻礙因素": ['atsub1', 'atsub2', 'atsub3', 'atsub4', 'atsub5', 'atsub6', 'atsub7'],
    "主題: 科任-媒體科技使用情形(共同)": ['at27a', 'at27b', 'at27c', 'at27d', 'at27e', 'at27f', 'at27g'], # 假設科任共同題變項名與導師不同 (例如 at27a)
    "主題: 科任-數位教學實踐與信念(共同)": ['at29a', 'at29x'], # 簡化
    "主題: 學生感知-課業進度感受": ['as19'],
    "主題: 學生感知-上網做功課時間": ['as35a'],
    "主題: 學生感知-喜歡學校程度": ['as14a']
}

# --- 目標三 ---
custom_topics_target3 = {
    "主題: 數位資源品質-學生報告": ['as57a', 'as57b', 'as57c', 'as57d'],
    "主題: 數位資源品質-家中上網方式(家長)": ['ap52_1', 'ap52_2', 'ap52_3', 'ap52_4', 'ap52_5', 'ap52_6', 'ap52_7'],
    "主題: 數位資源品質-家中設備數量(家長)": ['ap49a', 'ap49b', 'ap49c', 'ap49d', 'ap49e', 'ap49f', 'ap49g', 'ap49h'],
    "主題: 使用模式-學習相關時間(學生)": ['as35a', 'as35b'],
    "主題: 使用模式-娛樂相關時間(學生)": ['as35c', 'as35d', 'as35e'],
    "主題: 家庭SES-家長教育程度（學生）": ['as4d1', 'as4d2'],
    "主題: 家庭SES-家長教育程度（家長）": ['ap5'],
    "主題: 家庭SES-自評家境（學生）": ['as10'],
    "主題: 家庭SES-自評家境（家長）": ['ap20'],
    "主題: 家庭SES-家長職業(家長)": ['ap92', 'ap104'],
    "主題: 學習投入/表現(學生)": ['as35a', 'as35b', 'as20'],
    "主題: 學校支持-課程與管理": ['asc14', 'asc15', 'asc25k'],
    "主題: 學校支持-弱勢與設施": ['asc24j', 'asc25d', 'asc25e', 'asc25l', 'asc25m'],
}

# --- 目標四 (學生變項) ---
custom_topics_target4 = {
    "主題: 數位福祉-網路社交壓力(FoMO)": ['as39a', 'as39b', 'as39c', 'as39d'],
    "主題: 數位福祉-社會比較": ['as40a', 'as40b', 'as40c', 'as40d', 'as40e', 'as40f'],
    "主題: 數位福祉-螢幕使用時間": ['as35a', 'as35b', 'as35c', 'as35d', 'as35e', 'as35f'],
    "主題: 數位福祉-網路成癮傾向": ['as41a', 'as41b', 'as41c', 'as41d', 'as41e', 'as41f', 'as41g', 'as41h', 'as41i', 'as41j'],
    "主題: 網路霸凌經驗-被霸凌(是否與形式)": ['as53', 'as53a1', 'as53a2', 'as53a3', 'as53a4', 'as53a5', 'as53a6', 'as53a7', 'as53a8'],
    "主題: 網路霸凌經驗-霸凌他人(是否與形式)": ['as54', 'as54a1', 'as54a2', 'as54a3', 'as54a4', 'as54a5', 'as54a6', 'as54a7', 'as54a8'],
    "主題: 校園適應-同儕關係品質": ['as42a', 'as42b', 'as42c', 'as42d', 'as42e', 'as16a', 'as16b', 'as16c', 'as16d', 'as16e'],
    "主題: 校園適應-校園歸屬感": ['as14a', 'as14b', 'as14c'],
    "主題: 校園適應-學業壓力感受": ['as72k', 'as72l', 'as21'],
    "主題: 校園適應-整體幸福感": ['as62', 'as63', 'as65a', 'as65b', 'as65c'],
}

# --- 集中管理所有目標的定義 ---
target_definitions = {
    "目標一：學生數位學習與學業": {
        "topics": custom_topics_target1,
        "df_name": "df_s", # 主要使用學生原始資料
        "id_map_obj": master_id_map, # 使用合併後的 master map
        "value_map_obj": master_value_map,
    },
    "目標二：教師科技融入與學生經驗": {
        "topics": custom_topics_target2,
        "df_name": "df_merged_s_t_st", # 應指向您合併學生、導師、科任後的 DataFrame
        "id_map_obj": master_id_map,
        "value_map_obj": master_value_map,
    },
    "目標三：數位資源差異與學習機會": {
        "topics": custom_topics_target3,
        "df_name": "df_merged_s_p_sc", # 應指向您合併學生、家長、學校後的 DataFrame
        "id_map_obj": master_id_map,
        "value_map_obj": master_value_map,
    },
    "目標四：數位福祉與校園適應": {
        "topics": custom_topics_target4,
        "df_name": "df_s",
        "id_map_obj": master_id_map,
        "value_map_obj": master_value_map,
    },
}

# 為每個 custom_topics 補充 "主題: 所有可分析變項"
for target_name, definition in target_definitions.items():
    all_vars_in_target = []
    for topic_vars in definition['topics'].values():
        all_vars_in_target.extend(topic_vars)
    definition['topics']["主題: 所有可分析變項"] = sorted(list(set(all_vars_in_target)))


# --- 準備目標選擇器的選項 ---
target_selector_options = [{'label': name, 'value': name} for name in target_definitions.keys()]
initial_target = target_selector_options[0]['value'] if target_selector_options else None

# ==================================================
# App Layout 定義 (與前一版本相同)
# ==================================================
app.layout = html.Div([
    html.H1("TIGPS 資料探索儀表板"),
    html.Div([
        html.Label("選擇研究目標:", style={'fontWeight': 'bold'}),
        dcc.RadioItems(
            id='target-selector-radio',
            options=target_selector_options,
            value=initial_target,
            labelStyle={'display': 'block', 'marginBottom': '5px'}
        ),
    ], style={'marginBottom': 20, 'padding': '15px', 'border': '1px solid #ccc', 'borderRadius': '5px'}),
    html.Hr(),
    html.Div([
        html.Label("選擇分析類型:", style={'fontWeight': 'bold'}),
        dcc.RadioItems( id='analysis-type-radio',
           options=[ {'label': '主題/題組描述', 'value': 'describe_group'},
                     {'label': '雙變項關聯', 'value': 'relate'} ],
            value='describe_group', labelStyle={'display': 'inline-block', 'marginRight': '20px'}
        ),
    ], style={'marginBottom': 20, 'borderBottom': '1px solid #eee', 'paddingBottom': '10px'}),
    html.Div(id='controls-area', children=[], style={'padding': '20px', 'border': '1px solid #ddd', 'borderRadius': '5px', 'backgroundColor': '#f9f9f9', 'marginBottom': '20px'}),
    html.Hr(),
    html.Div([
        html.H3("分析結果:", style={'marginBottom': '10px'}),
        html.Div(id='describe-output-container'),
        html.Div(id='relate-output-container', children=[
             html.Div(id='stats-output-relate', style={'whiteSpace': 'pre-wrap', 'fontFamily': 'monospace', 'border': '1px solid #eee', 'padding': '10px', 'marginBottom': '20px', 'backgroundColor': '#fafafa'}),
             dcc.Graph(id='plot-output-relate', figure=go.Figure())
        ], style={'display': 'none'})
    ])
])

# ==================================================
# Callbacks 定義 (與前一版本相同，核心邏輯不變)
# ==================================================

# --- Callback A: 更新控制項區域佈局 ---
@app.callback(
    Output('controls-area', 'children'),
    Input('target-selector-radio', 'value')
)
def update_controls_area_layout(selected_target_name):
    if not selected_target_name or selected_target_name not in target_definitions:
        return html.P("請先選擇一個研究目標。")

    target_info = target_definitions[selected_target_name]
    current_target_topics = target_info['topics']
    active_id_map_for_dropdowns = target_info['id_map_obj'] # 使用 master_id_map
    current_df_name = target_info['df_name']
    current_df = globals().get(current_df_name, pd.DataFrame())

    current_topic_group_options = [{'label': name, 'value': name} for name in sorted(current_target_topics.keys())]
    initial_topic_for_target = current_topic_group_options[0]['value'] if current_topic_group_options else None

    default_topic_key_for_relate = "主題: 所有可分析變項" # 使用新的通用主題名
    if default_topic_key_for_relate not in current_target_topics and current_topic_group_options:
        default_topic_key_for_relate = current_topic_group_options[0]['value']
    
    default_codes_for_relate = current_target_topics.get(default_topic_key_for_relate, [])

    initial_relate_var_options = []
    if not current_df.empty:
        initial_relate_var_options = [{'label': f"{active_id_map_for_dropdowns.get(code, code)} ({code})", 'value': code}
                                      for code in default_codes_for_relate
                                      if code in active_id_map_for_dropdowns and active_id_map_for_dropdowns.get(code,code) in current_df.columns]

    initial_relate_x_val = initial_relate_var_options[0]['value'] if initial_relate_var_options else None
    initial_relate_y_val = initial_relate_var_options[1]['value'] if len(initial_relate_var_options) > 1 else (initial_relate_var_options[0]['value'] if initial_relate_var_options else None)
    
    describe_controls = html.Div(id='describe-group-controls', children=[
        html.Label("1. 選擇要描述的主題/題組:", style={'fontWeight': 'bold'}),
        dcc.Dropdown(id='topic-group-dropdown', options=current_topic_group_options, value=initial_topic_for_target, clearable=False),
        html.Label("2. (可選) 過濾顯示的子項目:", style={'fontWeight': 'bold', 'marginTop': '10px'}),
        dcc.Dropdown(id='variable-filter-multiselect', options=[], value=[], multi=True)
    ])
    relate_controls = html.Div(id='relate-controls', children=[
        html.Div([
             html.Label("1. 選擇 X 軸 主題/題組:", style={'fontWeight': 'bold'}),
             dcc.Dropdown(id='topic-group-dropdown-x', options=current_topic_group_options, value=default_topic_key_for_relate if default_topic_key_for_relate in current_target_topics else initial_topic_for_target, clearable=False),
             html.Label("2. 選擇 X 軸 變項:", style={'fontWeight': 'bold', 'marginTop': '5px'}),
             dcc.Dropdown(id='relate-x-dropdown', options=initial_relate_var_options, value=initial_relate_x_val, clearable=False)
        ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top', 'marginRight': '2%'}),
        html.Div([
            html.Label("3. 選擇 Y 軸 主題/題組:", style={'fontWeight': 'bold'}),
            dcc.Dropdown(id='topic-group-dropdown-y', options=current_topic_group_options, value=default_topic_key_for_relate if default_topic_key_for_relate in current_target_topics else initial_topic_for_target, clearable=False),
            html.Label("4. 選擇 Y 軸 變項:", style={'fontWeight': 'bold', 'marginTop': '5px'}),
            dcc.Dropdown(id='relate-y-dropdown', options=initial_relate_var_options, value=initial_relate_y_val, clearable=False)
        ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top', 'float': 'right'}),
        html.Div([
            html.Label("5. 選擇圖表類型:", style={'fontWeight': 'bold', 'marginTop': '15px'}),
            dcc.RadioItems( id='relate-plot-type',
               options=[ {'label': '盒鬚圖 (Y軸需轉分數)', 'value': 'boxplot'},
                         {'label': '交叉表熱圖 (百分比)', 'value': 'heatmap'},
                         {'label': '堆疊長條圖 (次數)', 'value': 'stackedbar'}],
                value='boxplot', labelStyle={'display': 'inline-block', 'marginRight': '20px'} )
        ], style={'clear': 'both', 'paddingTop': '15px'})
    ])
    return [describe_controls, relate_controls]

# --- Callback 1: 根據分析類型顯示/隱藏控制項和輸出區域 ---
@app.callback(
    Output('describe-group-controls', 'style', allow_duplicate=True), Output('relate-controls', 'style', allow_duplicate=True),
    Output('describe-output-container', 'style', allow_duplicate=True), Output('relate-output-container', 'style', allow_duplicate=True),
    Input('analysis-type-radio', 'value'),
    prevent_initial_call=True
)
def toggle_controls_and_outputs(analysis_type):
    desc_style = {'display': 'none', 'marginBottom': 15}; rel_style = {'display': 'none', 'marginBottom': 15}
    desc_out_style = {'display': 'none'}; rel_out_style = {'display': 'none'}
    if analysis_type == 'describe_group': desc_style = {'marginBottom': 15}; desc_out_style = {'display': 'block'}
    elif analysis_type == 'relate': rel_style = {'marginBottom': 15}; rel_out_style = {'display': 'block'}
    return desc_style, rel_style, desc_out_style, rel_out_style

# --- Callback 2: 動態更新描述性分析的過濾器選項 ---
@app.callback(
    Output('variable-filter-multiselect', 'options'), Output('variable-filter-multiselect', 'value'),
    Input('topic-group-dropdown', 'value'), State('target-selector-radio', 'value')
)
def update_variable_filter_options(selected_topic_group_name, selected_target_name):
    if not selected_topic_group_name or not selected_target_name or selected_target_name not in target_definitions: return [], []
    target_info = target_definitions[selected_target_name]; current_target_topics = target_info['topics']
    active_id_map = target_info['id_map_obj']; current_df = globals().get(target_info['df_name'], pd.DataFrame())
    if selected_topic_group_name not in current_target_topics: return [],[]
    codes_in_group = current_target_topics[selected_topic_group_name]
    options = [{'label': f"{active_id_map.get(code, code)} ({code})", 'value': code} for code in codes_in_group if code in active_id_map and active_id_map.get(code,code) in current_df.columns]
    return options, []

# --- Callback 3: 更新主題/題組描述輸出 ---
@app.callback(
    Output('describe-output-container', 'children'),
    Input('analysis-type-radio', 'value'), Input('topic-group-dropdown', 'value'),
    Input('variable-filter-multiselect', 'value'), State('target-selector-radio', 'value')
)
def update_describe_group_outputs(analysis_type, selected_topic_group_name, selected_variables, selected_target_name):
    if analysis_type != 'describe_group' or not selected_topic_group_name or not selected_target_name or selected_target_name not in target_definitions:
        return html.P("請選擇一個研究目標和主題/題組進行描述性分析。")
    target_info = target_definitions[selected_target_name]; current_target_topics = target_info['topics']
    current_df = globals().get(target_info['df_name'], pd.DataFrame()); active_id_map = target_info['id_map_obj']; active_value_map = target_info['value_map_obj']
    if selected_topic_group_name not in current_target_topics: return html.P(f"目標'{selected_target_name}'中無此主題'{selected_topic_group_name}'。")
    if current_df.empty: return html.Div([html.H4(f"研究目標: {selected_target_name} >> 主題/題組：{selected_topic_group_name}"), html.P(f"錯誤：目標 '{selected_target_name}' 對應的資料表 ({target_info['df_name']}) 未載入或為空。")])

    all_codes_in_group = current_target_topics[selected_topic_group_name]
    codes_to_display = selected_variables if selected_variables else all_codes_in_group
    output_elements = [html.H4(f"研究目標: {selected_target_name} >> 主題/題組：{selected_topic_group_name}")]
    if not codes_to_display: output_elements.append(html.P("此主題/題組下無變項可顯示。")); return output_elements

    for code in codes_to_display:
        if code not in all_codes_in_group: continue
        col_name = active_id_map.get(code, code)
        if col_name not in current_df.columns:
            output_elements.append(html.Div([ html.Hr(), html.P(f"錯誤(描述)：資料({target_info['df_name']})中找不到變項 '{code}'/'{col_name}'。", style={'color': 'red'}) ])); continue
        df_var_filtered = current_df[~current_df[col_name].isin(values_to_exclude)].copy()
        if df_var_filtered.empty or df_var_filtered[col_name].dropna().empty:
            output_elements.append(html.Div([ html.Hr(), html.P(f"子項目: {col_name} ({code}) - 過濾排除值或移除NA後無有效數據。") ])); continue
        stats_text_list = [f"--- 子項目: {col_name} ({code}) [已排除無效值] ---"]
        value_counts_abs = df_var_filtered[col_name].value_counts().sort_index(); value_counts_rel = df_var_filtered[col_name].value_counts(normalize=True).sort_index()
        option_order = get_option_order(code); valid_order = None
        try:
            if option_order:
                 current_index_set = set(value_counts_abs.index); valid_order = [opt for opt in option_order if opt in current_index_set]
                 if valid_order: value_counts_abs = value_counts_abs.reindex(valid_order, fill_value=0); value_counts_rel = value_counts_rel.reindex(valid_order, fill_value=0)
        except Exception as e: stats_text_list.append(f"警告：排序時出錯: {e}。")
        stats_df = pd.DataFrame({'次數': value_counts_abs, '比例': value_counts_rel}); stats_text_list.append("\n次數分佈:"); stats_text_list.append(stats_df.to_string(float_format='{:.1%}'.format))
        fig = go.Figure()
        try:
            fig = px.histogram(df_var_filtered, x=col_name, title=f"分佈：{col_name}", category_orders={col_name: valid_order} if valid_order else None)
            fig.update_layout(xaxis_title=col_name, yaxis_title="人數", height=300, margin=dict(t=30, b=0)); fig.update_xaxes(type='category')
        except Exception as e: error_msg = f"錯誤：繪圖時發生錯誤: {e}"; stats_text_list.append(f"\n{error_msg}"); fig.update_layout(title=error_msg)
        item_div = html.Div([ html.Hr(), html.Pre("\n".join(stats_text_list), style={'whiteSpace': 'pre-wrap', 'fontFamily': 'monospace', 'fontSize': 'small'}), dcc.Graph(figure=fig) ], style={'marginBottom': '20px', 'padding': '10px', 'border': '1px solid #eee'})
        output_elements.append(item_div)
    return output_elements

# --- Callback 4 & 5: 動態更新 X 和 Y 軸變項下拉選單的選項 ---
@app.callback(
    Output('relate-x-dropdown', 'options'), Output('relate-x-dropdown', 'value'),
    Output('relate-y-dropdown', 'options'), Output('relate-y-dropdown', 'value'),
    Input('topic-group-dropdown-x', 'value'), Input('topic-group-dropdown-y', 'value'),
    State('target-selector-radio', 'value')
)
def update_relate_variable_options(selected_topic_x, selected_topic_y, selected_target_name):
    if not selected_target_name or selected_target_name not in target_definitions: return [], None, [], None
    target_info = target_definitions[selected_target_name]; current_target_topics = target_info['topics']
    active_id_map = target_info['id_map_obj']; current_df = globals().get(target_info['df_name'], pd.DataFrame())
    options_x, value_x = ([], None)
    if selected_topic_x and selected_topic_x in current_target_topics:
        codes_x = current_target_topics[selected_topic_x]
        options_x = [{'label': f"{active_id_map.get(code, code)} ({code})", 'value': code} for code in codes_x if code in active_id_map and active_id_map.get(code,code) in current_df.columns]
        value_x = options_x[0]['value'] if options_x else None
    options_y, value_y = ([], None)
    if selected_topic_y and selected_topic_y in current_target_topics:
        codes_y = current_target_topics[selected_topic_y]
        options_y = [{'label': f"{active_id_map.get(code, code)} ({code})", 'value': code} for code in codes_y if code in active_id_map and active_id_map.get(code,code) in current_df.columns]
        value_y = options_y[0]['value'] if options_y else None
        if options_y and len(options_y) > 1 and value_y == value_x : value_y = options_y[1]['value']
        elif options_y and value_y == value_x and len(options_y) == 1 : value_y = None
    return options_x, value_x, options_y, value_y

# --- Callback 6: 更新雙變項關聯輸出 ---
@app.callback(
    Output('plot-output-relate', 'figure'), Output('stats-output-relate', 'children'),
    Input('analysis-type-radio', 'value'), Input('relate-x-dropdown', 'value'),
    Input('relate-y-dropdown', 'value'), Input('relate-plot-type', 'value'),
    State('target-selector-radio', 'value'), State('topic-group-dropdown-x', 'value'), State('topic-group-dropdown-y', 'value'),
    prevent_initial_call=True
)
def update_relate_outputs(analysis_type, x_code, y_code, plot_type, selected_target_name, topic_x_name, topic_y_name):
    if analysis_type != 'relate' or not x_code or not y_code or not selected_target_name or selected_target_name not in target_definitions:
        return go.Figure(), "請先選擇研究目標、X/Y 軸主題/題組，然後選擇具體變項。"
    target_info = target_definitions[selected_target_name]; current_df = globals().get(target_info['df_name'], pd.DataFrame())
    active_id_map = target_info['id_map_obj']; active_value_map = target_info['value_map_obj']
    if current_df.empty: return go.Figure(), f"錯誤：目標 '{selected_target_name}' 的資料表 ({target_info['df_name']}) 未載入或為空。"

    x_col = active_id_map.get(x_code, x_code); y_col = active_id_map.get(y_code, y_code)
    if x_col not in current_df.columns or y_col not in current_df.columns:
        missing_cols = []
        if x_col not in current_df.columns: missing_cols.append(f"X軸'{x_col}'({x_code})")
        if y_col not in current_df.columns: missing_cols.append(f"Y軸'{y_col}'({y_code})")
        return go.Figure(), f"錯誤(關聯)：資料({target_info['df_name']})中找不到: {', '.join(missing_cols)}。"
    if x_code == y_code: return go.Figure(), "錯誤：X 軸和 Y 軸不能選擇相同的變項。"

    stats_text_list = [f"===== 雙變項關聯分析 (研究目標: {selected_target_name}) ====="]
    stats_text_list.append(f"X 軸: {x_col} ({x_code}) [來自: {topic_x_name}]"); stats_text_list.append(f"Y 軸: {y_col} ({y_code}) [來自: {topic_y_name}]")
    stats_text_list.append(f"圖表類型: {plot_type}"); stats_text_list.append(f"[已排除含無效值的資料列]")
    fig = go.Figure()
    df_rel_filtered = current_df[ (~current_df[x_col].isin(values_to_exclude)) & (~current_df[y_col].isin(values_to_exclude)) ].copy()
    temp_df = df_rel_filtered[[x_col, y_col]].dropna()
    if temp_df.empty: return go.Figure(), "\n".join(stats_text_list) + "\n錯誤：過濾後無足夠數據。"

    try:
        option_order_x = get_option_order(x_code)
        option_order_y = get_option_order(y_code)
        valid_order_x = [opt for opt in option_order_x if opt in temp_df[x_col].unique()] if option_order_x else None
        valid_order_y = [opt for opt in option_order_y if opt in temp_df[y_col].unique()] if option_order_y else None

        if plot_type == 'boxplot':
            # ... (boxplot 邏輯同前) ...
            stats_text_list.append("\n--- 盒鬚圖分析 ---")
            score_map_y = get_label_to_score_map(y_code)
            if not score_map_y: msg = f"錯誤：Y軸'{y_col}'無法轉分數。"; stats_text_list.append(msg); fig.update_layout(title=msg); return fig, "\n".join(stats_text_list)
            y_score_col = f"{y_code}_score"; temp_df.loc[:, y_score_col] = temp_df[y_col].map(score_map_y)
            temp_df = temp_df.dropna(subset=[x_col, y_score_col])
            if temp_df.empty: msg = "錯誤：轉換分數後無數據。"; stats_text_list.append(msg); fig.update_layout(title=msg); return fig, "\n".join(stats_text_list)
            fig = px.box(temp_df, x=x_col, y=y_score_col, title=f"'{x_col}' 對 '{y_col}' (分數)", category_orders={x_col: valid_order_x} if valid_order_x else None, points=False)
            fig.update_layout(xaxis_title=f"{x_col}", yaxis_title=f"{y_col} (分數)")
            stats_text_list.append("\n分組統計 (Y分數):")
            grouped_stats = temp_df.groupby(x_col)[y_score_col].agg(['mean', 'median', 'std', 'count']).round(2)
            if valid_order_x: 
                try: grouped_stats = grouped_stats.reindex(valid_order_x)
                except Exception: pass
            stats_text_list.append(grouped_stats.to_string())

        elif plot_type == 'heatmap':
            # ... (heatmap 邏輯同前) ...
            stats_text_list.append("\n--- 交叉表熱圖 (行百分比) ---")
            crosstab_rel = pd.crosstab(temp_df[x_col], temp_df[y_col], normalize='index')
            if valid_order_x: 
                try: crosstab_rel = crosstab_rel.reindex(index=valid_order_x)
                except Exception: pass
            if valid_order_y: 
                try: crosstab_rel = crosstab_rel.reindex(columns=valid_order_y)
                except Exception: pass
            crosstab_rel = crosstab_rel.fillna(0)
            fig = px.imshow(crosstab_rel, text_auto=".1%", title=f"'{x_col}' vs '{y_col}' (行百分比)", labels=dict(x=y_col, y=x_col, color="比例"), x=crosstab_rel.columns, y=crosstab_rel.index, aspect="auto", color_continuous_scale=px.colors.sequential.Viridis)
            fig.update_xaxes(side="top"); stats_text_list.append("\n交叉表數據 (行百分比):"); stats_text_list.append(crosstab_rel.round(3).to_string())

        elif plot_type == 'stackedbar':
            # ... (stackedbar 邏輯同前) ...
            stats_text_list.append("\n--- 堆疊長條圖 (次數) ---")
            crosstab_abs = pd.crosstab(temp_df[x_col], temp_df[y_col])
            if valid_order_x: 
                try: crosstab_abs = crosstab_abs.reindex(index=valid_order_x)
                except Exception: pass
            if valid_order_y: 
                try: crosstab_abs = crosstab_abs.reindex(columns=valid_order_y)
                except Exception: pass
            crosstab_abs = crosstab_abs.fillna(0)
            plot_df = crosstab_abs.reset_index().melt(id_vars=x_col, var_name=y_col, value_name='人數')
            cat_orders = {};
            if valid_order_x: cat_orders[x_col] = valid_order_x
            if valid_order_y: cat_orders[y_col] = valid_order_y
            fig = px.bar(plot_df, x=x_col, y='人數', color=y_col, title=f"'{x_col}' vs '{y_col}' (次數)", category_orders=cat_orders if cat_orders else None, barmode='stack')
            fig.update_layout(xaxis_title=f"{x_col}", yaxis_title="人數"); stats_text_list.append("\n交叉表數據 (次數):"); stats_text_list.append(crosstab_abs.astype(int).to_string())

        else: msg = f"錯誤：未知圖表 '{plot_type}'。" ; stats_text_list.append(msg); fig.update_layout(title=msg)
    except Exception as e: error_msg = f"錯誤：處理關聯時發生錯誤: {e}"; stats_text_list.append(f"\n{error_msg}"); fig = go.Figure(); fig.update_layout(title=error_msg)
    return fig, "\n".join(stats_text_list)

# ==================================================
# 執行 App
# ==================================================
if __name__ == '__main__':
    print("儀表板準備啟動...")
    app.run(debug=True)