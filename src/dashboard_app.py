# -*- coding: utf-8 -*-
# 導入必要的函式庫
import dash
from dash import dcc, html # Dash 核心元件和 HTML 標籤
from dash.dependencies import Input, Output, State # 用於定義回呼函數的互動
import plotly.express as px # 用於快速生成互動式圖表
import plotly.graph_objects as go # 用於更底層的圖表控制或建立空圖
import pandas as pd # 用於資料處理
import json # 用於讀取 JSON 映射檔案
import re # 用於正則表達式 (檢查題幹代碼)
import numpy as np # 用於數值計算 (例如處理 NaN)

# ==================================================
# 前置作業：載入資料與映射字典
# (請確保這些檔案路徑相對於您執行此腳本的位置是正確的)
# ==================================================
# --- 載入資料 ---
try:
    # 使用相對路徑載入已標記的 CSV 檔案
    df_s = pd.read_csv('../data/TIGPSw1_s_descriptive_labeled.csv', low_memory=False)
    print("已成功載入 TIGPSw1_s_descriptive_labeled.csv")
except FileNotFoundError:
    print("錯誤：找不到 '../data/TIGPSw1_s_descriptive_labeled.csv'，請確認檔案路徑。")
    df_s = pd.DataFrame() # 如果找不到檔案，建立空的 DataFrame 以免後續出錯

# --- 載入 ID 映射檔 (變項代碼 -> 變項說明) ---
try:
    with open('../maps/tigps_w1_s_id_map.json', 'r', encoding='utf-8-sig') as f:
        id_map = json.load(f)
    print("已成功載入 tigps_w1_s_id_map.json")
except FileNotFoundError:
    print("警告：找不到 '../maps/tigps_w1_s_id_map.json'")
    id_map = {} # 如果找不到檔案，使用空字典

# --- 載入 Value 映射檔 (變項代碼 -> {原始值: 選項標籤}) ---
try:
    with open('../maps/tigps_w1_s_value_maps.json', 'r', encoding='utf-8-sig') as f:
        value_maps_data = json.load(f) # 載入整個 JSON
        # 提取 'value_maps' 鍵下的字典，這是實際的選項映射
        value_map = value_maps_data.get("value_maps", {})
        # (可選) 提取通用選項，如果有的話
        general_options = value_maps_data.get("general_options", {})
    print("已成功載入 ../maps/tigps_w1_s_value_maps.json")
except FileNotFoundError:
    print("警告：找不到 ../maps/tigps_w1_s_value_maps.json")
    value_map = {} # 如果找不到檔案，使用空字典
    general_options = {}

# ==================================================
# *** 新增：定義要從分析中排除的選項標籤列表 ***
# !!! 請務必根據您 df_s 資料中的實際標籤修改此列表 !!!
# ==================================================
values_to_exclude = [
    "不適用",
    #"不一定", # 根據需要決定是否排除
    "跳答",
    #"不知道", # 或 "我不清楚"
    "拒答",
    # 以下標籤可能不存在於已標籤化的資料中，但以防萬一
    "系統遺漏值",
    "無意義作答/邏輯矛盾",
    "此卷未答"
]
print(f"將從分析中排除以下標籤: {values_to_exclude}")

# ==================================================
# 輔助函數定義
# ==================================================
def get_option_order(variable_code):
    """
    根據變項代碼從 value_map 獲取選項標籤的建議順序。
    假設 value_map 的 key 是可轉換為數值的原始值。
    如果無法按數值排序，則嘗試按標籤字母排序。
    """
    options = value_map.get(variable_code, {}) # 從 value_map (單數) 獲取選項
    if not options: return [] # 如果沒有選項資訊，返回空列表

    sorted_items = []
    try:
        # 嘗試將選項的 key (原始值) 轉為 float 並排序
        numeric_keys = [(float(k), v) for k, v in options.items()]
        sorted_items = sorted(numeric_keys)
    except (ValueError, TypeError):
         # 如果 key 不是數字或無法排序，退回按標籤(value)字母排序
         try:
             # 返回按標籤字母排序的標籤列表
             return sorted(options.values())
         except TypeError: # 如果標籤本身也無法比較
             return list(options.values()) # 返回原始順序 (可能無意義)

    # 如果按數值鍵排序成功，返回排序後的標籤列表
    return [label for val, label in sorted_items]

