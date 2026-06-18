import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import os
import sys
import json
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.patches import Wedge
import matplotlib.font_manager as fm
import shutil

def set_chinese_font():
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False

try:
    import ctypes
    import ctypes.wintypes

    user32 = ctypes.windll.user32
    ole32 = ctypes.windll.ole32

    WM_DROPFILES = 0x0233

    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

def setup_drop_support(root, callback):
    if not DND_AVAILABLE:
        return

    try:
        ole32.OleInitialize(None)

        hwnd = root.winfo_id()
        user32.DragAcceptFiles(hwnd, True)

        def check_drop(event=None):
            try:
                msg = ctypes.wintypes.MSG()
                while user32.PeekMessageW(ctypes.byref(msg), hwnd, WM_DROPFILES, WM_DROPFILES, 1):
                    if msg.message == WM_DROPFILES:
                        hDrop = msg.wParam
                        num_files = user32.DragQueryFileW(hDrop, -1, None, 0)
                        if num_files > 0:
                            buf = ctypes.create_unicode_buffer(260)
                            user32.DragQueryFileW(hDrop, 0, buf, 260)
                            path = buf.value
                            if callback:
                                callback(path)
                        user32.DragFinish(hDrop)
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))
            except:
                pass
            root.after(100, check_drop)

        root.after(100, check_drop)

    except Exception as e:
        print(f"Drop setup failed: {e}")

