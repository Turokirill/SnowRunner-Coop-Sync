import os
import json
import shutil
import time
import re 
# Для EGS
# Файлы, которые не нужно синхронизировать
EXCLUDED_FILES = {"user_profile.dat", "user_settings.dat", "user_social_data.dat", "video.dat"}

# Укажите пути к исходной и целевой папкам здесь
SOURCE_FOLDER = r"C:\Users\TUROK\Desktop\SnowRunner\base\storage\f16af2d7289641ff8c3bf3b3b979efe9"# Папка с кошерными сохранениями
TARGET_FOLDER = r"C:\\Users\\TUROK\\Documents\\My Games\\SnowRunner\\base\\storage\\5d6b546b33b4427b8932a34676f2b539"#Папка с вашими хуевыми сохранениями

def load_dat_file(file_path):
    with open(file_path, 'rb') as file:
        data = file.read()
    return data

def save_dat_file(file_path, data):
    with open(file_path, 'wb') as file:
        file.write(data)

def sync_data_with_keywords(source_data, target_data, keywords):
    """
    Рекурсивно синхронизирует данные, содержащие ключевые слова.
    Если ключ отсутствует в целевом файле, он добавляется.
    Использует регулярные выражения для поиска ключевых слов.
    """
    if source_data is None or target_data is None:
        print(f"Warning: Encountered None value in source_data or target_data. Skipping.")
        return

    # Компилируем регулярные выражения для каждого ключевого слова
    keyword_patterns = [re.compile(r'.*' + re.escape(keyword) + r'.*', re.IGNORECASE) for keyword in keywords]

    if isinstance(source_data, dict):
        for key, value in source_data.items():
            # Проверяем, если ключ содержит одно из ключевых слов
            if key not in target_data:
                target_data[key] = value
            elif any(pattern.match(key) for pattern in keyword_patterns):
                target_data[key] = value
            elif isinstance(value, (dict, list)):
                if key not in target_data or target_data[key] is None:
                    target_data[key] = {} if isinstance(value, dict) else []
                sync_data_with_keywords(value, target_data[key], keywords)
    elif isinstance(source_data, list):
        for i, item in enumerate(source_data):
            if isinstance(item, (dict, list)):
                if i >= len(target_data) or target_data[i] is None:
                    target_data.append({} if isinstance(item, dict) else [])
                sync_data_with_keywords(item, target_data[i], keywords)

def sync_json_like_files(source_file, target_file, complete_save_key):
    try:
        with open(source_file, 'r') as file:
            raw_data = file.read()
            source_data = json.loads(raw_data.rstrip('\0'))
        
        with open(target_file, 'r') as file:
            raw_data = file.read()
            target_data = json.loads(raw_data.rstrip('\0'))

        if complete_save_key not in source_data or complete_save_key not in target_data:
            print(f"Error: '{complete_save_key}' key not found in source or target.")
            return

        source_complete_save = source_data[complete_save_key]
        target_complete_save = target_data[complete_save_key]

        if not isinstance(source_complete_save, dict):
            print(f"Error: '{complete_save_key}' in source is not a dictionary.")
            return

        if not isinstance(target_complete_save, dict):
            print(f"Error: '{complete_save_key}' in target is not a dictionary.")
            return

        if 'SslValue' not in target_complete_save:
            target_complete_save['SslValue'] = {}

        if 'persistentProfileData' not in target_complete_save['SslValue']:
            target_complete_save['SslValue']['persistentProfileData'] = {}

        print('Transferring unlocks and upgrades...')
        target_complete_save['SslValue']['upgradesGiverData'] = source_complete_save['SslValue'].get('upgradesGiverData', {})
        target_complete_save['SslValue']['persistentProfileData']['discoveredUpgrades'] = source_complete_save['SslValue']['persistentProfileData'].get('discoveredUpgrades', [])
        target_complete_save['SslValue']['persistentProfileData']['unlockedItemNames'] = source_complete_save['SslValue']['persistentProfileData'].get('unlockedItemNames', [])
        target_complete_save['SslValue']['persistentProfileData']['discoveredObjectives'] = source_complete_save['SslValue']['persistentProfileData'].get('discoveredObjectives', [])
        
        keywords = ["zone", "TSK", "level", "Cargo", "STATION", "Object", "OBJ", "State", "Delivery", "Objectives"] #Добавить "US" и "RU" для синхронизации машин. Если что то не синхронизировано, добавить слово ключ из файла CompleteSave
        print('Transferring data with keywords:', keywords)
        sync_data_with_keywords(source_complete_save, target_complete_save, keywords)

        backup_path = '{}.{}.bck'.format(target_file, str(round(time.time() * 1000)))
        print('Backing up target save to:', backup_path)
        shutil.copy2(target_file, backup_path)

        print('Writing updated save...')
        with open(target_file, 'w') as file:
            data = json.dumps(target_data) + '\0'
            file.write(data)
        print(f"Successfully synced {os.path.basename(target_file)}")
    except KeyError as e:
        print(f"Error: Missing expected key in source data: {e}")
    except Exception as e:
        print(f"Error processing {os.path.basename(target_file)}: {e}")

def sync_binary_files(source_file, target_file):
    try:
        source_data = load_dat_file(source_file)
        save_dat_file(target_file, source_data)
        print(f"Successfully synced {os.path.basename(target_file)}")
    except Exception as e:
        print(f"Error processing {os.path.basename(target_file)}: {e}")

def sync_folders(source_folder, target_folder):
    complete_save_key = input("Какое сохранение (пусто-CompleteSave, 1-CompleteSave1 и т.д)? ").strip()
    if complete_save_key:
        complete_save_key = f"CompleteSave{complete_save_key}"
    else:
        complete_save_key = "CompleteSave"
        
    for root, dirs, files in os.walk(source_folder):
        for file in files:
            if file in EXCLUDED_FILES:
                print(f"Skipping excluded file: {file}")
                continue

            source_file = os.path.join(root, file)
            relative_path = os.path.relpath(source_file, source_folder)
            target_file = os.path.join(target_folder, relative_path)

            if not os.path.exists(target_file):
                print(f"File {file} does not exist in target folder, copying...")
                os.makedirs(os.path.dirname(target_file), exist_ok=True)
                shutil.copy2(source_file, target_file)
                continue

            try:
                with open(source_file, 'r') as f:
                    json.loads(f.read().rstrip('\0'))
                sync_json_like_files(source_file, target_file, complete_save_key)
            except ValueError:
                sync_binary_files(source_file, target_file)

if __name__ == "__main__":
    if not os.path.exists(SOURCE_FOLDER) or not os.path.exists(TARGET_FOLDER):
        print("One of the specified folders does not exist. Please check the paths.")
    else:
        sync_folders(SOURCE_FOLDER, TARGET_FOLDER)
        print("Synchronization completed.")
