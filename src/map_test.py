# -*- coding: utf-8 -*-
import json
import pandas as pd
import time
import pprint
from collections import Counter
import os # 引入 os 模組來處理路徑

# --- 設定基本路徑 ---
# 請根據您的檔案存放位置修改
# DATA_DIR = '../data/' # 為了讓範例獨立執行，暫時改為當前目錄
# MAP_DIR = '.'         # 為了讓範例獨立執行，暫時改為當前目錄
# 實際使用時請改回您原本的設定
DATA_DIR = '../data/' # 假設 CSV 在 data 子目錄
MAP_DIR = '../maps/'  # 假設 JSON 在 maps 子目錄

# 確保目錄存在 (如果測試用)
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(MAP_DIR, exist_ok=True)

def load_json(filepath):
    """載入 JSON 檔案"""
    print(f"正在讀取 JSON 檔案: {filepath}")
    try:
        # *** 注意：使用 utf-8-sig 來處理可能的 BOM ***
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

# --- 新的/修改後的值轉換函式 ---
def map_all_values(df, general_options, specific_maps):
    """
    在 DataFrame 上進行值的轉換。
    對所有欄位應用 general_options。
    如果欄位有 specific_map，則 specific_map 中的規則優先於 general_options。
    """
    print("\n--- 開始轉換數值為標籤 (優先使用特定對應，並應用通用對應) ---")
    start_time = time.time()
    value_mapped_count = 0
    skipped_columns_errors = []
    unmapped_entries = []
    MAX_UNMAPPED_TO_PRINT = 50

    # 確保通用選項鍵為字串，以便於後續查找和合併
    # *** 修改：將 general_options 的鍵值都轉為字串 ***
    general_options_str_keys = {str(k): str(v) for k, v in general_options.items()}

    # 操作 DataFrame 的副本，避免修改原始傳入的 DataFrame
    processed_df = df.copy()

    # 遍歷 DataFrame 的所有欄位 (原始欄位代碼)
    for original_code in processed_df.columns:
        # 獲取該欄位的特定對應規則
        # *** 假設 specific_maps 的鍵也是字串或需要轉為字串來匹配欄位名 ***
        # 如果原始欄位代碼是數字，需確保 specific_maps 的鍵也是數字或進行轉換
        specific_map = specific_maps.get(str(original_code)) # 假設 specific_maps 的鍵是字串

        # 組合對應表：通用選項打底，特定選項覆蓋
        combined_map = general_options_str_keys.copy() # 從通用選項開始
        specific_map_str_keys_values = {}
        if isinstance(specific_map, dict) and specific_map:
            # *** 修改：特定 map 的鍵值也轉為字串 ***
            specific_map_str_keys_values = {str(k): str(v) for k, v in specific_map.items()}
            combined_map.update(specific_map_str_keys_values) # 特定選項覆蓋通用選項中的相同鍵

        # 如果組合後的對應表是空的 (例如 general_options 為空且無 specific_map)，則跳過此欄位
        if not combined_map:
            # print(f"欄位 {original_code} 無任何對應規則，跳過。") # 可取消註解以顯示更多資訊
            continue

        try:
            original_dtype = processed_df[original_code].dtype
            # 將欄位轉為字串進行替換，以處理混合類型並確保對應鍵匹配
            # 注意：Pandas 的 NA/None 值也會被轉為 'nan' 或類似字串
            # 我們需要在檢查未對應值時排除它們
            col_as_str = processed_df[original_code].astype(str)

            # 執行替換 (使用 .replace() 方法，它可以接受字典)
            replaced_col = col_as_str.replace(combined_map)

            # --- 檢查未對應的值 ---
            # 找出那些替換前後相同，且原始值不是 pandas 的 NA/null，也不是已經是對應後的值 的項目
            # 檢查 col_as_str 是否在 combined_map 的鍵中，而不是檢查 replaced_col == col_as_str
            # 因為如果原始值恰好等於目標值，也會替換成功
            # 我們要找的是不在 map key 中，也不是 NA 的原始值
            failed_mask = (~col_as_str.isin(combined_map.keys())) & \
                          (processed_df[original_code].notna()) & \
                          (col_as_str != 'nan') # 多加一層保險，處理可能的 'nan' 字串

            if failed_mask.any():
                failed_indices = processed_df.index[failed_mask]
                # print(f"欄位 {original_code} 發現 {len(failed_indices)} 個未對應值。") # Debug 資訊
                for idx in failed_indices:
                    if len(unmapped_entries) < MAX_UNMAPPED_TO_PRINT:
                        unmapped_value = processed_df.loc[idx, original_code] # 取原始值
                        unmapped_entries.append((idx, original_code, unmapped_value)) # 記錄原始欄位名和值
                    else:
                        # 只添加一次上限提示
                        if len(unmapped_entries) == MAX_UNMAPPED_TO_PRINT:
                            unmapped_entries.append(("...", f"達到顯示上限 ({MAX_UNMAPPED_TO_PRINT})", "..."))
                        break # 跳出內部迴圈，不再為此欄位添加未對應條目

            # --- 更新 DataFrame ---
            # 將處理過的字串類型欄位放回 DataFrame
            # 因為轉換後的值是標籤 (字串)，欄位類型會變成 object (或 string)
            processed_df[original_code] = replaced_col
            value_mapped_count += 1 # 記錄已處理（嘗試轉換）的欄位數

        except Exception as e:
            print(f"  處理欄位 '{original_code}' (原始 Dtype: {original_dtype}) 時發生錯誤: {e}")
            skipped_columns_errors.append(f"{original_code} (原因: 處理時發生錯誤)")

    # --- 處理結束後的報告 ---
    end_time = time.time()
    print("\n--- 值轉換完成 ---")
    print(f"嘗試轉換 {value_mapped_count} 個欄位的值 (使用通用選項，並優先應用特定選項)。")
    print(f"因處理錯誤而跳過 {len(skipped_columns_errors)} 個欄位。")
    print(f"值轉換過程耗時: {end_time - start_time:.2f} 秒。")

    if skipped_columns_errors:
        print("\n--- 以下欄位因處理錯誤而被跳過 ---")
        pprint.pprint(skipped_columns_errors)
    if unmapped_entries:
        print(f"\n--- 以下資料點的值無法在對應的 Value Map 中找到 (最多顯示 {MAX_UNMAPPED_TO_PRINT} 筆) ---")
        print("(索引, 欄位名稱, 未能轉換的值)")
        # 使用 pprint 處理可能包含換行符的欄位名稱或值
        for entry in unmapped_entries:
             pprint.pprint(entry) # 逐行打印以獲得更好格式
    elif value_mapped_count > 0 and not skipped_columns_errors:
         print("\n--- 所有欄位均已嘗試應用通用或特定 Value Map ---")
    elif value_mapped_count == 0 and not skipped_columns_errors:
        print("\n--- 沒有欄位需要進行值轉換，或所有欄位均無錯誤 ---")

    return processed_df # 返回處理過的新 DataFrame

