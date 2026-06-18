import sys
import os
import tkinter as tk

# 添加用户Python库路径
user_site_packages = os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', 'Python', 'Python312', 'site-packages')
if user_site_packages not in sys.path:
    sys.path.insert(0, user_site_packages)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from file_classifier import FileClassifier
from duplicate_detector import DuplicateDetector
from content_classifier import ContentClassifier
from logger import ClassificationLogger, StatsManager
from gui import FileClassifierGUI

def main():
    root = tk.Tk()
    
    classifier = FileClassifier(
        config_path=os.path.join(os.path.dirname(__file__), 'config/file_types.json'),
        settings_path=os.path.join(os.path.dirname(__file__), 'config/settings.json')
    )
    
    content_classifier = ContentClassifier()
    
    detector = DuplicateDetector()
    logger = ClassificationLogger(
        log_file=os.path.join(os.path.dirname(__file__), 'logs/classification_log.json')
    )
    stats_manager = StatsManager(
        stats_file=os.path.join(os.path.dirname(__file__), 'logs/stats.json')
    )
    
    app = FileClassifierGUI(root, classifier, detector, logger, stats_manager, content_classifier)
    
    root.mainloop()

if __name__ == "__main__":
    main()