def get_label_to_score_map(variable_code, reverse_score=False):
    """
    建立從選項標籤到數值分數 (1, 2, 3...) 的映射。
    分數的順序基於 value_map 中原始數值鍵的排序。
    如果原始鍵無法轉為數值排序，則無法生成可靠分數，返回 None。
    reverse_score=True 會將分數反轉 (例如 5, 4, 3...)。
    """
    options = value_map.get(variable_code, {}) # 從 value_map (單數) 獲取選項
    if not options: return None # 無選項資訊

    sorted_items = []
    try:
        # 嘗試按原始數值鍵排序
        numeric_keys = [(float(k), v) for k, v in options.items()]
        sorted_items = sorted(numeric_keys)
    except (ValueError, TypeError):
         # 如果無法按數值鍵排序，則無法保證分數的意義，不生成映射
         print(f"警告：變項 {variable_code} 的選項鍵無法轉換為數值排序，無法生成分數映射。")
         return None

    # 建立分數映射
    score_map = {}
    num_options = len(sorted_items)
    for i, (original_value, label) in enumerate(sorted_items):
        # 計算分數，1-based index
        score = (num_options - i) if reverse_score else (i + 1)
        score_map[label] = score # 映射: 標籤 -> 分數
    return score_map

# ==================================================
# Dash App 初始化
# ==================================================
# suppress_callback_exceptions=True 允許回呼函數的 Input/Output 不在初始佈局中完全定義 (例如動態顯示的元件)
app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server # 用於部署時 (例如 Heroku, Gunicorn)

# ==================================================
# 定義主題/題組結構 (用於新的描述性分析模式)
# ==================================================
# 原始變項分組結構 (用於提取資料)
target_var_groups_raw = [
    ['as35a'], ['as35b'], ['s56', 'as56a', 'as56b', 'as56d'],
    ['s59', 'as59a', 'as59b', 'as59c', 'as59d'], ['s60', 'as60a', 'as60b', 'as60c'],
    ['s61', 'as61a', 'as61b', 'as61c', 'as61d', 'as61e', 'as61f', 'as61g', 'as61h', 'as61i'],
    ['as14a'], ['as19'], ['as20'], ['s35', 'as35c', 'as35d', 'as35e', 'as35f'],
    ['s37', 'as37a', 'as37b', 'as37c', 'as37d', 'as37e', 'as37f'],
    ['s58', 'as58a', 'as58b', 'as58c', 'as58d', 'as58e'],
    ['s41', 'as41a', 'as41b', 'as41c', 'as41d', 'as41e', 'as41f', 'as41g', 'as41h', 'as41i', 'as41j'],
    ['s57', 'as57a', 'as57b', 'as57c', 'as57d'],
    ['s28', 'as28a', 'as28b', 'as28c', 'as28d', 'as28e', 'as28f', 'as28g', 'as28h', 'as28i', 'as28j', 'as28k', 'as28l', 'as28m', 'as28n', 'as28o', 'as28p', 'as28q', 'as28r'],
    ['s29', 'as29a', 'as29b', 'as29c', 'as29d', 'as29e', 'as29f', 'as29g', 'as29h', 'as29i', 'as29j', 'as29k', 'as29l', 'as29m', 'as29n', 'as29o', 'as29p', 'as29q', 'as29r'],
    ['as30'], ['as13'], ['s14', 'as14b', 'as14c'], ['s65', 'as65a', 'as65b', 'as65c'],
    ['s71', 'as71a', 'as71b', 'as71c', 'as71d', 'as71e', 'as71f'], ['as22'],
    ['s22a', 'as22a1', 'as22a2', 'as22a3', 'as22a4', 'as22a5', 'as22a6', 'as22a7'],
    ['s70'], # 代表時間運用題組
    ['s68', 'as68a1', 'as68a2', 'as68b1', 'as68b2', 'as68c1', 'as68c2', 'as68d1', 'as68d2', 'as68e'],
    ['s72', 'as72a', 'as72b', 'as72c', 'as72d', 'as72e', 'as72f', 'as72g', 'as72h', 'as72i', 'as72j', 'as72k', 'as72l'],
    ['s51'], # 代表實體霸凌題組
    ['s53'], # 代表網路霸凌題組
    ['as4d1'], ['as4d2'], ['as10'],
    ['s24', 'as24a', 'as24b', 'as24c', 'as24d', 'as24e', 'as24f', 'as24g', 'as24h', 'as24i', 'as24j'],
]

# 建立主題/題組映射: { "顯示名稱": [變項代碼列表] }
topic_groups = {}
# 建立所有可分析變項的扁平列表 (用於雙變項分析的獨立變項選擇)
all_analyzable_variables_flat = []

