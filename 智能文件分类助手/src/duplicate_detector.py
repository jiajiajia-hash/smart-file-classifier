import os
import hashlib
import shutil
import json
from datetime import datetime
from pathlib import Path

class DuplicateDetector:
    def __init__(self):
        self.hash_cache = {}
        self.recycle_bin_folder = "_回收站"
        self.recycle_log_file = os.path.join('logs', 'recycle_log.json')
        os.makedirs('logs', exist_ok=True)
    
    def get_file_hash(self, file_path, chunk_size=8192):
        if file_path in self.hash_cache:
            return self.hash_cache[file_path]
        
        try:
            hasher = hashlib.md5()
            with open(file_path, 'rb') as f:
                while chunk := f.read(chunk_size):
                    hasher.update(chunk)
            file_hash = hasher.hexdigest()
            self.hash_cache[file_path] = file_hash
            return file_hash
        except Exception:
            return None
        
    # 接收目标目录，遍历并查找所有重复文件
    def detect_duplicates(self, directory):
        hash_groups = {}
        
        for root, dirs, files in os.walk(directory):
            for filename in files:
                file_path = os.path.join(root, filename)
                
                if not os.path.isfile(file_path):
                    continue
                # 以哈希值为键，对文件路径分组
                file_hash = self.get_file_hash(file_path)
                if file_hash:
                    if file_hash not in hash_groups:
                        hash_groups[file_hash] = []
                    hash_groups[file_hash].append(file_path)
        
        duplicates = []
        for file_hash, paths in hash_groups.items():
            if len(paths) > 1:
                duplicates.append(paths)
        
        return duplicates
    
    def find_large_files(self, directory, threshold=104857600):
        large_files = []
        
        for root, dirs, files in os.walk(directory):
            for filename in files:
                file_path = os.path.join(root, filename)
                
                try:
                    file_size = os.path.getsize(file_path)
                    if file_size >= threshold:
                        large_files.append({
                            'path': file_path,
                            'size': file_size,
                            'size_readable': self.format_size(file_size)
                        })
                except Exception:
                    continue
        
        large_files.sort(key=lambda x: x['size'], reverse=True)
        return large_files
    
    def format_size(self, size_bytes):
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
    
    def delete_duplicates(self, duplicate_groups, keep_first=True):
        deleted_count = 0
        deleted_files = []
        
        for group in duplicate_groups:
            if keep_first:
                files_to_delete = group[1:]
            else:
                files_to_delete = group[:-1]
            
            for file_path in files_to_delete:
                try:
                    os.remove(file_path)
                    deleted_count += 1
                    deleted_files.append(file_path)
                except Exception as e:
                    print(f"删除失败 {file_path}: {e}")
        
        return deleted_count, deleted_files
    
    def move_to_recycle_bin(self, file_path, source_dir):
        """将文件移动到回收站"""
        try:
            recycle_bin = os.path.join(source_dir, self.recycle_bin_folder)
            os.makedirs(recycle_bin, exist_ok=True)
            
            filename = os.path.basename(file_path)
            dest_path = os.path.join(recycle_bin, filename)
            
            # 处理重名文件
            counter = 1
            while os.path.exists(dest_path):
                name, ext = os.path.splitext(filename)
                dest_path = os.path.join(recycle_bin, f"{name}_{counter}{ext}")
                counter += 1
            
            shutil.move(file_path, dest_path)
            
            # 记录到日志
            self.log_recycle_item(file_path, dest_path, source_dir)
            
            return True, dest_path
        except Exception as e:
            return False, str(e)
    
    def log_recycle_item(self, original_path, recycle_path, source_dir):
        """记录回收项目到日志"""
        log_entry = {
            'original_path': original_path,
            'recycle_path': recycle_path,
            'source_dir': source_dir,
            'timestamp': datetime.now().isoformat(),
            'filename': os.path.basename(original_path)
        }
        
        # 加载现有日志
        logs = []
        if os.path.exists(self.recycle_log_file):
            try:
                with open(self.recycle_log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            except:
                pass
        
        logs.append(log_entry)
        
        # 保存日志
        with open(self.recycle_log_file, 'w', encoding='utf-8') as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
    
    def get_recycle_items(self, source_dir):
        """获取指定目录回收站中的项目"""
        recycle_bin = os.path.join(source_dir, self.recycle_bin_folder)
        if not os.path.exists(recycle_bin):
            return []
        
        # 从日志获取
        logs = []
        if os.path.exists(self.recycle_log_file):
            try:
                with open(self.recycle_log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            except:
                pass
        
        # 过滤属于当前目录的项目，并且文件还在回收站中
        items = []
        for log in logs:
            if log.get('source_dir') == source_dir and os.path.exists(log.get('recycle_path')):
                items.append(log)
        
        return items
    
    def restore_from_recycle_bin(self, recycle_item):
        """从回收站还原文件"""
        try:
            recycle_path = recycle_item.get('recycle_path')
            original_path = recycle_item.get('original_path')
            
            if not os.path.exists(recycle_path):
                return False, "文件不存在于回收站中"
            
            # 确保目标目录存在
            original_dir = os.path.dirname(original_path)
            os.makedirs(original_dir, exist_ok=True)
            
            # 处理重名文件
            dest_path = original_path
            counter = 1
            while os.path.exists(dest_path):
                name, ext = os.path.splitext(os.path.basename(original_path))
                dest_path = os.path.join(original_dir, f"{name}_还原{counter}{ext}")
                counter += 1
            
            shutil.move(recycle_path, dest_path)
            
            # 更新日志，标记为已还原
            self.remove_from_recycle_log(recycle_item)
            
            return True, dest_path
        except Exception as e:
            return False, str(e)
    
    def permanently_delete(self, recycle_item):
        """永久删除回收站中的文件"""
        try:
            recycle_path = recycle_item.get('recycle_path')
            if os.path.exists(recycle_path):
                os.remove(recycle_path)
            
            self.remove_from_recycle_log(recycle_item)
            return True
        except Exception as e:
            return False
    
    def remove_from_recycle_log(self, recycle_item):
        """从日志中移除项目"""
        if not os.path.exists(self.recycle_log_file):
            return
        
        try:
            with open(self.recycle_log_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
            
            # 过滤掉要移除的项目
            updated_logs = [log for log in logs if 
                           not (log.get('recycle_path') == recycle_item.get('recycle_path') and 
                                log.get('original_path') == recycle_item.get('original_path'))]
            
            with open(self.recycle_log_file, 'w', encoding='utf-8') as f:
                json.dump(updated_logs, f, ensure_ascii=False, indent=2)
        except:
            pass