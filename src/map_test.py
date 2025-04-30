# -*- coding: utf-8 -*-
import json
import pandas as pd
import time
import pprint # 用於美化列表輸出

# --- 步驟 1: 讀取 id_map 和 結構 1 的 value_maps ---

# 讀取 id_map (變項代碼 -> 變項說明)
# *** 請根據您要處理的問卷 (學生/家長) 修改路徑 ***
id_map_file_path = 'tigps_w1_02_id_map.json' # 假設是家長問卷 id_map
loaded_id_map = None
try:
    with open(id_map_file_path, 'r', encoding='utf-8-sig') as f:
        loaded_id_map = json.load(f)
    print(f"成功從 {id_map_file_path} 讀取 id_map。")
except FileNotFoundError:
    print(f"錯誤：找不到檔案 {id_map_file_path}。請確認檔案路徑和名稱。")
    # exit()
except Exception as e:
    print(f"讀取 id_map 時發生錯誤：{e}")
    # exit()

# 讀取 value_maps (結構 1: 包含 general_options 和 value_maps)
# *** 請根據您要處理的問卷 (學生/家長) 修改路徑 ***
value_map_file_path = 'tigps_w1_02_value_maps.json' # 指向新的結構 1 檔案
loaded_structure1_maps = None
general_options = {}
specific_value_maps = {}
try:
    with open(value_map_file_path, 'r', encoding='utf-8-sig') as f:
        loaded_structure1_maps = json.load(f)

    if loaded_structure1_maps and 'general_options' in loaded_structure1_maps and 'value_maps' in loaded_structure1_maps:
        general_options = loaded_structure1_maps['general_options']
        specific_value_maps = loaded_structure1_maps['value_maps']
        print(f"成功從 {value_map_file_path} 讀取 結構 1 的 value_maps。")
    else:
        print(f"錯誤：檔案 {value_map_file_path} 未包含預期的 'general_options' 和 'value_maps' 鍵。")
        # exit()
except FileNotFoundError:
    print(f"錯誤：找不到檔案 {value_map_file_path}。請先執行產生結構 1 JSON 的程式碼。")
    # exit()
except Exception as e:
    print(f"讀取 結構 1 value_maps 時發生錯誤：{e}")
    # exit()

# --- 步驟 2: 確保 general_options 鍵是字串 ---
general_options = {str(k): v for k, v in general_options.items()}
print("Value map 結構確認完成 (預期鍵為字串)。")

# --- 步驟 3: 載入您的實際完整資料 ---
# *** 請將路徑修改為對應的 CSV 檔案 ***
csv_file_path = '../data/TIGPSw1_p.csv' # 假設家長資料檔名
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
    # 創建範例 DataFrame
    if loaded_id_map and specific_value_maps: # 確保 map 已載入
      print("創建範例 DataFrame 以繼續...")
      raw_data_df = pd.DataFrame({
          'nschool_id': [101, 102, 101],
          'ap1': [1, 2, 1],
          'ap2': [2, 1, 2],
          'ap3': [1975, 1980, 1978],
          'ap10a': [3, 4, 2],
          'ap114': [1, 2, 3],
          'text_var': ['文字A', '文字B', '文字C'] # 增加一個假文字欄位
      })
      # 同步更新 id_map (僅為範例)
      loaded_id_map = {
          'nschool_id': '學校ID', 'ap1': '請問您是孩子的？', 'ap2': '您的性別？',
          'ap3': '您的出生年？', 'ap10a': '家人會彼此商量？',
          'ap114': '家庭收支平衡狀況？', 'text_var': '文字說明欄位'
      }
      # specific_value_maps 保持不變
    else:
      print("因無法載入資料且 map 檔案不完整，無法繼續。")
      exit()

except Exception as e:
    print(f"載入 CSV 檔案時發生錯誤：{e}")
    # exit()

# --- 步驟 4: 複製原始資料並進行欄位名稱轉換 ---
print("\n--- 正在複製資料並轉換欄位名稱 ---")
descriptive_df = raw_data_df.copy()
valid_rename_map = {k: v for k, v in loaded_id_map.items() if k in descriptive_df.columns}
descriptive_df.rename(columns=valid_rename_map, inplace=True)
print(f"已將 {len(valid_rename_map)} 個欄位名稱從代碼轉換為說明。")
print(f"描述性欄位名稱 DataFrame 維度: {descriptive_df.shape}")

