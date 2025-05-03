# -*- coding: utf-8 -*-
import json
from collections import Counter # 用於計算元素出現次數
import os

# --- 設定檔案路徑 ---
input_id_map_path = '../maps/tigps_w1_t_id_map.json' # 輸入的家長 id_map 檔案
output_id_map_path = '../maps/tigps_w1_t_id_map.json' # 輸出的、說明文字唯一的 id_map 檔案

# --- 步驟 1: 讀取原始 id_map ---
loaded_id_map = None
print(f"正在從 {input_id_map_path} 讀取 id_map...")
try:
    # 使用 utf-8-sig 讀取可能包含 BOM 的 utf-8 檔案
    with open(input_id_map_path, 'r', encoding='utf-8-sig') as f:
        loaded_id_map = json.load(f)
    print("成功讀取 id_map。")
except FileNotFoundError:
    print(f"錯誤：找不到檔案 {input_id_map_path}。請確認檔案存在於腳本相同目錄下，或提供完整路徑。")
    exit()
except json.JSONDecodeError as e:
    print(f"錯誤：檔案 {input_id_map_path} 格式錯誤，無法解析 JSON。錯誤訊息：{e}")
    exit()
except Exception as e:
    print(f"讀取 id_map 時發生未知錯誤：{e}")
    exit()

# --- 步驟 2: 找出重複的說明文字 ---
print("\n正在檢查重複的說明文字...")
description_list = list(loaded_id_map.values()) # 取得所有說明文字的列表
description_counts = Counter(description_list) # 計算每個說明文字出現的次數
# 找出出現次數大於 1 的說明文字
duplicate_descriptions = {desc for desc, count in description_counts.items() if count > 1}

if duplicate_descriptions:
    print(f"發現 {len(duplicate_descriptions)} 個重複的說明文字將被修改。")
    # print("重複的說明文字列表:")
    # pprint.pprint(duplicate_descriptions) # 可選：印出哪些是重複的
else:
    print("未發現重複的說明文字，無需修改。")
    # 如果沒有重複，可以直接結束或選擇性地複製原始檔案
    # exit()

# --- 步驟 3: 建立新的 id_map，為重複說明添加後綴 ---
print("\n正在建立新的 id_map...")
modified_id_map = {}
modified_count = 0

# 遍歷原始 id_map 的每一個項目 (變項代碼: 說明文字)
for code, description in loaded_id_map.items():
    # 檢查當前的說明文字是否在重複列表中
    if description in duplicate_descriptions:
        # 如果是重複的，創建新的唯一說明文字 (原說明_變項代碼)
        new_description = f"{description}_{code}"
        modified_id_map[code] = new_description
        modified_count += 1
        # print(f"  修改: '{description}' -> '{new_description}' (for code: {code})") # 可選：顯示修改過程
    else:
        # 如果不是重複的，保持原樣
        modified_id_map[code] = description

print(f"處理完成，共修改了 {modified_count} 個重複說明文字的項目。")

# --- 步驟 4: 將修改後的 id_map 儲存到新的 JSON 檔案 ---
print(f"\n正在將結果儲存至 {output_id_map_path}...")
try:
    with open(output_id_map_path, 'w', encoding='utf-8') as f:
        # ensure_ascii=False 確保中文字符正確寫入
        # indent=4 使輸出的 JSON 檔案格式易讀
        json.dump(modified_id_map, f, ensure_ascii=False, indent=4)
    print(f"成功將修改後的 id_map 儲存至 {output_id_map_path}")
except IOError as e:
    print(f"錯誤：無法寫入檔案 {output_id_map_path}。請檢查權限或路徑。錯誤訊息：{e}")
except Exception as e:
    print(f"儲存新 id_map 時發生未知錯誤：{e}")