# 遍歷原始分組，建立 topic_groups 和 all_analyzable_variables_flat
for group in target_var_groups_raw:
    # 跳過特殊的代表性題組代碼，這些題組內容龐大，不適合直接加入下拉選單
    if group[0] in ['s70', 's51', 's53', 's22a', 's28', 's29', 's24', 's68', 's72']: continue

    group_items = []
    display_name = ""
    is_stem_group = False # 標記是否為以 's' 開頭的題組

    # 判斷是否為題組 (以 's' 加數字開頭)
    if re.match(r'^s\d+', group[0]):
        is_stem_group = True
        stem_code = group[0]
        # 嘗試從 id_map 獲取題幹描述，否則使用代碼本身
        stem_desc = id_map.get(stem_code, stem_code)
        display_name = f"題組: {stem_desc} ({stem_code})"
        group_items = group[1:] # 題組的子項目是從第二個元素開始
    else:
        # 這是獨立變項組 (可能只有一個元素)
        group_items = group

    # 過濾掉無效的變項代碼，或是在 DataFrame 中不存在對應欄位的代碼
    valid_items = [code for code in group_items if code in id_map and id_map.get(code) in df_s.columns]

    # 如果是題組且包含有效的子項目，則將其加入 topic_groups
    if is_stem_group and valid_items:
        topic_groups[display_name] = valid_items

    # 將所有有效的變項代碼加入扁平列表 (無論是否來自題組)
    all_analyzable_variables_flat.extend(valid_items)

# 加入自訂的主題 (跨越原始分組)
custom_topics = {
    "主題: 數位學習行為": ['as35a', 'as35b', 'as35c', 'as35d', 'as35e', 'as35f', 'as56a', 'as56b', 'as56d', 'as59a', 'as59b', 'as59c', 'as59d'],
    "主題: 數位素養": ['as60a', 'as60b', 'as60c', 'as61a', 'as61b', 'as61c', 'as61d', 'as61e', 'as61f', 'as61g', 'as61h', 'as61i'],
    "主題: 學習動機/興趣 (代理)": ['as14a', 'as19', 'as13', 'as14b', 'as14c'],
    "主題: 學業表現 (代理)": ['as20'],
    "主題: 自我概念/效能": ['as65a', 'as65b', 'as65c', 'as71a', 'as71b', 'as71c', 'as71d', 'as71e', 'as71f'],
    "主題: 網路沉迷風險": ['as41a', 'as41b', 'as41c', 'as41d', 'as41e', 'as41f', 'as41g', 'as41h', 'as41i', 'as41j'],
    # 可以視需要加入更多主題...
    # 例如: "主題: 家庭背景": ['as4d1', 'as4d2', 'as10'],
    # 注意：s28, s29, s72 等包含大量子項的題組，作為自訂主題可能一次顯示過多圖表
}

# 將自訂主題加入 topic_groups，並確保其變項也在扁平列表中
for topic_name, codes in custom_topics.items():
    # 過濾掉無效代碼或不存在的欄位
    valid_codes = [code for code in codes if code in id_map and id_map.get(code) in df_s.columns]
    if valid_codes:
        topic_groups[topic_name] = valid_codes
        # 將這些代碼也加入扁平列表 (如果還沒在裡面的話)
        all_analyzable_variables_flat.extend(valid_codes)

# 為所有獨立變項建立一個特殊的 "主題" 選項，方便在關聯分析中查找
all_analyzable_variables_flat = sorted(list(set(all_analyzable_variables_flat))) # 去重並排序
topic_groups["主題: 所有獨立變項"] = all_analyzable_variables_flat # 加入特殊主題

# --- 準備下拉選單選項 ---
# 選項 for 雙變項分析的具體變項選擇 (基於扁平列表)
# variable_options_flat = [{'label': f"{id_map.get(code, '未知')} ({code})", 'value': code}
#                          for code in all_analyzable_variables_flat]
# 選項 for 主題/題組描述性分析 和 雙變項分析的主題選擇
topic_group_options = [{'label': name, 'value': name} for name in sorted(topic_groups.keys())]

# --- 設定初始值 ---
# 描述性分析的初始主題
initial_topic_group = topic_group_options[0]['value'] if topic_group_options else None
# 關聯分析的初始主題 (預設為 "所有獨立變項" 或第一個主題)
default_relate_topic = next((name for name in sorted(topic_groups.keys()) if name == "主題: 所有獨立變項"), initial_topic_group)
# 根據初始主題獲取初始變項代碼列表
initial_relate_codes_x = topic_groups.get(default_relate_topic, [])
initial_relate_codes_y = topic_groups.get(default_relate_topic, [])
# 設定關聯分析中具體變項的初始選定值
initial_relate_x_var = initial_relate_codes_x[0] if initial_relate_codes_x else None
initial_relate_y_var = initial_relate_codes_y[1] if len(initial_relate_codes_y) > 1 else (initial_relate_codes_y[0] if initial_relate_codes_y else None)


