# -*- coding: utf-8 -*-
import json
import pandas as pd
import time
import pprint # 保持載入，雖然此版本可能較少用到

# --- 步驟 1: 讀取 id_map 和 結構 1 的 value_maps ---

# 讀取 id_map (變項代碼 -> 變項說明)
# *** 請確保這個路徑指向 Parent 問卷的 id_map ***
id_map_file_path = 'tigps_w1_02_id_map.json' # 假設您有對應的家長問卷 id_map
loaded_id_map = None
try:
    # 指定使用 utf-8-sig 來讀取可能包含 BOM 的 utf-8 檔案
    with open(id_map_file_path, 'r', encoding='utf-8-sig') as f:
        loaded_id_map = json.load(f)
    print(f"成功從 {id_map_file_path} 讀取 id_map。")
except FileNotFoundError:
    print(f"錯誤：找不到檔案 {id_map_file_path}。請確認檔案路徑和名稱。")
    # exit() # 暫時註解 exit() 以便展示後續程式碼結構
except Exception as e:
    print(f"讀取 id_map 時發生錯誤：{e}")
    # exit() # 暫時註解 exit()

# 讀取 value_maps (結構 1: 包含 general_options 和 value_maps)
# *** 請確保這個路徑指向您使用上一段代碼產生的 Parent 問卷 Structure 1 JSON ***
value_map_file_path = 'tigps_w1_02_value_maps.json' # 指向新的結構 1 檔案
loaded_structure1_maps = None
general_options = {}
specific_value_maps = {}
try:
    # 同樣使用 utf-8-sig
    with open(value_map_file_path, 'r', encoding='utf-8-sig') as f:
        loaded_structure1_maps = json.load(f)

    # 從讀取的結構中分離 general_options 和 value_maps (特定選項)
    if loaded_structure1_maps and 'general_options' in loaded_structure1_maps and 'value_maps' in loaded_structure1_maps:
        general_options = loaded_structure1_maps['general_options']
        specific_value_maps = loaded_structure1_maps['value_maps']
        print(f"成功從 {value_map_file_path} 讀取 結構 1 的 value_maps。")
        # print("讀取的 General Options:")
        # pprint.pprint(general_options)
    else:
        print(f"錯誤：檔案 {value_map_file_path} 未包含預期的 'general_options' 和 'value_maps' 鍵。")
        # exit() # 暫時註解 exit()
except FileNotFoundError:
    print(f"錯誤：找不到檔案 {value_map_file_path}。請先執行產生結構 1 JSON 的程式碼。")
    # exit() # 暫時註解 exit()
except Exception as e:
    print(f"讀取 結構 1 value_maps 時發生錯誤：{e}")
    # exit() # 暫時註解 exit()

# --- 步驟 2: 不再需要進行大規模鍵類型轉換 ---
# 結構 1 的 JSON 預期鍵已經是字串，這裡只需要確保 general_options 的鍵也是字串 (如果原始定義是數字)
# 但我們在產生結構 1 時已確保鍵是字串，故此步驟可大幅簡化或省略。
# 為保險起見，可以做個簡單檢查確認 general_options 鍵是字串
general_options = {str(k): v for k, v in general_options.items()}
print("Value map 結構確認完成 (預期鍵為字串)。")


# --- 步驟 3: 載入您的實際完整資料 ---
# *** 請將路徑修改為 Parent 問卷的 CSV 檔案 ***
csv_file_path = '../data/TIGPSw1_p.csv' # 假設家長資料檔名
raw_data_df = None
print(f"\n正在從 {csv_file_path} 載入完整資料...")
start_time = time.time()
try:
    raw_data_df = pd.read_csv(csv_file_path, low_memory=False) # 保持 low_memory=False
    end_time = time.time()
    print(f"成功載入資料。耗時: {end_time - start_time:.2f} 秒。")
    print(f"原始資料維度 (行數, 欄數): {raw_data_df.shape}")
except FileNotFoundError:
    print(f"錯誤：找不到您的資料檔案 {csv_file_path}。")
    # exit() # 暫時註解 exit()
except Exception as e:
    print(f"載入 CSV 檔案時發生錯誤：{e}")
    # exit() # 暫時註解 exit()

# 假設讀取失敗，創建一個範例 DataFrame 以便後續程式碼運行
if raw_data_df is None:
    print("創建範例 DataFrame 以繼續...")
    raw_data_df = pd.DataFrame({
        'nschool_id': [101, 102, 101],
        'ap1': [1, 2, 1],
        'ap2': [2, 1, 2],
        'ap3': [1975, 1980, 1978], # 假設 ap3 是數值年齡
        'ap10a': [3, 4, 2],
        'ap114': [1, 2, 3]
    })
    # 同步更新 id_map (僅為範例)
    loaded_id_map = {
        'nschool_id': '學校ID',
        'ap1': '請問您是孩子的？',
        'ap2': '您的性別？',
        'ap3': '您的出生年？',
        'ap10a': '家人會彼此商量？',
        'ap114': '家庭收支平衡狀況？'
    }
    # 同步更新 specific_value_maps (僅為範例)
    specific_value_maps['ap1'] = {"1": "父親", "2": "母親"}
    specific_value_maps['ap2'] = {"1": "女", "2": "男"}
    specific_value_maps['ap10a'] = {"1": "很不符合", "2": "不符合", "3": "符合", "4": "很符合"}
    specific_value_maps['ap114'] = {"1": "沒有造成困難", "2": "造成輕微困難", "3": "造成一些困難", "4": "造成很大困難"}

