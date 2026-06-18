import os
import shutil
import json
from datetime import datetime, timedelta
from pathlib import Path

class FileClassifier:
    def __init__(self, config_path='config/file_types.json', settings_path='config/settings.json'):
        self.file_types = self.load_config(config_path)
        self.settings = self.load_settings(settings_path)
        self.classification_stats = {}
        self.last_classification = []
        self.last_ai_classification = []  # 记录AI分类操作
        self.reset_stats()
        self.illegal_chars = '<>:\"\\|?*'

    def sanitize_filename(self, filename):
        """过滤文件名中的非法字符，将 <>:\"\\|?* 替换为下划线"""
        sanitized = []
        for char in filename:
            if char in self.illegal_chars:
                sanitized.append('_')
            else:
                sanitized.append(char)
        return ''.join(sanitized)

    def load_config(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return self.get_default_file_types()

    def load_settings(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return self.get_default_settings()

    def get_default_file_types(self):
        return {
            "【01-图片】": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".svg", ".ico", ".webp", ".heic"],
            "【02-文档】": [".txt", ".doc", ".docx", ".pdf", ".xls", ".xlsx", ".ppt", ".pptx", ".csv", ".json", ".xml", ".md"],
            "【03-视频】": [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v"],
            "【04-音频】": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"],
            "【05-压缩包】": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"],
            "【06-程序安装包】": [".exe", ".msi"],
            "【其他未知格式】": []
        }

    def get_default_settings(self):
        return {
            "backup_mode": True,
            "backup_folder": "_分类备份",
            "large_file_threshold": 104857600,
            "exclude_files": ["desktop.ini", "Thumbs.db", ".DS_Store"],
            "exclude_extensions": [".lnk"],
            "log_file": "logs/classification_log.json",
            "stats_file": "logs/stats.json",
            "dark_mode": False,
            "size_categories": {
                "小文件(<1MB)": 1048576,
                "中文件(1M-100M)": 104857600,
                "大文件(>100MB)": 1048576000
            },
            "time_categories": {
                "今日文件": 0,
                "本周文件": 7,
                "上月文件": 30,
                "更早归档": 9999
            }
        }

    def reset_stats(self):
        self.classification_stats = {category: 0 for category in self.file_types.keys()}
        self.classification_stats['【07-超大文件(>100MB)】'] = 0
        self.classification_stats['跳过'] = 0
        self.classification_stats['重复文件'] = 0

    def get_category(self, filename):
        ext = Path(filename).suffix.lower()
        for category, extensions in self.file_types.items():
            if ext in extensions:
                return category
        return "【其他未知格式】"

    def get_time_category(self, file_path):
        try:
            mtime = os.path.getmtime(file_path)
            file_time = datetime.fromtimestamp(mtime)
            now = datetime.now()
            days_diff = (now - file_time).days
            
            if days_diff == 0:
                return "今日文件"
            elif days_diff <= 7:
                return "本周文件"
            elif days_diff <= 30:
                return "上月文件"
            else:
                return "更早归档"
        except:
            return "更早归档"

    def get_size_category(self, file_size):
        if file_size < 1024 * 1024:
            return "小文件_1MB以下"
        elif file_size < 100 * 1024 * 1024:
            return "中文件_1M-100M"
        else:
            return "大文件_100MB以上"

    def is_excluded(self, filename):
        name = os.path.basename(filename).lower()
        ext = Path(filename).suffix.lower()
        return name in self.settings['exclude_files'] or ext in self.settings['exclude_extensions']

    def is_large_file(self, file_path):
        try:
            return os.path.getsize(file_path) >= self.settings['large_file_threshold']
        except:
            return False

    def create_backup(self, source_path, backup_dir):
        try:
            os.makedirs(backup_dir, exist_ok=True)
            dest_path = os.path.join(backup_dir, os.path.basename(source_path))
            if os.path.exists(dest_path):
                base, ext = os.path.splitext(os.path.basename(source_path))
                counter = 1
                while os.path.exists(os.path.join(backup_dir, f"{base}_{counter}{ext}")):
                    counter += 1
                dest_path = os.path.join(backup_dir, f"{base}_{counter}{ext}")
            shutil.copy2(source_path, dest_path)
            return dest_path
        except Exception as e:
            print(f"备份失败 {source_path}: {e}")
            return None

    def classify_by_type(self, source_dir, dest_dir=None, filter_keyword=None):
        if dest_dir is None:
            dest_dir = source_dir
        
        self.reset_stats()
        self.last_classification = []
        results = []
        
        try:
            items = os.listdir(source_dir)
        except PermissionError:
            print(f"无法访问目录: {source_dir}")
            self.classification_stats['跳过'] += 1
            return results
        
        backup_dir = os.path.join(dest_dir, self.settings['backup_folder'])
        
        debug_info = []
        
        for item in items:
            item_path = os.path.join(source_dir, item)
            
            try:
                is_file = os.path.isfile(item_path)
                if not is_file:
                    debug_info.append(f"跳过（非文件）: {item}")
                    continue
                
                if self.is_excluded(item):
                    excluded_reason = "扩展名" if Path(item).suffix.lower() in self.settings['exclude_extensions'] else "文件名"
                    debug_info.append(f"排除（{excluded_reason}）: {item}")
                    self.classification_stats['跳过'] += 1
                    continue
                
                # 筛选关键词检查
                if filter_keyword and filter_keyword not in item:
                    debug_info.append(f"跳过（不匹配关键词）: {item}")
                    self.classification_stats['跳过'] += 1
                    continue
                
                category = self.get_category(item)
                file_size = os.path.getsize(item_path)
                
                target_folder = os.path.join(dest_dir, category)
                os.makedirs(target_folder, exist_ok=True)
                
                if self.settings['backup_mode']:
                    self.create_backup(item_path, backup_dir)
                
                sanitized_item = self.sanitize_filename(item)
                if sanitized_item != item:
                    debug_info.append(f"⚠️ 文件名已修正: {item} → {sanitized_item}")
                
                dest_path = os.path.join(target_folder, sanitized_item)
                if os.path.exists(dest_path):
                    base, ext = os.path.splitext(sanitized_item)
                    counter = 1
                    while os.path.exists(os.path.join(target_folder, f"{base}_{counter}{ext}")):
                        counter += 1
                    dest_path = os.path.join(target_folder, f"{base}_{counter}{ext}")
                
                shutil.move(item_path, dest_path)
                self.classification_stats[category] += 1
                debug_info.append(f"✓ 分类成功: {item} → {category}")
                
                result_item = {
                    'original': item_path,
                    'destination': dest_path,
                    'category': category,
                    'size': file_size,
                    'time': datetime.now().isoformat()
                }
                results.append(result_item)
                self.last_classification.append(result_item)
                
            except PermissionError:
                self.classification_stats['跳过'] += 1
                debug_info.append(f"权限不足: {item}")
            except Exception as e:
                self.classification_stats['失败'] = self.classification_stats.get('失败', 0) + 1
                debug_info.append(f"失败: {item} - {str(e)}")
        
        self._debug_info = debug_info
        return results

    def classify_by_time(self, source_dir, dest_dir=None, filter_keyword=None):
        if dest_dir is None:
            dest_dir = source_dir
        
        self.reset_stats()
        self.last_classification = []
        results = []
        
        try:
            items = os.listdir(source_dir)
        except PermissionError:
            print(f"无法访问目录: {source_dir}")
            self.classification_stats['跳过'] += 1
            return results
        
        backup_dir = os.path.join(dest_dir, self.settings['backup_folder'])
        debug_info = []
        
        for item in items:
            item_path = os.path.join(source_dir, item)
            
            try:
                if not os.path.isfile(item_path):
                    debug_info.append(f"跳过（非文件）: {item}")
                    continue
                
                if self.is_excluded(item):
                    debug_info.append(f"排除: {item}")
                    self.classification_stats['跳过'] += 1
                    continue
                
                # 筛选关键词检查
                if filter_keyword and filter_keyword not in item:
                    debug_info.append(f"跳过（不匹配关键词）: {item}")
                    self.classification_stats['跳过'] += 1
                    continue
                
                time_category = self.get_time_category(item_path)
                target_folder = os.path.join(dest_dir, time_category)
                os.makedirs(target_folder, exist_ok=True)
                
                if self.settings['backup_mode']:
                    self.create_backup(item_path, backup_dir)
                
                sanitized_item = self.sanitize_filename(item)
                if sanitized_item != item:
                    debug_info.append(f"⚠️ 文件名已修正: {item} → {sanitized_item}")
                
                dest_path = os.path.join(target_folder, sanitized_item)
                if os.path.exists(dest_path):
                    base, ext = os.path.splitext(sanitized_item)
                    counter = 1
                    while os.path.exists(os.path.join(target_folder, f"{base}_{counter}{ext}")):
                        counter += 1
                    dest_path = os.path.join(target_folder, f"{base}_{counter}{ext}")
                
                shutil.move(item_path, dest_path)
                self.classification_stats[time_category] = self.classification_stats.get(time_category, 0) + 1
                debug_info.append(f"✓ 分类成功: {item} → {time_category}")
                
                result_item = {
                    'original': item_path,
                    'destination': dest_path,
                    'category': time_category,
                    'time': datetime.now().isoformat()
                }
                results.append(result_item)
                self.last_classification.append(result_item)
                
            except PermissionError:
                self.classification_stats['跳过'] += 1
                debug_info.append(f"权限不足: {item}")
            except Exception as e:
                self.classification_stats['失败'] = self.classification_stats.get('失败', 0) + 1
                debug_info.append(f"失败: {item} - {str(e)}")
        
        self._debug_info = debug_info
        return results

    def classify_by_size(self, source_dir, dest_dir=None, filter_keyword=None):
        if dest_dir is None:
            dest_dir = source_dir
        
        self.reset_stats()
        self.last_classification = []
        results = []
        
        try:
            items = os.listdir(source_dir)
        except PermissionError:
            print(f"无法访问目录: {source_dir}")
            self.classification_stats['跳过'] += 1
            return results
        
        backup_dir = os.path.join(dest_dir, self.settings['backup_folder'])
        debug_info = []
        
        for item in items:
            item_path = os.path.join(source_dir, item)
            
            try:
                if not os.path.isfile(item_path):
                    debug_info.append(f"跳过（非文件）: {item}")
                    continue
                
                if self.is_excluded(item):
                    debug_info.append(f"排除: {item}")
                    self.classification_stats['跳过'] += 1
                    continue
                
                # 筛选关键词检查
                if filter_keyword and filter_keyword not in item:
                    debug_info.append(f"跳过（不匹配关键词）: {item}")
                    self.classification_stats['跳过'] += 1
                    continue
                
                file_size = os.path.getsize(item_path)
                size_category = self.get_size_category(file_size)
                target_folder = os.path.join(dest_dir, size_category)
                os.makedirs(target_folder, exist_ok=True)
                
                if self.settings['backup_mode']:
                    self.create_backup(item_path, backup_dir)
                
                sanitized_item = self.sanitize_filename(item)
                if sanitized_item != item:
                    debug_info.append(f"⚠️ 文件名已修正: {item} → {sanitized_item}")
                
                dest_path = os.path.join(target_folder, sanitized_item)
                if os.path.exists(dest_path):
                    base, ext = os.path.splitext(sanitized_item)
                    counter = 1
                    while os.path.exists(os.path.join(target_folder, f"{base}_{counter}{ext}")):
                        counter += 1
                    dest_path = os.path.join(target_folder, f"{base}_{counter}{ext}")
                
                shutil.move(item_path, dest_path)
                self.classification_stats[size_category] = self.classification_stats.get(size_category, 0) + 1
                debug_info.append(f"✓ 分类成功: {item} → {size_category}")
                
                result_item = {
                    'original': item_path,
                    'destination': dest_path,
                    'category': size_category,
                    'size': file_size,
                    'time': datetime.now().isoformat()
                }
                results.append(result_item)
                self.last_classification.append(result_item)
                
            except PermissionError:
                self.classification_stats['跳过'] += 1
                debug_info.append(f"权限不足: {item}")
            except Exception as e:
                self.classification_stats['失败'] = self.classification_stats.get('失败', 0) + 1
                debug_info.append(f"失败: {item} - {str(e)}")
        
        self._debug_info = debug_info
        return results

    def undo_last_classification(self):
        if not self.last_classification:
            return False, "没有可撤销的分类操作"
        
        success_count = 0
        fail_count = 0
        
        for item in reversed(self.last_classification):
            try:
                if os.path.exists(item['destination']):
                    shutil.move(item['destination'], item['original'])
                    success_count += 1
            except Exception as e:
                fail_count += 1
                print(f"撤销失败 {item['destination']}: {e}")
        
        self.last_classification = []
        return True, f"撤销完成：成功还原 {success_count} 个文件，失败 {fail_count} 个文件"

    def get_stats(self):
        return self.classification_stats

    def get_last_classification(self):
        return self.last_classification
    
    def get_debug_info(self):
        return getattr(self, '_debug_info', [])

    def get_directory_stats(self, directory):
        stats = {
            'total': 0,
            'total_size': 0,
            'categories': {}
        }
        
        try:
            for item in os.listdir(directory):
                item_path = os.path.join(directory, item)
                try:
                    if os.path.isfile(item_path) and not self.is_excluded(item):
                        stats['total'] += 1
                        stats['total_size'] += os.path.getsize(item_path)
                        category = self.get_category(item)
                        if category not in stats['categories']:
                            stats['categories'][category] = {'count': 0, 'size': 0}
                        stats['categories'][category]['count'] += 1
                        stats['categories'][category]['size'] += os.path.getsize(item_path)
                except Exception:
                    continue
        except Exception:
            pass
        
        return stats
    
    def record_ai_classification(self, categorized, source_dir):
        """记录AI分类操作以便撤销"""
        self.last_ai_classification = []
        
        for category, items in categorized.items():
            folder_name = category.replace("【AI分类】", "").replace("【AI语义】", "")
            folder_path = os.path.join(source_dir, folder_name)
            
            for item in items:
                self.last_ai_classification.append({
                    'original_path': item['path'],
                    'new_path': os.path.join(folder_path, item['filename']),
                    'category': category
                })
    
    def undo_ai_classification(self):
        """撤销AI分类操作"""
        if not self.last_ai_classification:
            return False, "没有可撤销的AI分类操作"
        
        restored_count = 0
        failed_count = 0
        
        for record in self.last_ai_classification:
            src = record['original_path']
            dst = record['new_path']
            
            try:
                # 如果新路径存在，说明文件被移动了，需要还原
                if os.path.exists(dst):
                    shutil.move(dst, src)
                    restored_count += 1
            except Exception as e:
                failed_count += 1
                print(f"还原失败 {dst}: {e}")
        
        # 删除AI分类创建的文件夹
        try:
            categories = set([r['category'] for r in self.last_ai_classification])
            source_dir = os.path.dirname(self.last_ai_classification[0]['original_path'])
            for category in categories:
                folder_name = category.replace("【AI分类】", "").replace("【AI语义】", "")
                folder_path = os.path.join(source_dir, folder_name)
                if os.path.exists(folder_path) and not os.listdir(folder_path):
                    os.rmdir(folder_path)
        except:
            pass
        
        self.last_ai_classification = []
        
        message = f"已还原 {restored_count} 个文件"
        if failed_count > 0:
            message += f"，失败 {failed_count} 个"
        
        return True, message