# ==================================================
# App Layout 定義 (儀表板介面結構)
# ==================================================
app.layout = html.Div([
    # 標題
    html.H1("TIGPS 學生問卷資料探索儀表板"),

    # --- 分析類型選擇 ---
    html.Div([
        html.Label("選擇分析類型:", style={'fontWeight': 'bold'}),
        dcc.RadioItems(
            id='analysis-type-radio',
            options=[
                {'label': '主題/題組描述', 'value': 'describe_group'},
                {'label': '雙變項關聯', 'value': 'relate'}
            ],
            value='describe_group', # 預設選中"描述"
            labelStyle={'display': 'inline-block', 'marginRight': '20px'} # 讓選項水平排列
        ),
    ], style={'marginBottom': 20, 'borderBottom': '1px solid #eee', 'paddingBottom': '10px'}), # 底線分隔

    # --- 控制項區域 (會根據分析類型顯示或隱藏) ---
    html.Div([
        # --- 主題/題組描述控制項 ---
        html.Div(id='describe-group-controls', children=[
            html.Label("1. 選擇要描述的主題/題組:", style={'fontWeight': 'bold'}),
            dcc.Dropdown(
                id='topic-group-dropdown',
                options=topic_group_options, # 使用主題/題組選項
                value=initial_topic_group,   # 設定初始值
                clearable=False             # 不允許清空
            ),
            html.Label("2. (可選) 過濾顯示的子項目:", style={'fontWeight': 'bold', 'marginTop': '10px'}),
            dcc.Dropdown(
                id='variable-filter-multiselect',
                options=[],   # 選項由回呼函數動態生成
                value=[],     # 預設為空 (表示全選)
                multi=True    # 允許多選
            )
        ], style={'marginBottom': 15}), # 預設顯示 (因為初始分析類型是 describe_group)

        # --- 雙變項關聯控制項 ---
        html.Div(id='relate-controls', children=[
            # --- X軸選擇 ---
            html.Div([
                 html.Label("1. 選擇 X 軸 主題/題組:", style={'fontWeight': 'bold'}),
                 dcc.Dropdown(id='topic-group-dropdown-x', options=topic_group_options, value=default_relate_topic, clearable=False),
                 html.Label("2. 選擇 X 軸 變項:", style={'fontWeight': 'bold', 'marginTop': '5px'}),
                 dcc.Dropdown(id='relate-x-dropdown', options=[], value=initial_relate_x_var, clearable=False) # 選項動態生成
            ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top', 'marginRight': '2%'}), # 左右排列

            # --- Y軸選擇 ---
            html.Div([
                html.Label("3. 選擇 Y 軸 主題/題組:", style={'fontWeight': 'bold'}),
                dcc.Dropdown(id='topic-group-dropdown-y', options=topic_group_options, value=default_relate_topic, clearable=False),
                html.Label("4. 選擇 Y 軸 變項:", style={'fontWeight': 'bold', 'marginTop': '5px'}),
                dcc.Dropdown(id='relate-y-dropdown', options=[], value=initial_relate_y_var, clearable=False) # 選項動態生成
            ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top', 'float': 'right'}), # 左右排列

            # --- 圖表類型選擇 ---
            html.Div([
                html.Label("5. 選擇圖表類型:", style={'fontWeight': 'bold', 'marginTop': '15px'}),
                dcc.RadioItems(
                    id='relate-plot-type',
                    options=[
                        {'label': '盒鬚圖 (Y軸需轉分數)', 'value': 'boxplot'},
                        {'label': '交叉表熱圖 (百分比)', 'value': 'heatmap'},
                        {'label': '堆疊長條圖 (次數)', 'value': 'stackedbar'}
                    ],
                    value='boxplot', # 預設圖表類型
                    labelStyle={'display': 'inline-block', 'marginRight': '20px'}
                )
            ], style={'clear': 'both', 'paddingTop': '15px'}) # 清除浮動，確保在下方顯示
        ], style={'display': 'none', 'marginBottom': 15}), # 關聯控制項預設隱藏
    ], style={'padding': '20px', 'border': '1px solid #ddd', 'borderRadius': '5px', 'backgroundColor': '#f9f9f9', 'marginBottom': '20px'}), # 控制項區域的整體樣式

    html.Hr(), # 分隔線

    # --- 輸出區域 ---
    html.Div([
        html.H3("分析結果:", style={'marginBottom': '10px'}),
        # 用於顯示主題/題組描述的容器 (初始為空)
        html.Div(id='describe-output-container'),
        # 用於顯示雙變項關聯的容器 (初始隱藏)
        html.Div(id='relate-output-container', children=[
             # 顯示統計文字
             html.Div(id='stats-output-relate', style={'whiteSpace': 'pre-wrap', 'fontFamily': 'monospace', 'border': '1px solid #eee', 'padding': '10px', 'marginBottom': '20px', 'backgroundColor': '#fafafa'}),
             # 顯示圖表
             dcc.Graph(id='plot-output-relate', figure=go.Figure()) # 初始顯示空圖
        ], style={'display': 'none'}) # 關聯輸出區域預設隱藏
    ])
])

# ==================================================
# Callbacks 定義 (儀表板的互動邏輯)
# ==================================================

# --- Callback 1: 根據分析類型顯示/隱藏控制項和輸出區域 ---
@app.callback(
    # 輸出：控制四個區域的 style 屬性 (顯示/隱藏)
    Output('describe-group-controls', 'style'),
    Output('relate-controls', 'style'),
    Output('describe-output-container', 'style'),
    Output('relate-output-container', 'style'),
    # 輸入：分析類型 RadioItems 的值
    Input('analysis-type-radio', 'value')
)
def toggle_controls_and_outputs(analysis_type):
    """根據選擇的分析類型，顯示或隱藏對應的控制項和輸出區域"""
    if analysis_type == 'describe_group':
        # 顯示描述控制項和輸出，隱藏關聯控制項和輸出
        return ({'marginBottom': 15}, {'display': 'none', 'marginBottom': 15},
                {'display': 'block'}, {'display': 'none'})
    elif analysis_type == 'relate':
        # 隱藏描述控制項和輸出，顯示關聯控制項和輸出
        return ({'display': 'none', 'marginBottom': 15}, {'marginBottom': 15},
                {'display': 'none'}, {'display': 'block'})
    else: # 預設情況或意外值，顯示描述模式
        return ({'marginBottom': 15}, {'display': 'none', 'marginBottom': 15},
                {'display': 'block'}, {'display': 'none'})

# --- Callback 2: 動態更新描述性分析的變項過濾器選項 ---
@app.callback(
    # 輸出：過濾器下拉選單的選項和當前值
    Output('variable-filter-multiselect', 'options'),
    Output('variable-filter-multiselect', 'value'), # 重設選定值
    # 輸入：主題/題組下拉選單的值
    Input('topic-group-dropdown', 'value')
)
def update_variable_filter_options(selected_topic_group_name):
    """當選擇的主題/題組改變時，更新多選過濾器的選項，並清空其選定值"""
    if not selected_topic_group_name or selected_topic_group_name not in topic_groups:
        return [], [] # 無效選擇，返回空

    # 從 topic_groups 字典獲取該主題下的變項代碼列表
    codes_in_group = topic_groups[selected_topic_group_name]
    # 生成下拉選單選項，格式為 {'label': '說明 (代碼)', 'value': '代碼'}
    options = [{'label': f"{id_map.get(code, '未知')} ({code})", 'value': code}
               for code in codes_in_group if code in id_map] # 確保代碼有效

    return options, [] # 返回選項列表，並清空已選值 (代表預設全選)

# --- Callback 3: 更新主題/題組描述輸出 (*** 修改: 加入過濾 ***) ---
@app.callback(
    Output('describe-output-container', 'children'),
    Input('analysis-type-radio', 'value'),
    Input('topic-group-dropdown', 'value'),
    Input('variable-filter-multiselect', 'value')
)
def update_describe_group_outputs(analysis_type, selected_topic_group_name, selected_variables):
    if analysis_type != 'describe_group' or not selected_topic_group_name or selected_topic_group_name not in topic_groups:
        return html.P("請選擇一個主題或題組進行描述性分析。")

    all_codes_in_group = topic_groups[selected_topic_group_name]
    codes_to_display = selected_variables if selected_variables else all_codes_in_group
    output_elements = [html.H4(f"主題/題組：{selected_topic_group_name}")]

    if not codes_to_display:
        output_elements.append(html.P("此主題/題組下沒有可顯示的變項。"))
        return output_elements

    for code in codes_to_display:
        if code not in all_codes_in_group: continue
        col_name = id_map.get(code)
        if not col_name or col_name not in df_s.columns:
            output_elements.append(html.Div([ html.Hr(), html.P(f"錯誤：找不到變項 '{code}' / '{col_name}'。", style={'color': 'red'}) ]))
            continue

        # *** 過濾資料: 僅保留不包含在排除列表中的值 ***
        df_filtered = df_s[~df_s[col_name].isin(values_to_exclude)].copy()
        # 如果過濾後沒有數據，則跳過此變項
        if df_filtered.empty:
            output_elements.append(html.Div([ html.Hr(), html.P(f"子項目: {col_name} ({code}) - 過濾排除值後無有效數據。") ]))
            continue

        # --- 在過濾後的資料上進行計算和繪圖 ---
        stats_text_list = []
        stats_text_list.append(f"--- 子項目: {col_name} ({code}) [已排除無效值] ---") # 提示已過濾

        value_counts_abs = df_filtered[col_name].value_counts().sort_index()
        value_counts_rel = df_filtered[col_name].value_counts(normalize=True).sort_index()
        # *** 注意：get_option_order 現在也排除了無效值 ***
        option_order = get_option_order(code)
        valid_order = None

        try:
            if option_order: # option_order 現在只包含有效選項
                 current_index_set = set(value_counts_abs.index)
                 # valid_order 現在應該與 option_order 相同 (如果資料中有這些選項)
                 valid_order = [opt for opt in option_order if opt in current_index_set]
                 if valid_order:
                     value_counts_abs = value_counts_abs.reindex(valid_order, fill_value=0) # fill_value=0 處理排序後可能出現的NaN
                     value_counts_rel = value_counts_rel.reindex(valid_order, fill_value=0)
        except Exception as e:
            stats_text_list.append(f"警告：排序時出錯: {e}。")

        stats_df = pd.DataFrame({'次數': value_counts_abs, '比例': value_counts_rel})
        stats_text_list.append("\n次數分佈:")
        stats_text_list.append(stats_df.to_string(float_format='{:.1%}'.format))

        fig = go.Figure()
        try:
            # *** 使用過濾後的 df_filtered 進行繪圖 ***
            fig = px.histogram(df_filtered, x=col_name, title=f"分佈：{col_name}",
                               category_orders={col_name: valid_order} if valid_order else None)
            fig.update_layout(xaxis_title=col_name, yaxis_title="人數", height=300, margin=dict(t=30, b=0))
            fig.update_xaxes(type='category')
        except Exception as e:
            error_msg = f"錯誤：繪圖時發生錯誤: {e}"; stats_text_list.append(f"\n{error_msg}"); fig.update_layout(title=error_msg)

        item_div = html.Div([ html.Hr(), html.Pre("\n".join(stats_text_list), style={'whiteSpace': 'pre-wrap', 'fontFamily': 'monospace', 'fontSize': 'small'}), dcc.Graph(figure=fig) ], style={'marginBottom': '20px', 'padding': '10px', 'border': '1px solid #eee'})
        output_elements.append(item_div)
    return output_elements


# --- Callback 4: 動態更新 X 軸變項下拉選單的選項 ---
@app.callback(
    # 輸出：X 軸變項下拉選單的選項和當前值
    Output('relate-x-dropdown', 'options'),
    Output('relate-x-dropdown', 'value'),
    # 輸入：X 軸主題/題組下拉選單的值
    Input('topic-group-dropdown-x', 'value')
)
def update_relate_x_variable_options(selected_topic_group_name_x):
    """當關聯分析中 X 軸的主題/題組改變時，更新 X 軸具體變項下拉選單的選項"""
    if not selected_topic_group_name_x or selected_topic_group_name_x not in topic_groups:
        return [], None # 無效選擇，返回空

    # 獲取該主題下的變項代碼
    codes_in_group = topic_groups[selected_topic_group_name_x]
    # 生成選項列表
    options = [{'label': f"{id_map.get(code, '未知')} ({code})", 'value': code}
               for code in codes_in_group if code in id_map]

    # 預設選中該組的第一個變項
    default_value = options[0]['value'] if options else None
    return options, default_value

# --- Callback 5: 動態更新 Y 軸變項下拉選單的選項 ---
@app.callback(
    # 輸出：Y 軸變項下拉選單的選項和當前值
    Output('relate-y-dropdown', 'options'),
    Output('relate-y-dropdown', 'value'),
    # 輸入：Y 軸主題/題組下拉選單的值
    Input('topic-group-dropdown-y', 'value')
)
def update_relate_y_variable_options(selected_topic_group_name_y):
    """當關聯分析中 Y 軸的主題/題組改變時，更新 Y 軸具體變項下拉選單的選項"""
    if not selected_topic_group_name_y or selected_topic_group_name_y not in topic_groups:
        return [], None # 無效選擇，返回空

    codes_in_group = topic_groups[selected_topic_group_name_y]
    options = [{'label': f"{id_map.get(code, '未知')} ({code})", 'value': code}
               for code in codes_in_group if code in id_map]

    # 預設選中該組的第一個變項
    default_value = options[0]['value'] if options else None
    # (可選邏輯) 嘗試避免 Y 軸預設選中與 X 軸相同的變項 (如果 Y 選項多於1個)
    # if len(options) > 1 and default_value == initial_relate_x_var: # 需要讀取 X 的當前值，用 State
    #     default_value = options[1]['value']

    return options, default_value


# --- Callback 6: 更新雙變項關聯輸出 (*** 修改: 加入過濾 ***) ---
@app.callback(
    Output('plot-output-relate', 'figure'), Output('stats-output-relate', 'children'),
    Input('analysis-type-radio', 'value'), Input('relate-x-dropdown', 'value'),
    Input('relate-y-dropdown', 'value'), Input('relate-plot-type', 'value'),
    State('topic-group-dropdown-x', 'value'), State('topic-group-dropdown-y', 'value'),
    prevent_initial_call=True
)
def update_relate_outputs(analysis_type, x_code, y_code, plot_type, topic_x_name, topic_y_name):
    if analysis_type != 'relate' or not x_code or not y_code:
        return go.Figure(), "請先選擇 X 軸和 Y 軸的主題/題組，然後選擇具體變項。"

    x_col = id_map.get(x_code) if x_code in id_map else (x_code if x_code in df_s.columns else None)
    y_col = id_map.get(y_code) if y_code in id_map else (y_code if y_code in df_s.columns else None)

    if not x_col or x_col not in df_s.columns or not y_col or y_col not in df_s.columns:
        return go.Figure(), f"錯誤：找不到變項代碼或資料欄位 ({x_code}/{x_col} 或 {y_code}/{y_col})。"

    if x_code == y_code:
         return go.Figure(), "錯誤：X 軸和 Y 軸不能選擇相同的變項。"

    stats_text_list = []
    stats_text_list.append(f"===== 雙變項關聯分析 =====")
    stats_text_list.append(f"X 軸: {x_col} ({x_code}) [來自: {topic_x_name}]")
    stats_text_list.append(f"Y 軸: {y_col} ({y_code}) [來自: {topic_y_name}]")
    stats_text_list.append(f"圖表類型: {plot_type}")
    stats_text_list.append(f"[已排除含無效值的資料列]") # 提示已過濾

    fig = go.Figure()

    # *** 過濾資料: 排除在 X 或 Y 欄位中包含無效值的資料列 ***
    df_filtered = df_s[
        (~df_s[x_col].isin(values_to_exclude)) &
        (~df_s[y_col].isin(values_to_exclude))
    ].copy()

    # *** 在過濾後的資料上進行操作 ***
    temp_df = df_filtered[[x_col, y_col]].dropna() # dropna 以處理非標籤類型的缺失值(雖然可能不多)

    if temp_df.empty:
         return go.Figure(), "\n".join(stats_text_list) + "\n錯誤：過濾並移除遺漏值後，沒有足夠的數據進行分析。"

    try:
        # *** 注意：get_option_order 現在也排除了無效值 ***
        option_order_x = get_option_order(x_code)
        option_order_y = get_option_order(y_code)
        # 在過濾後的 temp_df 上獲取有效的 unique 值來排序
        valid_order_x = [opt for opt in option_order_x if opt in temp_df[x_col].unique()] if option_order_x else None
        valid_order_y = [opt for opt in option_order_y if opt in temp_df[y_col].unique()] if option_order_y else None

        # --- 根據圖表類型處理 (核心邏輯不變，但使用 temp_df) ---
        if plot_type == 'boxplot':
            stats_text_list.append("\n--- 盒鬚圖分析 ---")
            # *** 注意：get_label_to_score_map 現在也排除了無效值 ***
            score_map_y = get_label_to_score_map(y_code)
            if not score_map_y:
                msg = f"錯誤：Y 軸 '{y_col}' 無法轉換為有效分數。"; stats_text_list.append(msg); fig.update_layout(title=msg)
                return fig, "\n".join(stats_text_list)

            y_score_col = f"{y_code}_score"
            # 在已經過濾的 temp_df 上計算分數
            temp_df.loc[:, y_score_col] = temp_df[y_col].map(score_map_y)
            temp_df = temp_df.dropna(subset=[x_col, y_score_col]) # 移除可能因映射產生的 NA

            if temp_df.empty:
                 msg = "錯誤：轉換分數後無數據。"; stats_text_list.append(msg); fig.update_layout(title=msg)
                 return fig, "\n".join(stats_text_list)

            fig = px.box(temp_df, x=x_col, y=y_score_col, title=f"'{x_col}' 對 '{y_col}' (分數)",
                         category_orders={x_col: valid_order_x} if valid_order_x else None, points=False)
            fig.update_layout(xaxis_title=f"{x_col}", yaxis_title=f"{y_col} (分數)")

            stats_text_list.append("\n分組統計 (Y分數):")
            grouped_stats = temp_df.groupby(x_col)[y_score_col].agg(['mean', 'median', 'std', 'count']).round(2)
            if valid_order_x:
                 try: grouped_stats = grouped_stats.reindex(valid_order_x)
                 except Exception: pass
            stats_text_list.append(grouped_stats.to_string())

        elif plot_type == 'heatmap':
            stats_text_list.append("\n--- 交叉表熱圖 (行百分比) ---")
            # 在過濾後的 temp_df 上計算交叉表
            crosstab_rel = pd.crosstab(temp_df[x_col], temp_df[y_col], normalize='index')
            if valid_order_x:
                try: crosstab_rel = crosstab_rel.reindex(valid_order_x)
                except Exception: pass
            if valid_order_y:
                try: crosstab_rel = crosstab_rel.reindex(columns=valid_order_y)
                except Exception: pass
            crosstab_rel = crosstab_rel.fillna(0)
            fig = px.imshow(crosstab_rel, text_auto=".1%", title=f"'{x_col}' vs '{y_col}' (行百分比)",
                            labels=dict(x=y_col, y=x_col, color="比例"),
                            x=crosstab_rel.columns, y=crosstab_rel.index, aspect="auto",
                            color_continuous_scale=px.colors.sequential.Viridis)
            fig.update_xaxes(side="top")
            stats_text_list.append("\n交叉表數據 (行百分比):"); stats_text_list.append(crosstab_rel.round(3).to_string())

        elif plot_type == 'stackedbar':
            stats_text_list.append("\n--- 堆疊長條圖 (次數) ---")
            # 在過濾後的 temp_df 上計算交叉表
            crosstab_abs = pd.crosstab(temp_df[x_col], temp_df[y_col])
            if valid_order_x:
                try: crosstab_abs = crosstab_abs.reindex(valid_order_x)
                except Exception: pass
            if valid_order_y:
                try: crosstab_abs = crosstab_abs.reindex(columns=valid_order_y)
                except Exception: pass
            crosstab_abs = crosstab_abs.fillna(0)
            plot_df = crosstab_abs.reset_index().melt(id_vars=x_col, var_name=y_col, value_name='人數')
            cat_orders = {};
            if valid_order_x: cat_orders[x_col] = valid_order_x
            if valid_order_y: cat_orders[y_col] = valid_order_y
            fig = px.bar(plot_df, x=x_col, y='人數', color=y_col, title=f"'{x_col}' vs '{y_col}' (次數)",
                         category_orders=cat_orders if cat_orders else None, barmode='stack')
            fig.update_layout(xaxis_title=f"{x_col}", yaxis_title="人數")
            stats_text_list.append("\n交叉表數據 (次數):"); stats_text_list.append(crosstab_abs.astype(int).to_string())

        else:
            msg = f"錯誤：未知圖表 '{plot_type}'。" ; stats_text_list.append(msg); fig.update_layout(title=msg)

    except Exception as e:
        error_msg = f"錯誤：處理關聯時發生錯誤: {e}"; stats_text_list.append(f"\n{error_msg}"); fig = go.Figure(); fig.update_layout(title=error_msg)

    return fig, "\n".join(stats_text_list)

# ==================================================
# 執行 App
# ==================================================
if __name__ == '__main__':
    print("儀表板準備啟動...")
    # 檢查資料載入狀態
    data_loaded = not df_s.empty if 'df_s' in locals() else False
    id_map_loaded = bool(id_map) if 'id_map' in locals() else False
    value_map_loaded = bool(value_map) if 'value_map' in locals() else False
    print(f"資料載入狀態: df_s={'成功' if data_loaded else '失敗'}, id_map={'成功' if id_map_loaded else '失敗'}, value_map={'成功' if value_map_loaded else '失敗'}")
    print(f"找到 {len(all_analyzable_variables_flat)} 個獨立可分析變項。")
    print(f"找到 {len(topic_group_options)} 個主題/題組。")
    if not topic_group_options:
        print("警告：缺少主題/題組選項，儀表板可能無法正常運作。")
    # 啟動 Dash 伺服器 (使用 debug=True 方便開發時調試)
    app.run(debug=True)