# --- 步驟 4: 複製原始資料並進行欄位名稱轉換 ---
print("\n--- 正在複製資料並轉換欄位名稱 ---")
descriptive_df = raw_data_df.copy() # 直接複製一份，避免修改原始數據
valid_rename_map = {k: v for k, v in loaded_id_map.items() if k in descriptive_df.columns}
descriptive_df.rename(columns=valid_rename_map, inplace=True) # 直接在複製的 df 上修改
print(f"已將 {len(valid_rename_map)} 個欄位名稱從代碼轉換為說明。")
print(f"描述性欄位名稱 DataFrame 維度: {descriptive_df.shape}")

# 建立反向映射 (說明 -> 原始代碼)
original_code_from_desc = {}
for code, desc in valid_rename_map.items():
    if desc not in original_code_from_desc:
        original_code_from_desc[desc] = code

# --- 步驟 5: 在 descriptive_df 上進行值的轉換 (使用結構 1 maps) ---
print("\n--- 開始在描述性欄位名稱的 DataFrame 上轉換數值為標籤 (使用結構 1) ---")
start_time = time.time()
value_mapped_count = 0
value_skipped_count = 0

# 遍歷 descriptive_df 的欄位名稱 (中文說明)
for desc_col_name in descriptive_df.columns:
    original_code = original_code_from_desc.get(desc_col_name)

    # 檢查是否有此變項的特定 value map
    specific_map = specific_value_maps.get(original_code)

    # 只有當 specific_map 存在且有效時才進行轉換 (包括通用選項)
    if isinstance(specific_map, dict) and specific_map:
        # *** 核心修改：合併通用選項和特定選項 ***
        # 以特定選項優先 (specific_map 會覆蓋 general_options 中相同的鍵)
        # 確保兩個字典的鍵都是字串以利合併和 replace
        general_options_str = {str(k): v for k, v in general_options.items()}
        specific_map_str = {str(k): v for k, v in specific_map.items()}
        combined_map = {**general_options_str, **specific_map_str}

        # 檢查原始數值欄位的類型，嘗試轉為數值以便進行 replace
        # 注意：這裡假設原始代碼是數值或可以轉換為數值的字串
        # 如果原始 CSV 中代碼本來就是字串，這一步可能不需要，但做了通常無害
        # if pd.api.types.is_object_dtype(descriptive_df[desc_col_name]):
             # descriptive_df[desc_col_name] = pd.to_numeric(descriptive_df[desc_col_name], errors='coerce')
        # ** 重要：為了讓 replace 能正確匹配，需要確保 DataFrame 中的值和 map 的鍵類型一致 **
        # 由於 combined_map 的鍵是字串，我們需要確保 Series 中的值也是字串 (或者都是數值)
        # 為了處理混合類型 (例如同時有數字 1 和字串 '1')，先全部轉成字串再 replace 比較保險
        descriptive_df[desc_col_name] = descriptive_df[desc_col_name].astype(str).replace(combined_map)


        value_mapped_count += 1
        # print(f"  已轉換值: '{desc_col_name}' (原始代碼: {original_code})")

    elif original_code in specific_value_maps:
        # specific_map 存在但無效 (可能不是 dict 或為空)，計入跳過
         value_skipped_count +=1
    else:
        # 找不到 specific_map (可能是 ID、文字、或未定義的欄位)，計入跳過
        value_skipped_count += 1

end_time = time.time()
print("\n--- 值轉換完成 ---")
print(f"成功轉換 {value_mapped_count} 個欄位的值 (使用通用+特定選項)。")
print(f"跳過 {value_skipped_count} 個欄位的值 (可能原因：非選項代碼欄位、無有效 value map)。")
print(f"值轉換過程耗時: {end_time - start_time:.2f} 秒。")
print(f"最終 DataFrame 維度: {descriptive_df.shape}")

# --- 步驟 6: 查看最終結果 (範例) ---
print("\n--- 最終結果預覽 (欄位名稱和值都已轉換，前 5 筆) ---")
pd.set_option('display.max_columns', 20)
pd.set_option('display.max_colwidth', 50)
print(descriptive_df.head())

# --- 步驟 7: (可選) 儲存最終結果 ---
# *** 請將路徑修改為您希望儲存 Parent 問卷結果的檔名 ***
final_output_path = '../data/TIGPSw1_p_descriptive_labeled.csv' # 建議新檔名
print(f"\n--- 正在將最終結果儲存至 {final_output_path} ---")
start_time = time.time()
try:
    descriptive_df.to_csv(final_output_path, index=False, encoding='utf-8-sig')
    end_time = time.time()
    print(f"成功儲存檔案。耗時: {end_time - start_time:.2f} 秒。")
except Exception as e:
    print(f"儲存最終結果 CSV 檔案時發生錯誤：{e}")