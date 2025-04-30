# -*- coding: utf-8 -*-
import json
import pandas as pd
import time
import pprint
from collections import Counter

# --- 步驟 1: 讀取 id_map 和 結構 1 的 value_maps ---
id_map_file_path = 'tigps_w1_sc_id_map.json' # *** 使用修正過、說明唯一的 id_map ***
loaded_id_map = None
try:
    with open(id_map_file_path, 'r', encoding='utf-8-sig') as f:
        loaded_id_map = json.load(f)
    print(f"成功從 {id_map_file_path} 讀取 id_map。")
    # (重複檢查的程式碼可以移除或保留)
    # print("\n--- 檢查 id_map 中的重複說明文字 ---")
    # description_counts = Counter(loaded_id_map.values())
    # duplicate_descriptions = {desc: count for desc, count in description_counts.items() if count > 1}
    # if duplicate_descriptions:
    #     print(f"警告：即使檔名是 unique，檔案 {id_map_file_path} 內仍發現重複說明，請再次檢查：")
    #     pprint.pprint(duplicate_descriptions)
    # else:
    #     print("Id_map 中的說明文字均唯一。")

except FileNotFoundError:
    print(f"錯誤：找不到檔案 {id_map_file_path}。請確認檔案路徑和名稱。")
    exit()
except Exception as e:
    print(f"讀取 id_map 時發生錯誤：{e}")
    exit()

value_map_file_path = 'tigps_w1_sc_value_maps.json' # 指向結構 1 value map
loaded_structure1_maps = None
general_options = {}
specific_value_maps = {}
try:
    with open(value_map_file_path, 'r', encoding='utf-8-sig') as f:
        loaded_structure1_maps = json.load(f)
    if loaded_structure1_maps and 'general_options' in loaded_structure1_maps and 'value_maps' in loaded_structure1_maps:
        general_options = loaded_structure1_maps['general_options']
        specific_value_maps = loaded_structure1_maps['value_maps']
        print(f"\n成功從 {value_map_file_path} 讀取 結構 1 的 value_maps。")
    else:
        print(f"錯誤：檔案 {value_map_file_path} 格式不符。")
        exit()
except FileNotFoundError:
    print(f"錯誤：找不到檔案 {value_map_file_path}。")
    exit()
except Exception as e:
    print(f"讀取 結構 1 value_maps 時發生錯誤：{e}")
    exit()

# --- 步驟 2: 確保 general_options 鍵是字串 ---
general_options = {str(k): v for k, v in general_options.items()}
print("Value map 結構確認完成。")

# --- 步驟 3: 載入您的實際完整資料 ---
csv_file_path = '../data/TIGPSw1_sc.csv' # 假設家長資料檔名
raw_data_df = None
print(f"\n正在從 {csv_file_path} 載入完整資料...")
start_time = time.time()
try:
    raw_data_df = pd.read_csv(csv_file_path, low_memory=False)
    end_time = time.time()
    print(f"成功載入資料。耗時: {end_time - start_time:.2f} 秒。")
    print(f"原始資料維度 (行數, 欄數): {raw_data_df.shape}")
except FileNotFoundError:
    print(f"錯誤：找不到您的資料檔案 {csv_file_path}。")
    exit()
except Exception as e:
    print(f"載入 CSV 檔案時發生錯誤：{e}")
    exit()

# --- 步驟 4: 複製原始資料並進行欄位名稱轉換 ---
print("\n--- 正在複製資料並轉換欄位名稱 ---")
descriptive_df = raw_data_df.copy()
valid_id_map = {k: v for k, v in loaded_id_map.items() if k in descriptive_df.columns}
# **假設 id_map 已修正，這裡直接 rename**
descriptive_df.rename(columns=valid_id_map, inplace=True)
print(f"已嘗試將 {len(valid_id_map)} 個欄位名稱從代碼轉換為說明。")
print(f"描述性欄位名稱 DataFrame 維度: {descriptive_df.shape}")
# 檢查 rename 後是否仍有重複欄位 (理論上不應再有)
duplicate_renamed_cols = descriptive_df.columns[descriptive_df.columns.duplicated()].unique()
if not duplicate_renamed_cols.empty:
    print(f"*** 嚴重警告：Rename 後仍然產生了重複的欄位名稱: {list(duplicate_renamed_cols)} ***")
    print("       請務必修正 id_map 檔案使其說明文字唯一！")
    # exit() # 強烈建議在此停止

original_code_from_desc = {v: k for k, v in valid_id_map.items()} # id_map 唯一後，可直接反轉


# --- 步驟 5: 在 descriptive_df 上進行值的轉換 ---
print("\n--- 開始在描述性欄位名稱的 DataFrame 上轉換數值為標籤 (使用結構 1) ---")
start_time = time.time()
value_mapped_count = 0
# *** 修改：只記錄因錯誤而被跳過的欄位 ***
skipped_columns_errors = []
unmapped_entries = []
MAX_UNMAPPED_TO_PRINT = 50