original_code_from_desc = {}
for code, desc in valid_rename_map.items():
    if desc not in original_code_from_desc:
        original_code_from_desc[desc] = code

# --- 步驟 5: 在 descriptive_df 上進行值的轉換 (使用結構 1 maps) ---
print("\n--- 開始在描述性欄位名稱的 DataFrame 上轉換數值為標籤 (使用結構 1) ---")
start_time = time.time()
value_mapped_count = 0
skipped_columns = [] # <--- 初始化用於儲存跳過欄位名稱的列表

# 遍歷 descriptive_df 的欄位名稱 (中文說明)
for desc_col_name in descriptive_df.columns:
    original_code = original_code_from_desc.get(desc_col_name)
    specific_map = specific_value_maps.get(original_code)

    if isinstance(specific_map, dict) and specific_map:
        general_options_str = {str(k): v for k, v in general_options.items()}
        specific_map_str = {str(k): v for k, v in specific_map.items()}
        combined_map = {**general_options_str, **specific_map_str}

        # 轉換前記錄原始類型 (可選，用於偵錯)
        # original_dtype = descriptive_df[desc_col_name].dtype

        # 為了 replace，將欄位和 map key 都視為字串
        descriptive_df[desc_col_name] = descriptive_df[desc_col_name].astype(str).replace(combined_map)
        value_mapped_count += 1
        # print(f"  已轉換值: '{desc_col_name}' (原始代碼: {original_code}, 原始類型: {original_dtype})")

    elif original_code in specific_value_maps:
        # specific_map 存在但無效 (非 dict 或為空)
        skipped_columns.append(f"{desc_col_name} (原因: specific_map 無效或為空)") # <--- 記錄跳過的欄位及原因
    else:
        # 找不到 specific_map (可能是 ID、文字、或未定義)
        skipped_columns.append(f"{desc_col_name} (原因: 無 specific_map)") # <--- 記錄跳過的欄位及原因

end_time = time.time()
print("\n--- 值轉換完成 ---")
print(f"成功轉換 {value_mapped_count} 個欄位的值 (使用通用+特定選項)。")
# print(f"跳過 {len(skipped_columns)} 個欄位的值 (可能原因：非選項代碼欄位、無有效 value map)。") #<-- 原本的計數輸出
print(f"值轉換過程耗時: {end_time - start_time:.2f} 秒。")
print(f"最終 DataFrame 維度: {descriptive_df.shape}")

# --- 新增：印出被跳過的欄位列表 ---
if skipped_columns:
    print("\n--- 以下欄位在值轉換過程中被跳過 ---")
    pprint.pprint(skipped_columns)
else:
    print("\n--- 所有可轉換的欄位都已進行值轉換 (未跳過任何欄位) ---")


# --- 步驟 6: 查看最終結果 (範例) ---
print("\n--- 最終結果預覽 (欄位名稱和值都已轉換，前 5 筆) ---")
pd.set_option('display.max_columns', 20)
pd.set_option('display.max_colwidth', 50)
# 確保打印 head() 前 DataFrame 存在
if descriptive_df is not None:
    print(descriptive_df.head())
else:
    print("無法顯示預覽，因為 DataFrame 未成功載入或創建。")


# --- 步驟 7: (可選) 儲存最終結果 ---
# *** 請將路徑修改為您希望儲存 Parent 問卷結果的檔名 ***
final_output_path = '../data/TIGPSw1_p_descriptive_labeled.csv' # 建議新檔名
print(f"\n--- 正在將最終結果儲存至 {final_output_path} ---")
start_time = time.time()
# 確保儲存前 DataFrame 存在
if descriptive_df is not None:
    try:
        descriptive_df.to_csv(final_output_path, index=False, encoding='utf-8-sig')
        end_time = time.time()
        print(f"成功儲存檔案。耗時: {end_time - start_time:.2f} 秒。")
    except Exception as e:
        print(f"儲存最終結果 CSV 檔案時發生錯誤：{e}")
else:
     print("無法儲存檔案，因為 DataFrame 未成功載入或創建。")