# --- 修改後的欄位重新命名函式 ---
def rename_and_check_duplicates(df, id_map):
    """
    根據 id_map 重新命名欄位，並檢查是否有重複名稱。
    不再返回反向映射。
    """
    print("\n--- 正在複製資料並轉換欄位名稱 ---")
    descriptive_df = df.copy() # 操作副本

    # 過濾 id_map，只保留實際存在於 DataFrame 中的欄位 (原始代碼作為鍵)
    # *** 確保 id_map 的鍵和 df 的欄位名稱類型一致，這裡假設都是字串或可以轉為字串比較 ***
    valid_id_map = {str(k): v for k, v in id_map.items() if str(k) in descriptive_df.columns}

    if not valid_id_map:
         print("警告：提供的 id_map 中沒有任何鍵對應到 DataFrame 的欄位名稱。")
         # 如果沒有有效的映射，直接返回原始 DataFrame (副本)
         print("描述性欄位名稱 DataFrame 維度 (未變更): {descriptive_df.shape}")
         return descriptive_df

    # 執行 Rename
    descriptive_df.rename(columns=valid_id_map, inplace=True)
    print(f"已嘗試將 {len(valid_id_map)} 個欄位名稱從代碼轉換為說明。")
    print(f"描述性欄位名稱 DataFrame 維度: {descriptive_df.shape}")

    # 檢查 rename 後是否產生了重複欄位
    # 使用 .duplicated(keep=False) 找出所有重複項
    duplicated_cols = descriptive_df.columns[descriptive_df.columns.duplicated(keep=False)]
    unique_duplicated_cols = duplicated_cols.unique()

    if not unique_duplicated_cols.empty:
        print(f"\n*** 嚴重錯誤：Rename 後 DataFrame 中存在重複的欄位名稱: ***")
        # 找出哪些原始代碼映射到了同一個說明文字
        value_counts = pd.Series(valid_id_map).value_counts()
        conflicting_names = value_counts[value_counts > 1].index.tolist()
        print("以下說明文字被用於多個原始代碼，導致衝突：")
        pprint.pprint(conflicting_names)
        print("涉及的重複欄位包括:")
        pprint.pprint(list(unique_duplicated_cols))

        print("\n這通常是因為輸入的 id_map 檔案中說明文字不唯一。")
        print("請修正對應的 id_map 檔案後重試。腳本將跳過此資料集的後續處理。")
        return None # 返回 None 表示處理失敗
    else:
        print("確認 Rename 後欄位名稱均唯一。")
        return descriptive_df # 只返回處理後的 DataFrame

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

