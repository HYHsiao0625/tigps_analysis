# src/dashboard_app.py

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import scipy.stats as stats
import os

# --- 0. 基本設定與中文字體 ---
try:
    # 嘗試設定多種常見中文字體，增加通用性
    plt.rcParams['font.sans-serif'] = [
        'Microsoft JhengHei', 'Arial Unicode MS', 'Microsoft YaHei', 
        'SimHei', 'PingFang HK', 'Heiti TC', 'sans-serif'
    ]
    plt.rcParams['axes.unicode_minus'] = False
    # st.sidebar.success("已嘗試設定Matplotlib中文字體。") # 稍後在主應用中顯示
except Exception as e:
    # st.sidebar.error(f"設定Matplotlib中文字體時發生錯誤: {e}") # 稍後在主應用中顯示
    pass

# --- 檔案路徑定義 (相對於專案根目錄 tigps_analysis/) ---
# 假設您是從 tigps_analysis/ 目錄下執行 streamlit run src/dashboard_app.py
RAW_STUDENT_DATA_PATH = 'data/TIGPSw1_s_descriptive_labeled.csv'

# --- 常量與順序定義 (從分析腳本複製過來) ---
grouping_col_name = "你上學期的平均成績大約如何?"

# 數值型特徵列表
numerical_feature_cols_all = [
    "完成學校功課(查找完成作業需要的資料)",  # as35a
    "課外的學習(各種線上付費或免費的課程)"   # as35b
]
# 類別型特徵列表
categorical_feature_cols_all = [
    "電腦(含桌機或筆電)",                         # as56a
    "智慧型手機",                                 # as56b
    "平板或電子書閱讀器(iPad, Kindle...)",        # as56d
    "讀書或寫作業時,我會先將無關的網站、即時通訊、手機APP或提醒聲音關掉", # as59a
    "我能要求自己先完成作業或讀書進度後,才能去看我喜歡的網站或玩手機。",       # as59b
    "我會運用學習平台上的儀表板,了解自己的認真或表現情況(...)",             # as59c
    "我會運用學習平台以外的軟體(如:Google日曆、Forrest、Notion、Anki等),安排我的學習進度。", # as59d
    "我喜歡學校。",                                 # as14a
    "你跟得上學校課業進度嗎?"                       # as19
]

all_selected_cols_for_processing = [grouping_col_name] + numerical_feature_cols_all + categorical_feature_cols_all

# 順序定義
grade_order = ['全班五名以內', '全班六至十名', '全班十一至二十名', '全班二十一至三十名', '全班三十名以後']
time_mapping = { "沒有": 0.0, "0.5小時以內": 0.25, "0.5-1小時": 0.75, "1-1.5小時": 1.25, "1.5-2小時": 1.75, "2-2.5小時": 2.25, "2.5-3小時": 2.75, "3-3.5小時": 3.25, "3.5-4小時": 3.75, "4-4.5小時": 4.25, "4.5-5小時": 4.75, "5小時以上": 5.5 }
values_to_replace_time = ["此卷未答", "跳答", "系統遺漏值"]
comp_freq_order = ['幾乎每天', '每週三四次', '每週一兩次', '每月三四次', '每月一兩次', '一年幾次', '幾乎沒有', '沒有這項設備']
values_to_replace_freq = ["此卷未答", "系統遺漏值"]
agreement_order_s59 = ['很符合', '符合', '不符合', '很不符合']
values_to_replace_manage = ["系統遺漏值", "此卷未答"] # 通用遺失值
agreement_order_s14a = ['很同意', '同意', '不同意', '很不同意']
progress_order_s19 = ['我的進度超前', '大部分都跟得上', '只落後一點點,很快就跟上了', '我有點落後,可能跟得上', '我落後很多,很難跟得上']

category_orders_map = {
    "電腦(含桌機或筆電)": comp_freq_order, "智慧型手機": comp_freq_order, "平板或電子書閱讀器(iPad, Kindle...)": comp_freq_order,
    "讀書或寫作業時,我會先將無關的網站、即時通訊、手機APP或提醒聲音關掉": agreement_order_s59,
    "我能要求自己先完成作業或讀書進度後,才能去看我喜歡的網站或玩手機。": agreement_order_s59,
    "我會運用學習平台上的儀表板,了解自己的認真或表現情況(...)": agreement_order_s59,
    "我會運用學習平台以外的軟體(如:Google日曆、Forrest、Notion、Anki等),安排我的學習進度。": agreement_order_s59,
    "我喜歡學校。": agreement_order_s14a, "你跟得上學校課業進度嗎?": progress_order_s19
}
palettes_for_categorical = ["muted", "pastel", "deep", "colorblind", "bright", "tab10"] # Corrected here