for desc_col_name in descriptive_df.columns:
    original_code = original_code_from_desc.get(desc_col_name)
    specific_map = specific_value_maps.get(original_code)

    # 只有當 specific_map 是一個有效的、非空的字典時，才嘗試轉換
    if isinstance(specific_map, dict) and specific_map:
        try:
            original_dtype = descriptive_df[desc_col_name].dtype # 獲取原始類型
            general_options_str = {str(k): v for k, v in general_options.items()}
            specific_map_str = {str(k): v for k, v in specific_map.items()}
            combined_map = {**general_options_str, **specific_map_str}

            col_as_str = descriptive_df[desc_col_name].astype(str)
            replaced_col = col_as_str.replace(combined_map)

            failed_mask = (replaced_col == col_as_str) & \
                          (col_as_str.notna()) & \
                          (col_as_str != 'nan') & \
                          (~col_as_str.isin(combined_map.values()))

            if failed_mask.any():
                failed_indices = descriptive_df.index[failed_mask]
                for idx in failed_indices:
                    if len(unmapped_entries) < MAX_UNMAPPED_TO_PRINT:
                        unmapped_value = descriptive_df.loc[idx, desc_col_name]
                        unmapped_entries.append((idx, desc_col_name, unmapped_value))
                    else:
                        if len(unmapped_entries) == MAX_UNMAPPED_TO_PRINT:
                           unmapped_entries.append(("...", "達到顯示上限", "..."))
                           break

            descriptive_df[desc_col_name] = replaced_col
            value_mapped_count += 1

        except Exception as e:
            # 只有在轉換過程中發生錯誤時，才記錄到 skipped_columns_errors
            print(f"  處理欄位 '{desc_col_name}' (原始代碼: {original_code}, Dtype: {original_dtype}) 時發生錯誤: {e}")
            skipped_columns_errors.append(f"{desc_col_name} (原因: 處理時發生錯誤)") # <--- 加入錯誤列表

    # 注意：如果 specific_map 不存在或無效 (例如 None 或空字典)，這裡不再將其加入任何 skipped 列表
    # elif original_code in specific_value_maps: # specific_map 無效
    #     pass # 不再記錄
    # else: # 無 specific_map
    #     pass # 不再記錄


# ... (後續的 Step 6 和 Step 7 保持不變) ...
end_time = time.time()
print("\n--- 值轉換完成 ---")
print(f"成功轉換 {value_mapped_count} 個欄位的值 (使用通用+特定選項)。")
# *** 修改：更新打印的列表和說明 ***
print(f"因處理錯誤或欄位名重複(若id_map未修正)而跳過 {len(skipped_columns_errors)} 個欄位。")
print(f"值轉換過程耗時: {end_time - start_time:.2f} 秒。")
print(f"最終 DataFrame 維度: {descriptive_df.shape}")

# --- 修改：印出因錯誤或重複而被跳過的欄位列表 ---
if skipped_columns_errors:
    print("\n--- 以下欄位因處理錯誤或欄位名重複而被跳過 ---")
    pprint.pprint(skipped_columns_errors)

# --- 印出無法轉換的具體資料點 ---
if unmapped_entries:
    print(f"\n--- 以下資料點的值無法在對應的 Value Map 中找到 (最多顯示 {MAX_UNMAPPED_TO_PRINT} 筆) ---")
    print("(索引, 欄位名稱, 未能轉換的值)")
    pprint.pprint(unmapped_entries)
elif value_mapped_count > 0 and not skipped_columns_errors: # 確保有轉換且無錯誤
    print("\n--- 所有有對應 Value Map 的欄位中的值均成功轉換或原本就無需轉換 ---")
elif value_mapped_count == 0 and not skipped_columns_errors:
     print("\n--- 沒有找到需要進行值轉換的欄位，或所有欄位均無錯誤 ---")

# --- 步驟 6: 查看最終結果 (範例) ---
# (程式碼不變)
print("\n--- 最終結果預覽 (欄位名稱和值都已轉換，前 5 筆) ---")
pd.set_option('display.max_columns', 20)
pd.set_option('display.max_colwidth', 50)
if descriptive_df is not None:
    print(descriptive_df.head())
else:
    print("無法顯示預覽，因為 DataFrame 未成功載入或創建。")

# --- 步驟 7: (可選) 儲存最終結果 ---
# (程式碼不變)
final_output_path = '../data/TIGPSw1_sc_descriptive_labeled.csv'
print(f"\n--- 正在將最終結果儲存至 {final_output_path} ---")
start_time = time.time()
if descriptive_df is not None:
    try:
        descriptive_df.to_csv(final_output_path, index=False, encoding='utf-8-sig')
        end_time = time.time()
        print(f"成功儲存檔案。耗時: {end_time - start_time:.2f} 秒。")
    except Exception as e:
        print(f"儲存最終結果 CSV 檔案時發生錯誤：{e}")
else:
     print("無法儲存檔案，因為 DataFrame 未成功載入或創建。")