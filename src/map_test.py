# -*- coding: utf-8 -*-
import json
import pandas as pd
import time
import pprint
from collections import Counter
import os # 引入 os 模組來處理路徑

# --- 設定基本路徑 ---
# 請根據您的檔案存放位置修改
DATA_DIR = '../data/' # CSV 檔案所在的資料夾路徑
MAP_DIR = '.'         # id_map 和 value_maps JSON 檔案所在的資料夾路徑

def load_json(filepath):
    """載入 JSON 檔案"""
    print(f"正在讀取 JSON 檔案: {filepath}")
    try:
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            data = json.load(f)
        print(f"成功讀取: {filepath}")
        return data
    except FileNotFoundError:
        print(f"錯誤：找不到檔案 {filepath}。")
        return None
    except json.JSONDecodeError as e:
        print(f"錯誤：檔案 {filepath} JSON 格式錯誤。錯誤訊息：{e}")
        return None
    except Exception as e:
        print(f"讀取檔案 {filepath} 時發生未知錯誤：{e}")
        return None

def load_csv(filepath):
    """載入 CSV 檔案"""
    print(f"正在讀取 CSV 檔案: {filepath}")
    start_time = time.time()
    try:
        # low_memory=False 有助於處理混合類型的欄位
        df = pd.read_csv(filepath, low_memory=False)
        end_time = time.time()
        print(f"成功載入資料。耗時: {end_time - start_time:.2f} 秒。")
        print(f"原始資料維度 (行數, 欄數): {df.shape}")
        return df
    except FileNotFoundError:
        print(f"錯誤：找不到資料檔案 {filepath}。")
        return None
    except Exception as e:
        print(f"載入 CSV 檔案 {filepath} 時發生錯誤：{e}")
        return None

def rename_and_check_duplicates(df, id_map):
    """根據 id_map 重新命名欄位，並檢查是否有重複名稱"""
    print("\n--- 正在複製資料並轉換欄位名稱 ---")
    descriptive_df = df.copy()
    valid_id_map = {k: v for k, v in id_map.items() if k in descriptive_df.columns}
    
    # 執行 Rename
    descriptive_df.rename(columns=valid_id_map, inplace=True)
    print(f"已嘗試將 {len(valid_id_map)} 個欄位名稱從代碼轉換為說明。")
    print(f"描述性欄位名稱 DataFrame 維度: {descriptive_df.shape}")

    # 檢查 rename 後是否產生了重複欄位
    duplicate_renamed_cols = descriptive_df.columns[descriptive_df.columns.duplicated()].unique()
    if not duplicate_renamed_cols.empty:
        print(f"\n*** 嚴重錯誤：Rename 後 DataFrame 中存在重複的欄位名稱: ***")
        pprint.pprint(list(duplicate_renamed_cols))
        print("\n這通常是因為輸入的 id_map 檔案中說明文字不唯一。")
        print("請修正對應的 id_map 檔案後重試。腳本將跳過此資料集的後續處理。")
        return None, None # 返回 None 表示處理失敗
    else:
        print("確認 Rename 後欄位名稱均唯一。")
        # 建立反向映射 (說明 -> 原始代碼)
        original_code_from_desc = {v: k for k, v in valid_id_map.items()}
        return descriptive_df, original_code_from_desc

def map_values(df, general_options, specific_maps, original_code_map):
    """在 DataFrame 上進行值的轉換 (使用結構 1 maps)"""
    print("\n--- 開始在描述性欄位名稱的 DataFrame 上轉換數值為標籤 (使用結構 1) ---")
    start_time = time.time()
    value_mapped_count = 0
    skipped_columns_errors = []
    unmapped_entries = []
    MAX_UNMAPPED_TO_PRINT = 50

    general_options_str = {str(k): v for k, v in general_options.items()} # 確保通用選項鍵為字串

    for desc_col_name in df.columns:
        original_code = original_code_map.get(desc_col_name)
        specific_map = specific_maps.get(original_code)

        if isinstance(specific_map, dict) and specific_map:
            try:
                original_dtype = df[desc_col_name].dtype
                specific_map_str = {str(k): v for k, v in specific_map.items()}
                combined_map = {**general_options_str, **specific_map_str}

                col_as_str = df[desc_col_name].astype(str)
                replaced_col = col_as_str.replace(combined_map)

                failed_mask = (replaced_col == col_as_str) & \
                              (col_as_str.notna()) & \
                              (col_as_str != 'nan') & \
                              (~col_as_str.isin(combined_map.values()))

                if failed_mask.any():
                    failed_indices = df.index[failed_mask]
                    for idx in failed_indices:
                        if len(unmapped_entries) < MAX_UNMAPPED_TO_PRINT:
                            unmapped_value = df.loc[idx, desc_col_name]
                            unmapped_entries.append((idx, desc_col_name, unmapped_value))
                        else:
                            if len(unmapped_entries) == MAX_UNMAPPED_TO_PRINT:
                               unmapped_entries.append(("...", "達到顯示上限", "..."))
                               break
                
                # 直接在傳入的 DataFrame 上修改
                df[desc_col_name] = replaced_col 
                value_mapped_count += 1

            except Exception as e:
                print(f"  處理欄位 '{desc_col_name}' (原始代碼: {original_code}, Dtype: {original_dtype}) 時發生錯誤: {e}")
                skipped_columns_errors.append(f"{desc_col_name} (原因: 處理時發生錯誤)")
        # else: # 欄位無 specific_map，不需處理也不需報告為錯誤
        #    pass

    end_time = time.time()
    print("\n--- 值轉換完成 ---")
    print(f"成功轉換 {value_mapped_count} 個欄位的值 (使用通用+特定選項)。")
    print(f"因處理錯誤而跳過 {len(skipped_columns_errors)} 個欄位。")
    print(f"值轉換過程耗時: {end_time - start_time:.2f} 秒。")

    if skipped_columns_errors:
        print("\n--- 以下欄位因處理錯誤而被跳過 ---")
        pprint.pprint(skipped_columns_errors)
    if unmapped_entries:
        print(f"\n--- 以下資料點的值無法在對應的 Value Map 中找到 (最多顯示 {MAX_UNMAPPED_TO_PRINT} 筆) ---")
        print("(索引, 欄位名稱, 未能轉換的值)")
        pprint.pprint(unmapped_entries)
    elif value_mapped_count > 0 and not skipped_columns_errors:
        print("\n--- 所有有對應 Value Map 的欄位中的值均成功轉換或原本就無需轉換 ---")
    elif value_mapped_count == 0 and not skipped_columns_errors:
        print("\n--- 沒有找到需要進行值轉換的欄位，或所有欄位均無錯誤 ---")
    
    return df # 返回處理過的 DataFrame