# --- 1. 數據載入與預處理函數 ---
@st.cache_data # Streamlit 快取機制，加速數據載入和預處理
def load_and_preprocess_data(raw_file_path):
    try:
        df_raw = pd.read_csv(raw_file_path, low_memory=False)
        st.sidebar.success(f"成功從 {raw_file_path} 載入原始數據。")
    except FileNotFoundError:
        st.error(f"錯誤：找不到原始數據檔案 {raw_file_path}。請確保檔案路徑正確。")
        return None

    st.sidebar.info("正在進行數據預處理...")
    # 確保只選取我們定義好的欄位，避免潛在的额外欄位問題
    cols_to_select_initially = [col for col in all_selected_cols_for_processing if col in df_raw.columns]
    if len(cols_to_select_initially) != len(all_selected_cols_for_processing):
        st.sidebar.warning("部分定義的欄位在原始數據中缺失，將只處理存在的欄位。")
        missing_cols_in_raw = [col for col in all_selected_cols_for_processing if col not in df_raw.columns]
        st.sidebar.json({"定義的欄位但原始數據中缺失": missing_cols_in_raw})


    df_processed = df_raw[cols_to_select_initially].copy()

    # A. 處理分群變項
    if grouping_col_name in df_processed.columns:
        df_processed[grouping_col_name] = df_processed[grouping_col_name].replace(["系統遺漏值", "此卷未答", "我不知道"], np.nan)
        grade_dtype = pd.CategoricalDtype(categories=grade_order, ordered=True)
        df_processed[grouping_col_name] = df_processed[grouping_col_name].astype(grade_dtype)

    # B. 處理時間型數值特徵
    for col in numerical_feature_cols_all:
        if col in df_processed.columns:
            df_processed[col] = df_processed[col].replace(values_to_replace_time, np.nan)
            mapped_col = df_processed[col].map(time_mapping)
            # combine_first 用於保留那些不在 mapping 中的值 (例如已經是 NaN 的)
            df_processed[col] = mapped_col.combine_first(df_processed[col])
            df_processed[col] = pd.to_numeric(df_processed[col], errors='coerce')

    # C. 處理設備使用頻率類別特徵
    freq_cols_to_process = ["電腦(含桌機或筆電)", "智慧型手機", "平板或電子書閱讀器(iPad, Kindle...)"]
    for col in freq_cols_to_process:
        if col in df_processed.columns:
            df_processed[col] = df_processed[col].replace(values_to_replace_freq, np.nan)
            comp_freq_dtype = pd.CategoricalDtype(categories=comp_freq_order, ordered=True)
            df_processed[col] = df_processed[col].astype(comp_freq_dtype)
    
    # D. 處理線上學習自我管理類別特徵 (as59系列)
    s59_cols_to_process = [
        "讀書或寫作業時,我會先將無關的網站、即時通訊、手機APP或提醒聲音關掉",
        "我能要求自己先完成作業或讀書進度後,才能去看我喜歡的網站或玩手機。",
        "我會運用學習平台上的儀表板,了解自己的認真或表現情況(...)",
        "我會運用學習平台以外的軟體(如:Google日曆、Forrest、Notion、Anki等),安排我的學習進度。"
    ]
    for col in s59_cols_to_process:
         if col in df_processed.columns:
            df_processed[col] = df_processed[col].replace(values_to_replace_manage, np.nan)
            agreement_dtype_s59 = pd.CategoricalDtype(categories=agreement_order_s59, ordered=True)
            df_processed[col] = df_processed[col].astype(agreement_dtype_s59)

    # E. 處理 "我喜歡學校。" (as14a)
    col_as14a = "我喜歡學校。"
    if col_as14a in df_processed.columns:
        df_processed[col_as14a] = df_processed[col_as14a].replace(values_to_replace_manage, np.nan)
        agreement_dtype_s14a = pd.CategoricalDtype(categories=agreement_order_s14a, ordered=True)
        df_processed[col_as14a] = df_processed[col_as14a].astype(agreement_dtype_s14a)

    # F. 處理 "你跟得上學校課業進度嗎?" (as19)
    col_as19 = "你跟得上學校課業進度嗎?"
    if col_as19 in df_processed.columns:
        df_processed[col_as19] = df_processed[col_as19].replace(values_to_replace_manage, np.nan)
        progress_dtype_s19 = pd.CategoricalDtype(categories=progress_order_s19, ordered=True)
        df_processed[col_as19] = df_processed[col_as19].astype(progress_dtype_s19)
    
    st.sidebar.success("數據預處理完畢。")
    return df_processed

