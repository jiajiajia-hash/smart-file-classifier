import json
import os
from datetime import datetime

class ClassificationLogger:
    def __init__(self, log_file='logs/classification_log.json'):
        self.log_file = log_file
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    def log_classification(self, results, source_dir, classification_type):
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'source_dir': source_dir,
            'classification_type': classification_type,
            'files_processed': len(results),
            'details': results
        }
        
        try:
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            else:
                logs = []
            
            logs.append(log_entry)
            
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"写入日志失败: {e}")
            return False
    
    def get_logs(self):
        try:
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception:
            return []
    
    def clear_logs(self):
        try:
            if os.path.exists(self.log_file):
                os.remove(self.log_file)
            return True
        except Exception:
            return False

class StatsManager:
    def __init__(self, stats_file='logs/stats.json'):
        self.stats_file = stats_file
        os.makedirs(os.path.dirname(stats_file), exist_ok=True)
    
    def save_stats(self, stats, classification_type):
        stats_entry = {
            'timestamp': datetime.now().isoformat(),
            'classification_type': classification_type,
            'stats': stats
        }
        
        try:
            if os.path.exists(self.stats_file):
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    all_stats = json.load(f)
            else:
                all_stats = []
            
            all_stats.append(stats_entry)
            
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(all_stats, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"保存统计失败: {e}")
            return False
    
    def get_stats(self):
        try:
            if os.path.exists(self.stats_file):
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception:
            return []
    
    def get_latest_stats(self):
        stats = self.get_stats()
        if stats:
            return stats[-1]
        return None