def save_csv(df, filepath):
    """儲存 DataFrame 到 CSV 檔案"""
    print(f"\n--- 正在將最終結果儲存至 {filepath} ---")
    start_time = time.time()
    try:
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        end_time = time.time()
        print(f"成功儲存檔案。耗時: {end_time - start_time:.2f} 秒。")
        return True
    except Exception as e:
        print(f"儲存最終結果 CSV 檔案 '{filepath}' 時發生錯誤：{e}")
        return False

def process_dataset(prefix, data_dir, map_dir):
    """處理單一資料集的完整流程"""
    print(f"\n{'='*10} 開始處理資料集: {prefix} {'='*10}")

    # --- 建構檔案路徑 ---
    # *** 注意：這裡假設您的 id_map 檔名包含 _unique, value_map 檔名包含 _structure1 ***
    id_map_path = os.path.join(map_dir, f'tigps_w1_{prefix}_id_map.json')
    value_map_path = os.path.join(map_dir, f'tigps_w1_{prefix}_value_maps_structure1.json')
    csv_path = os.path.join(data_dir, f'TIGPSw1_{prefix}.csv')
    output_path = os.path.join(data_dir, f'TIGPSw1_{prefix}_descriptive_labeled.csv')

    # --- 執行步驟 ---
    loaded_id_map = load_json(id_map_path)
    loaded_structure1_maps = load_json(value_map_path)
    raw_data_df = load_csv(csv_path)

    # 檢查是否所有必要檔案都成功載入
    if not loaded_id_map or not loaded_structure1_maps or raw_data_df is None:
        print(f"資料集 {prefix} 因缺少必要檔案而無法處理。")
        return

    # 提取 general 和 specific maps
    general_options = loaded_structure1_maps.get('general_options', {})
    specific_value_maps = loaded_structure1_maps.get('value_maps', {})
    if not general_options and not specific_value_maps:
         print(f"警告：Value map 檔案 {value_map_path} 似乎是空的或格式不正確。")
         # 根據需要決定是否繼續

    # 重新命名欄位並檢查重複
    descriptive_df, original_code_from_desc = rename_and_check_duplicates(raw_data_df, loaded_id_map)
    if descriptive_df is None: # 如果 rename 失敗 (發現重複)
        print(f"資料集 {prefix} 因欄位名稱重複問題停止處理。")
        return

    # 轉換值
    processed_df = map_values(descriptive_df, general_options, specific_value_maps, original_code_from_desc)

    # 查看結果預覽
    print("\n--- 最終結果預覽 (欄位名稱和值都已轉換，前 5 筆) ---")
    pd.set_option('display.max_columns', 20)
    pd.set_option('display.max_colwidth', 50)
    print(processed_df.head())

    # 儲存結果
    save_csv(processed_df, output_path)

    print(f"\n{'='*10} 資料集: {prefix} 處理完成 {'='*10}")


# --- 主要執行區塊 ---
if __name__ == "__main__":
    # 定義要處理的所有資料集前綴
    datasets_to_process = ['s', 'p', 'f', 't', 'st', 'sc']

    print("##### 開始批次處理 TIGPS 資料集轉換 #####")

    # 遍歷每個資料集前綴並處理
    for prefix in datasets_to_process:
        process_dataset(prefix, data_dir=DATA_DIR, map_dir=MAP_DIR)
        print("\n" + "#" * 50 + "\n") # 添加分隔線

    print("##### 所有資料集處理完畢 #####")