# --- 2. 主應用介面 ---
st.set_page_config(layout="wide", page_title="數位學習樣貌與學業關聯分析")

# 嘗試設定字體，並在側邊欄顯示結果
try:
    plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'Arial Unicode MS', 'Microsoft YaHei', 'SimHei', 'PingFang HK', 'Heiti TC', 'sans-serif']
    plt.rcParams['axes.unicode_minus'] = False
    st.sidebar.success("Matplotlib 中文字體已嘗試設定。")
except Exception as e:
    st.sidebar.error(f"設定 Matplotlib 中文字體時發生錯誤: {e}")


st.title("目標一：描繪數位學習樣貌與學業關聯的初步圖像")
st.markdown(f"""
本儀表板旨在呈現不同學業成就群體的學生，在各項數位學習行為、素養及學習動機等特徵上的初步畫像。
主要的分群方式是依據學生「**{grouping_col_name}**」的回答。
""")

# 載入並預處理數據
df_display = load_and_preprocess_data(RAW_STUDENT_DATA_PATH)

if df_display is not None:
    alpha = 0.05 # 統計檢定顯著水準

   # --- A. 數值型特徵分析與呈現 ---
    st.header("A. 數值型特徵分析")
    for num_col in numerical_feature_cols_all:
        if num_col in df_display.columns:
            st.subheader(f"特徵：{num_col}")
            
            # 描述性統計表格
            desc_stats = df_display.groupby(grouping_col_name, observed=True)[num_col].agg(
                ['count', 'mean', 'median', 'std']
            ).round(2)
            st.write(f"各「{grouping_col_name}」群組在「{num_col}」上的統計：")
            st.dataframe(desc_stats)

            # 盒鬚圖
            fig_num, ax_num = plt.subplots(figsize=(10, 6)) # 創建 fig, ax
            sns.boxplot(x=grouping_col_name, y=num_col, data=df_display, 
                        order=grade_order, 
                        hue=grouping_col_name, # Added to address FutureWarning
                        palette="viridis", 
                        ax=ax_num,
                        legend=False) # Added to address FutureWarning
            ax_num.set_title(f'不同成績組別在「{num_col}」上的分佈', fontsize=14)
            ax_num.set_xlabel(grouping_col_name, fontsize=10)
            ax_num.set_ylabel(f"{num_col} (小時)", fontsize=10) # 假設單位是小時
            ax_num.tick_params(axis='x', rotation=45, labelsize=8) # Corrected: removed ha='right'
            ax_num.tick_params(axis='y', labelsize=8)
            plt.tight_layout()
            st.pyplot(fig_num)
            plt.close(fig_num) # 關閉圖表，釋放記憶體

            # 統計檢定
            st.markdown("**統計檢定結果：**")
            grouped_data_for_test = [
                df_display[df_display[grouping_col_name] == group_level][num_col].dropna()
                for group_level in df_display[grouping_col_name].cat.categories
            ]
            grouped_data_for_test = [g for g in grouped_data_for_test if not g.empty]

            if len(grouped_data_for_test) >= 2:
                # ANOVA
                try:
                    f_statistic, p_value_anova = stats.f_oneway(*grouped_data_for_test)
                    st.markdown(f"* **ANOVA 檢定**: F統計量 = {f_statistic:.2f}, p-value = {p_value_anova:.4f}")
                    if p_value_anova < alpha:
                        st.markdown(f"    * 結論: **顯著差異** (p < {alpha})。不同成績組別在「{num_col}」上的平均數存在顯著差異。建議進行 post-hoc 檢定。")
                    else:
                        st.markdown(f"    * 結論: **無顯著差異** (p >= {alpha})。")
                except Exception as e:
                    st.markdown(f"* ANOVA 檢定執行錯誤: {e}")
                # Kruskal-Wallis
                try:
                    h_statistic, p_value_kruskal = stats.kruskal(*grouped_data_for_test)
                    st.markdown(f"* **Kruskal-Wallis H 檢定**: H統計量 = {h_statistic:.2f}, p-value = {p_value_kruskal:.4f}")
                    if p_value_kruskal < alpha:
                        st.markdown(f"    * 結論: **顯著差異** (p < {alpha})。不同成績組別在「{num_col}」上的分佈（中位數）存在顯著差異。建議進行 post-hoc 檢定。")
                    else:
                        st.markdown(f"    * 結論: **無顯著差異** (p >= {alpha})。")
                except Exception as e:
                    st.markdown(f"* Kruskal-Wallis 檢定執行錯誤: {e}")
            else:
                st.markdown("* 有效數據組別少於2組，無法進行 ANOVA 或 Kruskal-Wallis 檢定。")
            
            # 文字解讀區塊 (請您填充)
            st.markdown(f"""
            **初步文字解讀 ({num_col})**: 
            * *(例如：從圖表和統計數據看，成績「全班五名以內」的學生在此項目的平均值/中位數為 X，而「全班三十名以後」的為 Y...)*
            * *(結合p值：ANOVA/Kruskal-Wallis 檢定結果顯示這些差異在統計上是/不是顯著的...)*
            * *(您的觀察與推論...)*
            """)
            st.markdown("---")
        else:
            st.warning(f"數值型欄位 {num_col} 未在載入的數據中找到。")

    # --- B. 類別型特徵分析與呈現 ---
    st.header("B. 類別型特徵分析")
    palette_idx = 0
    for cat_col in categorical_feature_cols_all: # 確保此列表已定義
        if cat_col in df_display.columns:
            # ... (table display code remains the same) ...
            st.subheader(f"特徵：{cat_col}")
            cat_analysis_table = df_display.groupby(grouping_col_name, observed=True)[cat_col].value_counts(
                normalize=True, dropna=False 
            ).mul(100).round(2).unstack(fill_value=0)

            # --- 新增：轉換 NaN 欄位名稱為字串 ---
            nan_col_str_representation = "遺失值(NaN)" # 用於代表 NaN 欄位的字串
            new_column_names = []
            original_nan_col_name = None # 用於記錄原始的 np.nan (如果存在)

            for col_name in cat_analysis_table.columns:
                if pd.isna(col_name): # 檢查是否為 np.nan
                    new_column_names.append(nan_col_str_representation)
                    original_nan_col_name = col_name # 記下它，方便後續排序
                else:
                    new_column_names.append(col_name)
            cat_analysis_table.columns = new_column_names
            # --- 轉換結束 ---
            
            current_hue_order = category_orders_map.get(cat_col, None) 
            if current_hue_order is None and isinstance(df_display[cat_col].dtype, pd.CategoricalDtype):
                 current_hue_order = df_display[cat_col].dtype.categories.tolist()

            if current_hue_order:
                # 根據 current_hue_order 建立基礎的排序列表
                ordered_columns = [col for col in current_hue_order if col in cat_analysis_table.columns]
                
                # 如果原始數據中有 NaN 類別 (現在被轉換為 nan_col_str_representation)
                # 且這個代表 NaN 的字串欄位存在於表格中，且尚未被加入到 ordered_columns
                if nan_col_str_representation in cat_analysis_table.columns and \
                   nan_col_str_representation not in ordered_columns:
                    ordered_columns.append(nan_col_str_representation)
                
                # 確保所有實際存在的欄位都被包含，以防萬一
                for col_name_in_table in cat_analysis_table.columns:
                    if col_name_in_table not in ordered_columns:
                        ordered_columns.append(col_name_in_table)
                
                cat_analysis_table = cat_analysis_table[ordered_columns] # 使用最終的欄位列表重新排序
            
            st.write(f"各「{grouping_col_name}」群組在「{cat_col}」上的選項百分比 (%)：")
            st.dataframe(cat_analysis_table) # 現在應該沒問題了

            # 分組長條圖
            plot_data_cat = df_display.groupby(grouping_col_name, observed=True)[cat_col].value_counts(
                normalize=True 
            ).mul(100).rename('percentage').reset_index()

            fig_cat, ax_cat = plt.subplots(figsize=(12, 7))
            sns.barplot(x=grouping_col_name, y='percentage', hue=cat_col, data=plot_data_cat,
                        order=grade_order, hue_order=current_hue_order, 
                        palette=palettes_for_categorical[palette_idx % len(palettes_for_categorical)], ax=ax_cat)
            palette_idx += 1
            ax_cat.set_title(f'不同成績組別在「{cat_col}」上的選項百分比\n(基於有效回答者)', fontsize=14)
            ax_cat.set_xlabel(grouping_col_name, fontsize=10)
            ax_cat.set_ylabel('百分比 (%)', fontsize=10)
            ax_cat.tick_params(axis='x', rotation=45, labelsize=8) # Corrected: removed ha='right'
            ax_cat.tick_params(axis='y', labelsize=8)
            ax_cat.legend(title=cat_col, bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=8, title_fontsize='9')
            plt.tight_layout(rect=[0, 0, 0.85, 1]) 
            st.pyplot(fig_cat)
            plt.close(fig_cat)


            # 統計檢定
            st.markdown("**統計檢定結果：**")
            contingency_table = pd.crosstab(df_display[grouping_col_name], df_display[cat_col])
            if contingency_table.empty or contingency_table.sum().sum() == 0 or contingency_table.shape[0] < 2 or contingency_table.shape[1] < 2:
                st.markdown("* 列聯表數據不足，無法進行卡方檢定。")
            else:
                try:
                    chi2, p_value_chi2, dof, expected_freq = stats.chi2_contingency(contingency_table)
                    st.markdown(f"* **卡方獨立性檢定**: 卡方統計量 = {chi2:.2f}, p-value = {p_value_chi2:.4f}, 自由度 = {dof}")
                    
                    min_expected_freq = expected_freq.min()
                    warning_msg = ""
                    if min_expected_freq < 1:
                        warning_msg = f"警告：期望頻率中存在小於1的值 (最小期望頻率: {min_expected_freq:.2f})。"
                    elif min_expected_freq < 5:
                        num_cells_lt_5 = (expected_freq < 5).sum()
                        total_cells = expected_freq.size
                        if (num_cells_lt_5 / total_cells) > 0.2:
                            warning_msg = f"警告：超過20%的儲存格期望頻率小於5 (最小期望頻率: {min_expected_freq:.2f})。卡方檢定結果可能不夠準確。"
                        else:
                            warning_msg = f"注意：部分儲存格期望頻率小於5 (最小期望頻率: {min_expected_freq:.2f})。"
                    if warning_msg:
                        st.markdown(f"    * {warning_msg}")

                    if p_value_chi2 < alpha:
                        st.markdown(f"    * 結論: **顯著關聯** (p < {alpha})。「{grouping_col_name}」與「{cat_col}」之間存在統計上顯著的關聯。建議分析殘差。")
                    else:
                        st.markdown(f"    * 結論: **無顯著關聯** (p >= {alpha})。")
                except Exception as e:
                    st.markdown(f"* 卡方檢定執行錯誤: {e}")
            
            # 文字解讀區塊 (請您填充)
            st.markdown(f"""
            **初步文字解讀 ({cat_col})**:
            * *(例如：從圖表和統計數據看，成績「全班五名以內」的學生在此項目選擇「很符合」的比例為 X%，而「全班三十名以後」的為 Y%...)*
            * *(結合p值：卡方檢定結果顯示這些差異在統計上是/不是顯著的...)*
            * *(您的觀察與推論...)*
            """)
            st.markdown("---")
        else:
            st.warning(f"類別型欄位 {cat_col} 未在載入的數據中找到。")

    st.header("整體總結與發現")
    st.markdown("""
    *(請在此處綜合所有分析結果，撰寫您對「不同成績群體學生在數位學習樣貌上的初步圖像」的總結性看法、主要發現的群體畫像等。)*
    
    **例如，您可以從以下幾個角度思考：**
    * **高學業成就群體特徵**：他們在哪些數位行為、態度或資源擁有上表現出顯著的正面特徵？（例如，更高的自我管理能力、更正面的學習態度、更有效的學習時間分配等）
    * **中低學業成就群體特徵**：他們在哪些方面可能面臨挑戰或表現出不同的模式？
    * **普遍現象**：有哪些數位行為或態度在所有學生群體中都比較普遍或比較罕見？
    * **令人意外的發現**：有哪些結果與您的初步預期不符？
    * **尚需深入探討的問題**：基於目前的分析，有哪些新的問題或方向值得未來進一步研究？（例如，設備使用頻率的遺失值問題、使用儀表板的複雜模式等）
    * **對教學實務的可能啟示**：這些發現對於教學設計、學生輔導或資源分配有何初步的啟示？
    """)

else:
    st.error("數據未能成功載入或處理，無法顯示儀表板內容。請檢查檔案路徑和數據處理邏輯。")