# --- 修改後的資料集處理流程 ---
def process_dataset(prefix, data_dir, map_dir):
    """處理單一資料集的完整流程 (先轉換值，再重新命名欄位)"""
    print(f"\n{'='*10} 開始處理資料集: {prefix} {'='*10}")

    # --- 建構檔案路徑 ---
    # 保持檔名結構，但路徑來自參數
    id_map_path = os.path.join(map_dir, f'tigps_w1_{prefix}_id_map.json')
    value_map_path = os.path.join(map_dir, f'tigps_w1_{prefix}_value_maps.json')
    csv_path = os.path.join(data_dir, f'TIGPSw1_{prefix}.csv')
    output_path = os.path.join(data_dir, f'TIGPSw1_{prefix}_descriptive_labeled.csv')

    # --- 執行步驟 ---
    loaded_id_map = load_json(id_map_path)
    loaded_value_maps = load_json(value_map_path) # 載入包含 general 和 specific 的檔案
    raw_data_df = load_csv(csv_path)

    # --- 檢查檔案載入情況 ---
    if raw_data_df is None: # 至少要有原始資料
        print(f"資料集 {prefix} 因無法載入 CSV 檔案 {csv_path} 而無法處理。")
        return
    if loaded_id_map is None:
        print(f"警告：資料集 {prefix} 缺少或無法讀取 id_map 檔案 {id_map_path}，欄位將不會被重新命名。")
        loaded_id_map = {} # 提供空字典以繼續執行，避免後續錯誤
    if loaded_value_maps is None:
        print(f"警告：資料集 {prefix} 缺少或無法讀取 value_map 檔案 {value_map_path}，將不會進行值轉換。")
        loaded_value_maps = {} # 提供空字典以繼續執行

    # --- 提取 general 和 specific maps ---
    # *** 提供預設空字典，確保即使檔案不存在或格式錯誤也能安全地獲取 ***
    general_options = loaded_value_maps.get('general_options', {})
    specific_value_maps = loaded_value_maps.get('value_maps', {})
    # 只有當檔案存在但內容為空或格式不對時才發出警告
    if not general_options and not specific_value_maps and loaded_value_maps is not None and loaded_value_maps != {}:
          print(f"警告：Value map 檔案 {value_map_path} 似乎是空的或缺少 'general_options'/'value_maps' 鍵。")

    # --- 步驟 1: 進行值轉換 ---
    value_mapped_df = map_all_values(raw_data_df, general_options, specific_value_maps)

    # --- 步驟 2: 進行欄位重新命名 ---
    descriptive_df = rename_and_check_duplicates(value_mapped_df, loaded_id_map)

    # 如果欄位重新命名失敗 (例如，因為 id_map 導致重複欄位名)
    if descriptive_df is None:
        print(f"資料集 {prefix} 因欄位名稱重複問題停止處理 (在值映射之後發生)。")
        # 可考慮儲存僅轉換了值的 DataFrame
        # output_path_value_only = os.path.join(data_dir, f'TIGPSw1_{prefix}_value_mapped_only.csv')
        # print(f"嘗試儲存僅轉換值的結果到: {output_path_value_only}")
        # save_csv(value_mapped_df, output_path_value_only)
        return

    # --- 最終結果就是 descriptive_df ---
    processed_df = descriptive_df

    # 查看結果預覽
    print("\n--- 最終結果預覽 (欄位名稱和值都已轉換，前 5 筆) ---")
    # 增加顯示寬度以便查看更多欄位
    pd.set_option('display.max_columns', 50)
    pd.set_option('display.width', 1000) # 設置終端顯示寬度
    pd.set_option('display.max_colwidth', 50)
    print(processed_df.head())

    # 儲存結果
    save_csv(processed_df, output_path)

    print(f"\n{'='*10} 資料集: {prefix} 處理完成 {'='*10}")


# --- 主要執行區塊 ---
if __name__ == "__main__":
    # 定義要處理的所有資料集前綴
    datasets_to_process = ['s', 'p', 'f', 't', 'st', 'sc']
    # 為了測試方便，先用一個虛擬的 'test' 資料集

    print("\n##### 開始批次處理 TIGPS 資料集轉換 #####")

    # 遍歷每個資料集前綴並處理
    for prefix in datasets_to_process:
        # *** 確保傳遞正確的目錄參數 ***
        process_dataset(prefix, data_dir=DATA_DIR, map_dir=MAP_DIR)
        print("\n" + "#" * 50 + "\n") # 添加分隔線

    print("##### 所有資料集處理完畢 #####")
