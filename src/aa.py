# -*- coding: utf-8 -*-
import json
import os
import copy # 用於深層複製字典

def convert_value_map_to_structure1(input_filepath, output_filepath):
    """
    讀取一個 '結構 2' 的 value map JSON 檔案,
    將其轉換為 '結構 1' (分離 general_options 和 value_maps),
    並儲存到新的 JSON 檔案。

    Args:
        input_filepath (str): 輸入的 JSON 檔案路徑 (結構 2)。
        output_filepath (str): 輸出的 JSON 檔案路徑 (結構 1)。
    """
    print(f"\n--- 開始處理檔案: {input_filepath} ---")

    # --- 步驟 1: 讀取原始 '結構 2' JSON ---
    loaded_structure2_maps = None
    try:
        with open(input_filepath, 'r', encoding='utf-8-sig') as f:
            loaded_structure2_maps = json.load(f)
        print(f"成功從 {input_filepath} 讀取原始 value map。")
    except FileNotFoundError:
        print(f"錯誤：找不到檔案 {input_filepath}。請確認檔案路徑和名稱。")
        return
    except json.JSONDecodeError as e:
        print(f"錯誤：檔案 {input_filepath} 格式錯誤，無法解析 JSON。錯誤訊息：{e}")
        return
    except Exception as e:
        print(f"讀取檔案 {input_filepath} 時發生未知錯誤：{e}")
        return

    # --- 步驟 2: 提取通用選項 ---
    first_var_key = next(iter(loaded_structure2_maps), None)
    if not first_var_key:
        print(f"錯誤：檔案 {input_filepath} 為空或格式不符。")
        return

    general_options = {}
    potential_general_keys = {"-4", "-5", "-6", "-7", "-8", "-9", "-99", "-999"}
    # *** 修改：從第一個有效的字典值中提取通用選項 ***
    first_valid_map = None
    for key in loaded_structure2_maps:
        if isinstance(loaded_structure2_maps[key], dict):
            first_valid_map = loaded_structure2_maps[key]
            first_var_key = key # 更新 first_var_key 以便打印警告
            break # 找到第一個就跳出

    if first_valid_map:
        for key, value in first_valid_map.items():
            if key in potential_general_keys:
                general_options[str(key)] = value # 確保鍵是字串
    else:
        print(f"警告：在檔案 {input_filepath} 中未找到任何包含字典值的變項，無法提取通用選項。")
        # 您可以選擇創建一個預設的 general_options 或直接返回
        # general_options = { "-4": "不適用", ... } # 預設值範例
        # return # 如果決定無法處理就返回

    if not general_options:
         print(f"警告：在檔案 {input_filepath} 的第一個有效變項 '{first_var_key}' 中未找到通用選項代碼。")
    else:
        print(f"提取到的 General Options (共 {len(general_options)} 項):")
        # print(general_options)

    # --- 步驟 3: 提取各變項的特定選項 ---
    specific_value_maps = {}
    processed_var_count = 0
    skipped_vars = []
    for var_name, original_map in loaded_structure2_maps.items():
        if isinstance(original_map, dict):
            specific_map_for_var = {}
            for key, value in original_map.items():
                if str(key) not in general_options:
                    specific_map_for_var[str(key)] = value
            if specific_map_for_var:
                specific_value_maps[var_name] = specific_map_for_var
            processed_var_count += 1
        else:
            # *** 修改：記錄非字典格式的變項 ***
            print(f"警告：變項 '{var_name}' 的值不是預期的字典格式 (類型: {type(original_map)})，將被跳過。")
            skipped_vars.append(var_name)


    print(f"處理完成 {processed_var_count} 個字典格式的變項，提取了 {len(specific_value_maps)} 個變項的特定選項。")
    if skipped_vars:
        print(f"跳過了以下非字典格式的變項：{skipped_vars}")

    # --- 步驟 4: 組合為 '結構 1' ---
    final_output_structure1 = {
        "general_options": general_options,
        "value_maps": specific_value_maps
    }

    # --- 步驟 5: 儲存新的 JSON 檔案 ---
    print(f"正在將結果儲存至 {output_filepath}...")
    try:
        with open(output_filepath, 'w', encoding='utf-8') as f:
            json.dump(final_output_structure1, f, ensure_ascii=False, indent=4)
        print(f"成功將轉換後的 value map 儲存至 {output_filepath}")
    except IOError as e:
        print(f"錯誤：無法寫入檔案 {output_filepath}。錯誤訊息：{e}")
    except Exception as e:
        print(f"儲存新 value map 時發生未知錯誤：{e}")


# --- 主要執行區塊 ---
if __name__ == "__main__":
    # *** 修改：只處理 tigps_w1_st_value_maps.json ***
    input_file = 'tigps_w1_st_value_maps.json'
    base, ext = os.path.splitext(input_file)
    output_file = f"{base}_structure1{ext}"

    # 執行轉換函數
    convert_value_map_to_structure1(input_file, output_file)