class FileClassifierGUI:
    def __init__(self, master, classifier, detector, logger, stats_manager, content_classifier=None):
        self.master = master
        self.classifier = classifier
        self.detector = detector
        self.logger = logger
        self.stats_manager = stats_manager
        self.content_classifier = content_classifier
        self.dark_mode = False
        self.current_dir = ""
        self.duplicates = []
        self.large_files = []
        self.last_results = []
        self.dnd_available = DND_AVAILABLE

        self.setup_styles()
        self.create_widgets()

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')

        # 浅色主题
        self.light_colors = {
            'bg': '#ffffff',
            'fg': '#333333',
            'frame': '#f5f5f5',
            'header': '#4a90d9',
            'header_fg': '#ffffff',
            'success': '#2ecc71',
            'warning': '#f39c12',
            'error': '#e74c3c',
            'info': '#3498db',
            'green_btn': '#27ae60',
            'blue_btn': '#3498db'
        }

        # 深色主题
        self.dark_colors = {
            'bg': '#2d2d2d',
            'fg': '#ecf0f1',
            'frame': '#353535',
            'header': '#2c3e50',
            'header_fg': '#ecf0f1',
            'success': '#27ae60',
            'warning': '#f39c12',
            'error': '#e74c3c',
            'info': '#2980b9',
            'green_btn': '#1e8449',
            'blue_btn': '#2980b9'
        }

        self.colors = self.light_colors
        self.dark_mode = False

        self.style.configure('Header.TLabel', foreground=self.colors['header_fg'], font=('Arial', 16, 'bold'))
        self.style.configure('Green.TButton', background=self.colors['green_btn'], 
                           foreground='white', font=('Arial', 10, 'bold'))
        self.style.configure('Blue.TButton', background=self.colors['blue_btn'], 
                           foreground='white', font=('Arial', 10, 'bold'))
        self.style.configure('Orange.TButton', background='#E07749', 
                           foreground='white', font=('Arial', 10, 'bold'))
        self.style.configure('Browse.TButton', background=self.colors['info'], 
                           foreground='white', font=('Arial', 10))
        self.style.configure('DarkMode.TButton', background='#4a4a4a', 
                           foreground='white', font=('Arial', 10))

    def create_widgets(self):
        self.master.title("智能文件分类助手")
        self.master.geometry("950x750")
        self.master.resizable(True, True)

        # 设置窗口行权重，让分布更均匀
        self.master.rowconfigure(0, weight=0)  # 标题栏（固定高度）
        self.master.rowconfigure(1, weight=0)  # 目录选择（固定高度）
        self.master.rowconfigure(2, weight=2)  # 拖拽区域（占较大空间）
        self.master.rowconfigure(3, weight=0)  # 分类按钮（固定高度）
        self.master.rowconfigure(4, weight=0)  # 高级功能（固定高度）
        self.master.rowconfigure(5, weight=3)  # 结果区（占最大空间）
        self.master.rowconfigure(6, weight=0)  # 状态栏（固定高度）
        self.master.columnconfigure(0, weight=1)

        # 标题栏
        self.header_frame = tk.Frame(self.master, bg=self.colors['header'], padx=15, pady=12)
        self.header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
        self.header_frame.columnconfigure(0, weight=1)

        self.title_label = tk.Label(self.header_frame, text="🧠 智能文件分类助手", 
                                     font=('Arial', 18, 'bold'), bg=self.colors['header'], fg=self.colors['header_fg'])
        self.title_label.grid(row=0, column=0)

        # 目录选择区
        self.dir_frame = tk.Frame(self.master, bg=self.colors['bg'], padx=10, pady=8)
        self.dir_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=3)
        self.dir_frame.columnconfigure(1, weight=1)

        self.dir_label = tk.Label(self.dir_frame, text="📂 目标目录:", font=('Arial', 11), bg=self.colors['bg'], fg=self.colors['fg'])
        self.dir_label.grid(row=0, column=0, sticky=tk.W, padx=5)

        self.dir_entry = ttk.Entry(self.dir_frame, font=('Arial', 11), width=50)
        self.dir_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        self.dir_entry.insert(0, os.path.expanduser("~/Desktop"))
        self.dir_entry.bind('<KeyRelease>', self.validate_path)

        self.browse_btn = ttk.Button(self.dir_frame, text="🔍 浏览", command=self.browse_directory,
                                     style='Browse.TButton')
        self.browse_btn.grid(row=0, column=2, padx=5)

        # 筛选关键词
        self.filter_label = tk.Label(self.dir_frame, text="🔎 关键词:", font=('Arial', 11), bg=self.colors['bg'], fg=self.colors['fg'])
        self.filter_label.grid(row=1, column=0, sticky=tk.W, padx=5, pady=(8, 0))

        self.filter_entry = ttk.Entry(self.dir_frame, font=('Arial', 11), width=50)
        self.filter_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=(8, 0))

        self.filter_tip = tk.Label(self.dir_frame, text="（留空则分类所有文件，输入关键词则只分类含关键词的文件）", 
                                    font=('Arial', 9), bg=self.colors['bg'], fg='gray')
        self.filter_tip.grid(row=2, column=1, sticky=tk.W, padx=5)

        self.path_status = tk.Label(self.dir_frame, text="", font=('Arial', 10), bg=self.colors['bg'])
        self.path_status.grid(row=3, column=1, sticky=tk.W, padx=5)

        # 拖拽区域
        self.drop_frame = tk.LabelFrame(self.master, text="📥 拖拽区域", bg=self.colors['frame'], 
                                       padx=15, pady=15, highlightthickness=2, highlightbackground=self.colors['header'])
        self.drop_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=8)
        self.drop_frame.columnconfigure(0, weight=1)
        self.drop_frame.columnconfigure(1, weight=1)
        self.drop_frame.rowconfigure(0, weight=1)

        self.drop_left_frame = tk.Frame(self.drop_frame, bg=self.colors['frame'], padx=10, pady=10, cursor='hand2')
        self.drop_left_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.drop_label = tk.Label(self.drop_left_frame, 
                                     text="🗂️\n\n点击此处选择目录\n进行智能分类\n\n或直接输入路径后按回车", 
                                     font=('Arial', 13), justify=tk.CENTER, bg=self.colors['frame'], fg=self.colors['fg'],
                                     cursor='hand2')
        self.drop_label.grid(row=0, column=0)

        self.drop_left_frame.bind('<Button-1>', self.on_drop_frame_click)
        self.drop_label.bind('<Button-1>', self.on_drop_frame_click)

        self.drop_right_frame = tk.Frame(self.drop_frame, bg=self.colors['frame'], padx=10, pady=10)
        self.drop_right_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.dir_stats_label = tk.Label(self.drop_right_frame, text="", font=('Arial', 11, 'bold'), 
                                       bg=self.colors['frame'], fg=self.colors['fg'])
        self.dir_stats_label.grid(row=0, column=0, pady=5)

        self.category_blocks_frame = tk.Frame(self.drop_right_frame, bg=self.colors['frame'])
        self.category_blocks_frame.grid(row=1, column=0)

        # 分类按钮区
        self.classify_frame = tk.Frame(self.master, bg=self.colors['bg'], padx=10, pady=8)
        self.classify_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=3)

        self.type_btn = ttk.Button(self.classify_frame, text="📷 按类型分类", 
                                   command=lambda: self.classify_files('type'),
                                   style='Green.TButton', width=14)
        self.type_btn.grid(row=0, column=0, padx=4, pady=4)

        self.time_btn = ttk.Button(self.classify_frame, text="📅 按时间分类", 
                                   command=lambda: self.classify_files('time'),
                                   style='Green.TButton', width=14)
        self.time_btn.grid(row=0, column=1, padx=4, pady=4)

        self.size_btn = ttk.Button(self.classify_frame, text="📦 按大小分类", 
                                   command=lambda: self.classify_files('size'),
                                   style='Green.TButton', width=14)
        self.size_btn.grid(row=0, column=2, padx=4, pady=4)

        self.ai_classify_btn = ttk.Button(self.classify_frame, text="🧠 AI内容分类", 
                                          command=self.classify_by_content,
                                          style='Green.TButton', width=14)
        self.ai_classify_btn.grid(row=0, column=3, padx=4, pady=4)

        self.undo_btn = ttk.Button(self.classify_frame, text="↩️ 撤销分类", 
                                   command=self.undo_classification,
                                   style='Blue.TButton', width=14)
        self.undo_btn.grid(row=0, column=4, padx=4, pady=4)

        self.undo_ai_btn = ttk.Button(self.classify_frame, text="↩️ 撤销AI分类", 
                                       command=self.undo_ai_classification,
                                       style='Blue.TButton', width=14)
        self.undo_ai_btn.grid(row=0, column=5, padx=4, pady=4)

        # 高级功能区
        self.advanced_frame = tk.Frame(self.master, bg=self.colors['bg'], padx=10, pady=8)
        self.advanced_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=3)

        self.duplicate_btn = ttk.Button(self.advanced_frame, text="🔍 检测重复文件", 
                                        command=self.detect_duplicates,
                                        style='Blue.TButton', width=14)
        self.duplicate_btn.grid(row=0, column=0, padx=4, pady=4)

        self.large_btn = ttk.Button(self.advanced_frame, text="📊 查找大文件", 
                                     command=self.find_large_files,
                                     style='Blue.TButton', width=14)
        self.large_btn.grid(row=0, column=1, padx=4, pady=4)

        self.stats_btn = ttk.Button(self.advanced_frame, text="📈 统计图表", 
                                     command=self.show_stats,
                                     style='Blue.TButton', width=14)
        self.stats_btn.grid(row=0, column=2, padx=4, pady=4)

        self.log_btn = ttk.Button(self.advanced_frame, text="📋 分类日志", 
                                   command=self.show_logs,
                                   style='Blue.TButton', width=14)
        self.log_btn.grid(row=0, column=3, padx=4, pady=4)

        self.custom_btn = ttk.Button(self.advanced_frame, text="⚙️ 自定义规则", 
                                     command=self.show_custom_rules,
                                     style='Blue.TButton', width=14)
        self.custom_btn.grid(row=0, column=4, padx=4, pady=4)

        self.recycle_btn = ttk.Button(self.advanced_frame, text="🗑️ 回收站", 
                                      command=self.show_recycle_bin,
                                      style='Orange.TButton', width=14)
        self.recycle_btn.grid(row=0, column=5, padx=4, pady=4)
        
        self.clean_btn = ttk.Button(self.advanced_frame, text="🗑️ 删除分类文件夹", 
                                      command=self.clean_category_folders,
                                      style='Orange.TButton', width=14)
        self.clean_btn.grid(row=0, column=6, padx=4, pady=4)

        # 结果区
        self.result_frame = tk.LabelFrame(self.master, text="📝 分类结果", bg=self.colors['bg'], 
                                         padx=10, pady=10, highlightthickness=2, highlightbackground=self.colors['header'])
        self.result_frame.grid(row=5, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=8)
        self.result_frame.columnconfigure(0, weight=1)
        self.result_frame.rowconfigure(0, weight=1)

        self.result_text = tk.Text(self.result_frame, wrap=tk.WORD, height=15, font=('Arial', 10), 
                                   bg='white', fg=self.colors['fg'])
        self.result_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.scrollbar = ttk.Scrollbar(self.result_frame, orient=tk.VERTICAL, command=self.result_text.yview)
        self.scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.result_text.configure(yscrollcommand=self.scrollbar.set)

        self.stats_canvas = tk.Canvas(self.result_frame, height=20, bg=self.colors['bg'])
        self.stats_canvas.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)

        # 状态栏
        self.status_bar = tk.Label(self.master, text="就绪", relief=tk.SUNKEN, 
                                   bg=self.colors['frame'], fg=self.colors['fg'])
        self.status_bar.grid(row=6, column=0, sticky=(tk.W, tk.E))

        # 深色模式按钮 - 放在标题栏
        self.dark_mode_btn = ttk.Button(self.header_frame, text="🌙 深色模式", 
                                         command=self.toggle_dark_mode,
                                         style='DarkMode.TButton')
        self.dark_mode_btn.grid(row=0, column=1, sticky=tk.E)

        self.tooltip = None
        self.validate_path()

    def toggle_dark_mode(self):
        self.dark_mode = not self.dark_mode
        if self.dark_mode:
            self.colors = self.dark_colors
            self.dark_mode_btn.config(text="☀️ 浅色模式")
        else:
            self.colors = self.light_colors
            self.dark_mode_btn.config(text="🌙 深色模式")
        self.apply_theme()

    def apply_theme(self):
        self.master.configure(bg=self.colors['bg'])
        
        self.header_frame.configure(bg=self.colors['header'])
        self.title_label.configure(bg=self.colors['header'], fg=self.colors['header_fg'])
        self.dark_mode_btn.configure(style='DarkMode.TButton')
        
        self.dir_frame.configure(bg=self.colors['bg'])
        self.dir_label.configure(bg=self.colors['bg'], fg=self.colors['fg'])
        self.filter_label.configure(bg=self.colors['bg'], fg=self.colors['fg'])
        self.filter_tip.configure(bg=self.colors['bg'], fg='gray')
        self.path_status.configure(bg=self.colors['bg'])
        
        self.drop_frame.configure(bg=self.colors['frame'], highlightbackground=self.colors['header'])
        self.drop_left_frame.configure(bg=self.colors['frame'])
        self.drop_right_frame.configure(bg=self.colors['frame'])
        self.drop_label.configure(bg=self.colors['frame'], fg=self.colors['fg'])
        self.dir_stats_label.configure(bg=self.colors['frame'], fg=self.colors['fg'])
        
        self.classify_frame.configure(bg=self.colors['bg'])
        self.advanced_frame.configure(bg=self.colors['bg'])
        
        self.result_frame.configure(bg=self.colors['bg'], highlightbackground=self.colors['header'])
        
        if self.dark_mode:
            self.result_text.configure(bg=self.colors['frame'], fg=self.colors['fg'])
        else:
            self.result_text.configure(bg='white', fg=self.colors['fg'])
        
        self.stats_canvas.configure(bg=self.colors['bg'])
        
        self.status_bar.configure(bg=self.colors['frame'], fg=self.colors['fg'])
        
        self.style.configure('Green.TButton', background=self.colors['green_btn'])
        self.style.configure('Blue.TButton', background=self.colors['blue_btn'])
        self.style.configure('Browse.TButton', background=self.colors['info'])

    def show_tooltip(self, event, text):
        self.tooltip = tk.Toplevel(self.master)
        self.tooltip.wm_overrideredirect(True)
        x = event.x_root + 10
        y = event.y_root + 10
        self.tooltip.wm_geometry(f"+{x}+{y}")

        label = tk.Label(self.tooltip, text=text, bg='#333', fg='white', 
                         padx=5, pady=5, font=('Arial', 10))
        label.pack()

    def hide_tooltip(self, event):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

    def browse_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.dir_entry.delete(0, tk.END)
            self.dir_entry.insert(0, directory)
            self.validate_path()

    def on_drop_frame_click(self, event):
        directory = filedialog.askdirectory()
        if directory:
            self.dir_entry.delete(0, tk.END)
            self.dir_entry.insert(0, directory)
            self.validate_path()
            self.classify_files('type')

    def validate_path(self, event=None):
        path = self.dir_entry.get()
        if os.path.isdir(path):
            self.path_status.config(text="✓ 目录存在", foreground=self.colors['success'])
            self.update_directory_stats(path)
        else:
            self.path_status.config(text="✗ 目录不存在", foreground=self.colors['error'])
            self.clear_directory_stats()

    def update_directory_stats(self, directory):
        stats = self.classifier.get_directory_stats(directory)

        for widget in self.category_blocks_frame.winfo_children():
            widget.destroy()

        if stats['total'] == 0:
            self.dir_stats_label.config(text=f"目录为空")
            return

        self.dir_stats_label.config(text=f"共 {stats['total']} 个文件")

        cat_colors = {
            "【01-图片】": "#f1c40f",
            "【02-文档】": "#9b59b6",
            "【03-视频】": "#3498db",
            "【04-音频】": "#e74c3c",
            "【05-压缩包】": "#1abc9c",
            "【06-程序安装包】": "#f39c12",
            "【其他未知格式】": "#7f8c8d"
        }

        row = 0
        col = 0
        max_cols = 4

        for category, info in stats['categories'].items():
            color = cat_colors.get(category, '#7f8c8d')
            block_frame = tk.Frame(self.category_blocks_frame, width=60, height=40, bg=self.colors['frame'])
            block_frame.grid(row=row, column=col, padx=5, pady=5)

            canvas = tk.Canvas(block_frame, width=50, height=30, bg=color)
            canvas.pack(pady=2)

            label = tk.Label(block_frame, text=f"{info['count']}", bg=self.colors['frame'], 
                             fg=self.colors['fg'], font=('Arial', 9))
            label.pack()

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

    def clear_directory_stats(self):
        self.dir_stats_label.config(text="")
        for widget in self.category_blocks_frame.winfo_children():
            widget.destroy()

    def classify_files(self, mode):
        source_dir = self.dir_entry.get()
        filter_keyword = self.filter_entry.get().strip()

        if not os.path.isdir(source_dir):
            messagebox.showerror("错误", "请选择有效的目录")
            return

        try:
            os.listdir(source_dir)
        except PermissionError:
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, f"❌ 权限不足：无法访问目录")
            self.status_bar.config(text="权限不足")
            messagebox.showerror("权限错误", "无法访问目录，请检查权限")
            return

        self.current_dir = source_dir
        self.result_text.delete(1.0, tk.END)
        self.status_bar.config(text="正在分类...")
        self.master.update_idletasks()

        try:
            if mode == 'type':
                results = self.classifier.classify_by_type(source_dir, filter_keyword=filter_keyword)
                classification_type = '按类型分类'
            elif mode == 'time':
                results = self.classifier.classify_by_time(source_dir, filter_keyword=filter_keyword)
                classification_type = '按时间分类'
            elif mode == 'size':
                results = self.classifier.classify_by_size(source_dir, filter_keyword=filter_keyword)
                classification_type = '按大小分类'

            self.last_results = results
            self.logger.log_classification(results, source_dir, classification_type)
            self.stats_manager.save_stats(self.classifier.get_stats(), classification_type)

            stats = self.classifier.get_stats()

            self.result_text.insert(tk.END, f"📂 分类目录: {source_dir}\n", 'header')
            if filter_keyword:
                self.result_text.insert(tk.END, f"🔎 筛选关键词: '{filter_keyword}'\n", 'header')
            self.result_text.insert(tk.END, f"📅 分类时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n", 'header')
            self.result_text.insert(tk.END, "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n", 'header')
            self.result_text.insert(tk.END, "📊 分类统计:\n", 'header')

            for category, count in stats.items():
                if count > 0:
                    if category in ['跳过']:
                        self.result_text.insert(tk.END, f"  {category}: ", 'warning')
                        self.result_text.insert(tk.END, f"{count} 个文件\n", 'warning')
                    elif category in ['失败']:
                        self.result_text.insert(tk.END, f"  {category}: ", 'error')
                        self.result_text.insert(tk.END, f"{count} 个文件\n", 'error')
                    else:
                        self.result_text.insert(tk.END, f"  {category}: ", 'success')
                        self.result_text.insert(tk.END, f"{count} 个文件\n", 'success')

            self.result_text.insert(tk.END, "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n", 'header')
            self.result_text.insert(tk.END, f"✅ 成功分类 {len(results)} 个文件\n", 'success')

            if stats.get('跳过', 0) > 0:
                self.result_text.insert(tk.END, f"⏭️ 跳过 {stats.get('跳过', 0)} 个文件\n", 'warning')

            self.result_text.tag_config('header', font=('Arial', 10, 'bold'))
            self.result_text.tag_config('success', foreground=self.colors['success'])
            self.result_text.tag_config('warning', foreground=self.colors['warning'])
            self.result_text.tag_config('error', foreground=self.colors['error'])

            self.status_bar.config(text="分类完成")
            
            # 显示详细日志
            self.result_text.insert(tk.END, "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n", 'header')
            self.result_text.insert(tk.END, "📋 详细日志:\n", 'header')
            
            if hasattr(self.classifier, '_debug_info'):
                for info in self.classifier._debug_info:
                    if "跳过" in info or "排除" in info:
                        self.result_text.insert(tk.END, f"⏭️ {info}\n", 'warning')
                    elif "失败" in info:
                        self.result_text.insert(tk.END, f"❌ {info}\n", 'error')
                    else:
                        self.result_text.insert(tk.END, f"✓ {info}\n", 'success')
            
            messagebox.showinfo("成功", f"已成功分类 {len(results)} 个文件！")

        except Exception as e:
            self.result_text.insert(tk.END, f"❌ 分类失败: {str(e)}", 'error')
            self.status_bar.config(text="分类失败")
            messagebox.showerror("错误", f"分类失败: {str(e)}")

    def undo_classification(self):
        success, message = self.classifier.undo_last_classification()
        if success:
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, f"↩️ {message}", 'success')
            self.status_bar.config(text="已撤销")
            self.validate_path()
            messagebox.showinfo("成功", message)
        else:
            messagebox.showwarning("提示", message)
    
    def undo_ai_classification(self):
        """撤销AI分类操作"""
        success, message = self.classifier.undo_ai_classification()
        if success:
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, f"↩️ {message}", 'success')
            self.result_text.tag_config('success', foreground=self.colors['success'])
            self.status_bar.config(text="已撤销AI分类")
            self.validate_path()
            messagebox.showinfo("成功", message)
        else:
            messagebox.showwarning("提示", message)

    def detect_duplicates(self):
        source_dir = self.dir_entry.get()
        if not os.path.isdir(source_dir):
            messagebox.showerror("错误", "请选择有效的目录")
            return

        self.result_text.delete(1.0, tk.END)
        self.status_bar.config(text="正在检测重复文件...")
        self.master.update_idletasks()

        try:
            self.duplicates = self.detector.detect_duplicates(source_dir)

            if not self.duplicates:
                self.result_text.insert(tk.END, "🎉 未发现重复文件", 'success')
                self.status_bar.config(text="检测完成")
                messagebox.showinfo("结果", "未发现重复文件")
                return

            duplicate_window = tk.Toplevel(self.master)
            duplicate_window.title("重复文件检测结果")
            duplicate_window.geometry("850x650")

            frame = ttk.Frame(duplicate_window, padding="10")
            frame.pack(fill=tk.BOTH, expand=True)

            listbox = tk.Listbox(frame, width=100, height=20, font=('Arial', 10))
            listbox.pack(fill=tk.BOTH, expand=True, pady=5)

            for i, group in enumerate(self.duplicates, 1):
                listbox.insert(tk.END, f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                listbox.insert(tk.END, f"📦 重复组 {i} ({len(group)} 个文件)")
                for path in group:
                    size = self.detector.format_size(os.path.getsize(path))
                    listbox.insert(tk.END, f"   [{size}] {path}")
                listbox.insert(tk.END, "")

            btn_frame = ttk.Frame(frame)
            btn_frame.pack(fill=tk.X, pady=10)

            recycle_btn = ttk.Button(btn_frame, text="🗑️ 移入回收站", 
                                     command=lambda: self.move_duplicates_to_recycle(duplicate_window, source_dir))
            recycle_btn.pack(side=tk.LEFT, padx=5)

            delete_btn = ttk.Button(btn_frame, text="💀 永久删除", 
                                   command=lambda: self.delete_selected_duplicates(duplicate_window))
            delete_btn.pack(side=tk.LEFT, padx=5)

            backup_btn = ttk.Button(btn_frame, text="📁 移动至备份", 
                                   command=lambda: self.move_to_backup(duplicate_window))
            backup_btn.pack(side=tk.LEFT, padx=5)

            cancel_btn = ttk.Button(btn_frame, text="❌ 取消", 
                                   command=duplicate_window.destroy)
            cancel_btn.pack(side=tk.RIGHT, padx=5)

            self.status_bar.config(text="检测完成")

        except Exception as e:
            self.result_text.insert(tk.END, f"❌ 检测失败: {str(e)}", 'error')
            self.status_bar.config(text="检测失败")

    def delete_selected_duplicates(self, window):
        deleted_count, deleted_files = self.detector.delete_duplicates(self.duplicates)
        messagebox.showinfo("完成", f"已删除 {deleted_count} 个重复文件")
        window.destroy()
        self.validate_path()

    def move_duplicates_to_recycle(self, window, source_dir):
        moved_count = 0
        for group in self.duplicates:
            for path in group[1:]:
                success, _ = self.detector.move_to_recycle_bin(path, source_dir)
                if success:
                    moved_count += 1
        messagebox.showinfo("完成", f"已将 {moved_count} 个文件移入回收站")
        window.destroy()
        self.validate_path()

    def move_to_backup(self, window):
        backup_dir = os.path.join(self.dir_entry.get(), "_重复文件备份")
        os.makedirs(backup_dir, exist_ok=True)
        moved_count = 0
        for group in self.duplicates:
            for path in group[1:]:
                try:
                    shutil.move(path, os.path.join(backup_dir, os.path.basename(path)))
                    moved_count += 1
                except:
                    pass
        messagebox.showinfo("完成", f"已移动 {moved_count} 个重复文件至备份目录")
        window.destroy()
        self.validate_path()

    def show_recycle_bin(self):
        source_dir = self.dir_entry.get()
        if not os.path.isdir(source_dir):
            messagebox.showerror("错误", "请选择有效的目录")
            return

        recycle_items = self.detector.get_recycle_items(source_dir)

        recycle_window = tk.Toplevel(self.master)
        recycle_window.title("回收站")
        recycle_window.geometry("900x600")

        frame = ttk.Frame(recycle_window, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)

        header = ttk.Label(frame, text=f"📦 回收站 - {os.path.basename(source_dir)}", font=('Arial', 12, 'bold'))
        header.pack(pady=5)

        if not recycle_items:
            ttk.Label(frame, text="回收站为空", font=('Arial', 11)).pack(pady=20)
            ttk.Button(frame, text="关闭", command=recycle_window.destroy).pack(pady=10)
            return

        list_frame = ttk.Frame(frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        listbox = tk.Listbox(list_frame, width=120, height=20, font=('Arial', 9), yscrollcommand=scrollbar.set)
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=listbox.yview)

        for item in recycle_items:
            timestamp = item.get('timestamp', '')[:19]
            filename = item.get('filename', '')
            listbox.insert(tk.END, f"📄 {filename}")
            listbox.insert(tk.END, f"   时间: {timestamp}")
            listbox.insert(tk.END, "")

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=10)

        def restore_selected():
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("提示", "请选择要还原的文件")
                return
            item_indices = set(idx // 3 for idx in selection)
            restored_count = 0
            for item_idx in sorted(item_indices, reverse=True):
                if item_idx < len(recycle_items):
                    success, _ = self.detector.restore_from_recycle_bin(recycle_items[item_idx])
                    if success:
                        restored_count += 1
            messagebox.showinfo("完成", f"已还原 {restored_count} 个文件")
            recycle_window.destroy()
            self.validate_path()

        restore_btn = ttk.Button(btn_frame, text="↩️ 还原选中", command=restore_selected)
        restore_btn.pack(side=tk.LEFT, padx=5)

        delete_btn = ttk.Button(btn_frame, text="💀 永久删除选中", 
                               command=lambda: [self.detector.permanently_delete(recycle_items[idx//3]) for idx in listbox.curselection()] or messagebox.showinfo("完成", "已删除") or recycle_window.destroy())
        delete_btn.pack(side=tk.LEFT, padx=5)

        close_btn = ttk.Button(btn_frame, text="❌ 关闭", command=recycle_window.destroy)
        close_btn.pack(side=tk.RIGHT, padx=5)

    def find_large_files(self):
        source_dir = self.dir_entry.get()
        if not os.path.isdir(source_dir):
            messagebox.showerror("错误", "请选择有效的目录")
            return

        self.result_text.delete(1.0, tk.END)
        self.status_bar.config(text="正在查找大文件...")
        self.master.update_idletasks()

        try:
            self.large_files = self.detector.find_large_files(source_dir)

            if not self.large_files:
                self.result_text.insert(tk.END, "🎉 未发现大于100MB的文件", 'success')
                self.status_bar.config(text="查找完成")
                messagebox.showinfo("结果", "未发现大于100MB的文件")
                return

            large_window = tk.Toplevel(self.master)
            large_window.title("大文件列表")
            large_window.geometry("800x600")

            frame = ttk.Frame(large_window, padding="10")
            frame.pack(fill=tk.BOTH, expand=True)

            total_size = sum(f['size'] for f in self.large_files)
            label = ttk.Label(frame, text=f"📊 发现 {len(self.large_files)} 个大文件（总计: {self.detector.format_size(total_size)}）",
                             font=('Arial', 12, 'bold'))
            label.pack(pady=5)

            for file_info in self.large_files:
                file_frame = ttk.Frame(frame, padding="5")
                file_frame.pack(fill=tk.X, pady=2)
                ttk.Label(file_frame, text=os.path.basename(file_info['path']), font=('Arial', 10), width=40).pack(side=tk.LEFT)
                ttk.Label(file_frame, text=file_info['size_readable'], font=('Arial', 10), width=20).pack(side=tk.RIGHT)

            self.status_bar.config(text="查找完成")

        except Exception as e:
            self.result_text.insert(tk.END, f"❌ 查找失败: {str(e)}", 'error')
            self.status_bar.config(text="查找失败")

    def show_stats(self):
        latest_stats = self.stats_manager.get_latest_stats()
        if not latest_stats:
            messagebox.showinfo("提示", "暂无统计数据")
            return

        stats = latest_stats.get('stats', {})
        classification_type = latest_stats.get('classification_type', '')

        labels = []
        sizes = []
        colors = ['#f1c40f', '#9b59b6', '#3498db', '#e74c3c', '#1abc9c', '#f39c12', '#7f8c8d']

        for category, count in stats.items():
            if count > 0 and category not in ['跳过', '重复文件']:
                labels.append(category)
                sizes.append(count)

        if not labels:
            messagebox.showinfo("提示", "没有可显示的数据")
            return

        set_chinese_font()

        stats_window = tk.Toplevel(self.master)
        stats_window.title("分类统计图表")
        stats_window.geometry("900x500")

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4), dpi=100)

        ax1.pie(sizes, labels=labels, colors=colors[:len(labels)], autopct='%1.1f%%', startangle=90, textprops={'fontsize': 8})
        ax1.axis('equal')
        ax1.set_title(f'{classification_type} - 文件数量分布')

        ax2.bar(labels, sizes, color=colors[:len(labels)])
        ax2.set_title(f'{classification_type} - 文件数量统计')
        ax2.tick_params(axis='x', rotation=45, labelsize=8)

        canvas = FigureCanvasTkAgg(fig, master=stats_window)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        plt.close(fig)

    def show_logs(self):
        logs = self.logger.get_logs()
        if not logs:
            messagebox.showinfo("提示", "暂无分类日志")
            return

        log_window = tk.Toplevel(self.master)
        log_window.title("分类日志")
        log_window.geometry("800x600")

        log_text = tk.Text(log_window, wrap=tk.WORD, font=('Arial', 10))
        log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        scrollbar = ttk.Scrollbar(log_window, orient=tk.VERTICAL, command=log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        log_text.configure(yscrollcommand=scrollbar.set)

        for i, log in enumerate(reversed(logs), 1):
            log_str = f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            log_str += f"📝 记录 {i}\n"
            log_str += f"📅 时间: {log['timestamp'][:19]}\n"
            log_str += f"📂 目录: {log['source_dir']}\n"
            log_str += f"🔄 类型: {log['classification_type']}\n"
            log_str += f"📊 文件数: {log['files_processed']}\n\n"
            log_text.insert(tk.END, log_str)

    def show_custom_rules(self):
        custom_window = tk.Toplevel(self.master)
        custom_window.title("自定义分类规则")
        custom_window.geometry("700x550")

        frame = ttk.Frame(custom_window, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="添加新的文件类型规则", font=('Arial', 12, 'bold')).pack(pady=5)

        ext_frame = ttk.Frame(frame)
        ext_frame.pack(fill=tk.X, pady=5)
        ttk.Label(ext_frame, text="扩展名:").pack(side=tk.LEFT)
        ext_entry = ttk.Entry(ext_frame, width=15)
        ext_entry.pack(side=tk.LEFT, padx=5)
        ext_entry.insert(0, ".xxx")

        name_frame = ttk.Frame(frame)
        name_frame.pack(fill=tk.X, pady=5)
        ttk.Label(name_frame, text="分类名称:").pack(side=tk.LEFT)
        name_entry = ttk.Entry(name_frame, width=30)
        name_entry.pack(side=tk.LEFT, padx=5)
        name_entry.insert(0, "自定义分类")

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=5)
        add_btn = ttk.Button(btn_frame, text="➕ 添加规则", 
                             command=lambda: self.add_custom_rule(ext_entry.get(), name_entry.get()))
        add_btn.pack(side=tk.LEFT, padx=5)

        io_frame = ttk.Frame(frame)
        io_frame.pack(fill=tk.X, pady=5)
        import_btn = ttk.Button(io_frame, text="📥 从TXT批量导入", 
                               command=lambda: self.import_rules_from_txt())
        import_btn.pack(side=tk.LEFT, padx=5)
        export_btn = ttk.Button(io_frame, text="📤 导出规则为TXT", 
                               command=lambda: self.export_rules_to_txt())
        export_btn.pack(side=tk.LEFT, padx=5)

        ttk.Label(frame, text="当前规则（双击扩展名可删除）:", font=('Arial', 11, 'bold')).pack(pady=5)

        # 使用列表框显示规则
        rules_listbox = tk.Listbox(frame, height=18, width=70, font=('Arial', 9))
        rules_listbox.pack(fill=tk.BOTH, expand=True)
        
        # 存储规则数据
        self.rules_data = []
        for category, exts in self.classifier.file_types.items():
            for ext in exts:
                self.rules_data.append((category, ext))
                rules_listbox.insert(tk.END, f"{category} → {ext}")
        
        # 双击删除扩展名
        def on_double_click(event):
            selection = rules_listbox.curselection()
            if selection:
                index = selection[0]
                category, ext = self.rules_data[index]
                if messagebox.askyesno("确认删除", f"确定要删除规则「{category} → {ext}」吗？"):
                    self.delete_extension(category, ext)
                    # 更新列表
                    rules_listbox.delete(index)
                    del self.rules_data[index]
        
        rules_listbox.bind('<Double-1>', on_double_click)

    def add_custom_rule(self, ext, name):
        if not ext.startswith('.'):
            ext = '.' + ext

        if not name:
            messagebox.showwarning("提示", "请输入分类名称")
            return

        config_path = 'config/file_types.json'
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            if name not in config:
                config[name] = []

            if ext not in config[name]:
                config[name].append(ext)
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
                self.classifier.file_types = config
                messagebox.showinfo("成功", f"已添加规则: {ext} → {name}")
            else:
                messagebox.showwarning("提示", "该扩展名已存在于该分类中")
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {str(e)}")

    def delete_extension(self, category_name, ext):
        """从分类中删除单个扩展名"""
        if not category_name:
            messagebox.showwarning("提示", "请输入分类名称")
            return
        
        if not ext:
            messagebox.showwarning("提示", "请输入要删除的扩展名")
            return
        
        if not ext.startswith('.'):
            ext = '.' + ext

        config_path = 'config/file_types.json'
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            if category_name in config:
                if ext in config[category_name]:
                    config[category_name].remove(ext)
                    # 如果分类下没有扩展名了，删除该分类
                    if not config[category_name]:
                        del config[category_name]
                    with open(config_path, 'w', encoding='utf-8') as f:
                        json.dump(config, f, ensure_ascii=False, indent=2)
                    self.classifier.file_types = config
                    messagebox.showinfo("成功", f"已从「{category_name}」中删除扩展名: {ext}")
                else:
                    messagebox.showwarning("提示", f"「{category_name}」中未找到扩展名: {ext}")
            else:
                messagebox.showwarning("提示", f"未找到分类: {category_name}")
        except Exception as e:
            messagebox.showerror("错误", f"删除失败: {str(e)}")

    def import_rules_from_txt(self):
        format_info = """📋 TXT文件格式说明：

示例：
图片文件:
  .png .jpg .jpeg
文档文件:
  .doc, .docx, .pdf
音频文件:
  .mp3 .wav

注意：分类名称后加英文冒号":"，扩展名用逗号或空格分隔"""

        if not messagebox.askyesno("导入格式说明", f"{format_info}\n\n是否继续？"):
            return

        file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if not file_path:
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            config = {}
            current_category = None
            for line in content.split('\n'):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if line.endswith(':'):
                    current_category = line[:-1].strip()
                    config[current_category] = []
                elif current_category:
                    exts = [p.strip() for p in line.replace(',', ' ').split()]
                    for ext in exts:
                        if ext:
                            if not ext.startswith('.'):
                                ext = '.' + ext
                            config[current_category].append(ext.lower())

            if not config:
                messagebox.showwarning("提示", "未找到有效的规则")
                return

            with open('config/file_types.json', 'r', encoding='utf-8') as f:
                existing_config = json.load(f)

            imported_count = 0
            for category, exts in config.items():
                if category not in existing_config:
                    existing_config[category] = []
                for ext in exts:
                    if ext not in existing_config[category]:
                        existing_config[category].append(ext)
                        imported_count += 1

            with open('config/file_types.json', 'w', encoding='utf-8') as f:
                json.dump(existing_config, f, ensure_ascii=False, indent=2)

            self.classifier.file_types = existing_config
            messagebox.showinfo("成功", f"已导入 {imported_count} 条新规则")
        except Exception as e:
            messagebox.showerror("错误", f"导入失败: {str(e)}")

    def export_rules_to_txt(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if not file_path:
            return

        try:
            content = []
            for category, exts in self.classifier.file_types.items():
                content.append(f"{category}:")
                content.append(f"  {', '.join(exts)}")
                content.append("")

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(content))

            messagebox.showinfo("成功", f"规则已导出至:\n{file_path}")
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {str(e)}")

    def clean_category_folders(self):
        """删除当前目录下的分类文件夹（支持多选删除）"""
        source_dir = self.dir_entry.get()
        
        if not os.path.isdir(source_dir):
            messagebox.showerror("错误", "请先选择有效的目录")
            return
        
        # 获取所有分类文件夹名称
        category_folders = []
        for item in os.listdir(source_dir):
            item_path = os.path.join(source_dir, item)
            if os.path.isdir(item_path):
                # 判断是否为分类文件夹
                if item.startswith("【") and item.endswith("】"):
                    category_folders.append(item)
                elif item in ["小文件_1MB以下", "中文件_1M-100M", "大文件_100MB以上"]:
                    category_folders.append(item)
                elif item in ["今天", "昨天", "本周", "本月", "上月文件", "更早归档"]:
                    category_folders.append(item)
        
        if not category_folders:
            messagebox.showinfo("提示", "未找到分类文件夹")
            return
        
        # 创建选择窗口
        clean_window = tk.Toplevel(self.master)
        clean_window.title("删除分类文件夹")
        clean_window.geometry("500x400")
        
        frame = ttk.Frame(clean_window, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="选择要删除的分类文件夹:", font=('Arial', 11, 'bold')).pack(pady=5)
        
        # 列表框
        listbox = tk.Listbox(frame, selectmode=tk.MULTIPLE, height=12, font=('Arial', 10))
        listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        
        for folder in category_folders:
            listbox.insert(tk.END, folder)
        
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        # 选中删除按钮
        delete_selected_btn = ttk.Button(btn_frame, text="🗑️ 删除选中", 
                                         command=lambda: self.delete_selected_folders(source_dir, listbox, clean_window),
                                         width=12)
        delete_selected_btn.pack(side=tk.LEFT, padx=3)
        
        # 全选按钮
        select_all_btn = ttk.Button(btn_frame, text="全选", 
                                    command=lambda: listbox.select_set(0, tk.END),
                                    width=8)
        select_all_btn.pack(side=tk.LEFT, padx=3)
        
        # 一键删除所有按钮
        delete_all_btn = ttk.Button(btn_frame, text="🔥 一键删除全部", 
                                    command=lambda: self.delete_all_folders(source_dir, listbox, clean_window),
                                    style='Orange.TButton',
                                    width=12)
        delete_all_btn.pack(side=tk.RIGHT, padx=3)
        
        cancel_btn = ttk.Button(btn_frame, text="取消", 
                                command=clean_window.destroy,
                                width=8)
        cancel_btn.pack(side=tk.RIGHT, padx=3)
    
    def delete_selected_folders(self, source_dir, listbox, window):
        """删除选中的分类文件夹"""
        selected_indices = listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("提示", "请先选择要删除的文件夹")
            return
        
        selected_folders = [listbox.get(i) for i in selected_indices]
        folder_list = "\n".join(f"  - {f}" for f in selected_folders)
        
        if not messagebox.askyesno("确认删除", f"确定要删除以下分类文件夹吗？\n\n{folder_list}\n\n⚠️ 文件夹内的文件将被移动到上级目录！"):
            return
        
        self._delete_folders(source_dir, selected_folders)
        window.destroy()
    
    def delete_all_folders(self, source_dir, listbox, window):
        """删除所有分类文件夹"""
        all_folders = [listbox.get(i) for i in range(listbox.size())]
        folder_list = "\n".join(f"  - {f}" for f in all_folders)
        
        if not messagebox.askyesno("确认删除全部", f"确定要删除所有分类文件夹吗？\n\n{folder_list}\n\n⚠️ 所有文件将被移动到上级目录！"):
            return
        
        self._delete_folders(source_dir, all_folders)
        window.destroy()
    
    def _delete_folders(self, source_dir, folders):
        """执行删除文件夹操作"""
        moved_count = 0
        deleted_count = 0
        
        try:
            for folder_name in folders:
                folder_path = os.path.join(source_dir, folder_name)
                
                # 将文件夹内的文件移到上级目录
                for item in os.listdir(folder_path):
                    item_path = os.path.join(folder_path, item)
                    if os.path.isfile(item_path):
                        dest_path = os.path.join(source_dir, item)
                        counter = 1
                        while os.path.exists(dest_path):
                            base, ext = os.path.splitext(item)
                            dest_path = os.path.join(source_dir, f"{base}_{counter}{ext}")
                            counter += 1
                        shutil.move(item_path, dest_path)
                        moved_count += 1
                
                # 删除空文件夹
                os.rmdir(folder_path)
                deleted_count += 1
            
            messagebox.showinfo("成功", f"已删除 {deleted_count} 个分类文件夹，{moved_count} 个文件已移回原目录")
            self.validate_path()
        except Exception as e:
            messagebox.showerror("错误", f"操作失败: {str(e)}")

    def classify_by_content(self):
        """AI内容分类 - 根据文档正文内容进行智能分类"""
        source_dir = self.dir_entry.get()
        
        if not os.path.isdir(source_dir):
            messagebox.showerror("错误", "请选择有效的目录")
            return
        
        if not self.content_classifier or not self.content_classifier.is_available():
            messagebox.showwarning("提示", "AI内容分类模块不可用，请安装依赖：\n\npip install jieba pdfplumber python-docx")
            return
        
        self.result_text.delete(1.0, tk.END)
        self.status_bar.config(text="正在进行AI内容分析...")
        self.master.update_idletasks()
        
        try:
            results = self.content_classifier.batch_classify(source_dir)
            
            if not results:
                self.result_text.insert(tk.END, "未找到可分析的文档（支持TXT/PDF/DOCX格式）", 'warning')
                self.status_bar.config(text="分析完成")
                messagebox.showinfo("结果", "未找到可分析的文档")
                return
            
            # 按分类整理结果
            categorized = {}
            for item in results:
                category = item['category']
                if category not in categorized:
                    categorized[category] = []
                categorized[category].append(item)
            
            # 显示结果
            self.result_text.insert(tk.END, f"📂 分析目录: {source_dir}\n", 'header')
            self.result_text.insert(tk.END, f"📅 分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n", 'header')
            self.result_text.insert(tk.END, "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n", 'header')
            self.result_text.insert(tk.END, "🧠 AI内容分类结果:\n", 'header')
            
            total_files = 0
            for category, items in categorized.items():
                self.result_text.insert(tk.END, f"\n📁 {category} ({len(items)}个文件):\n", 'success')
                for item in items:
                    self.result_text.insert(tk.END, f"   ✓ {item['filename']}\n", 'info')
                total_files += len(items)
            
            self.result_text.insert(tk.END, "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n", 'header')
            self.result_text.insert(tk.END, f"✅ 共分析 {total_files} 个文档\n", 'success')
            
            self.result_text.tag_config('header', font=('Arial', 10, 'bold'))
            self.result_text.tag_config('success', foreground=self.colors['success'])
            self.result_text.tag_config('warning', foreground=self.colors['warning'])
            self.result_text.tag_config('info', foreground=self.colors['info'])
            
            self.status_bar.config(text="AI分析完成")
            
            # 询问是否执行分类
            if messagebox.askyesno("确认", f"AI已分析 {total_files} 个文档，是否按内容分类移动文件？"):
                self.execute_content_classification(categorized, source_dir)
            
        except Exception as e:
            self.result_text.insert(tk.END, f"❌ AI分析失败: {str(e)}", 'error')
            self.status_bar.config(text="分析失败")
            messagebox.showerror("错误", f"AI分析失败: {str(e)}")
    
    def execute_content_classification(self, categorized, source_dir):
        """执行AI内容分类的文件移动"""
        # 先记录AI分类操作以便撤销
        self.classifier.record_ai_classification(categorized, source_dir)
        
        moved_count = 0
        failed_count = 0
        
        for category, items in categorized.items():
            # 创建分类文件夹（去掉【AI分类】或【AI语义】前缀）
            folder_name = category.replace("【AI分类】", "").replace("【AI语义】", "")
            folder_path = os.path.join(source_dir, folder_name)
            os.makedirs(folder_path, exist_ok=True)
            
            for item in items:
                try:
                    src_path = item['path']
                    dst_path = os.path.join(folder_path, item['filename'])
                    
                    if src_path != dst_path:
                        shutil.move(src_path, dst_path)
                        moved_count += 1
                except Exception as e:
                    failed_count += 1
                    print(f"移动失败 {item['filename']}: {e}")
        
        result_msg = f"✅ 成功分类 {moved_count} 个文件"
        if failed_count > 0:
            result_msg += f"\n❌ 失败 {failed_count} 个文件"
        
        messagebox.showinfo("完成", result_msg)
        self.validate_path()