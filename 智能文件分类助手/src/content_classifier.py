import os
import re
import json
import sys
from collections import Counter
from datetime import datetime

# 添加用户Python库路径（兼容Windows本地Python环境）
user_site_packages = os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', 'Python', 'Python312', 'site-packages')
if user_site_packages not in sys.path:
    sys.path.insert(0, user_site_packages)

# 导入 jieba 中文分词库（AI核心），如果失败则标记为不可用
try:
    import jieba
    import jieba.analyse
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False
    print("警告：未安装 jieba 库，AI内容分类功能将不可用")

# 导入pdfplumber（PDF解析）
try:
    from pdfplumber import open as open_pdf
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    print("警告：未安装 pdfplumber 库，PDF文件分析功能将不可用")

# 导入python-docx（Word解析）
try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    print("警告：未安装 python-docx 库，DOCX文件分析功能将不可用")

# 主类
class ContentClassifier:
    def __init__(self):
        # 定义分类规则：关键词列表 -> 分类名称
        # 核心规则字典：字典+列表嵌套
        self.category_rules = {
            # ============ 文档资料类 ============
            "财务票据": ["发票", "税号", "报销", "金额", "开票", "付款", "收款", "收据", 
                        "发票号", "纳税人", "税率", "税额", "价税", "合计", "结算",
                        "增值税", "抵扣", "凭证", "账目", "对账单", "银行流水", "汇款"],
            "合同协议": ["合同", "协议", "甲方", "乙方", "丙方", "承租方", "出租方",
                        "甲方乙方", "签订日期", "有效期", "违约责任", "权利义务", "条款",
                        "委托书", "授权书", "承诺函", "意向书", "谅解备忘录", "补充协议"],
            "法律文书": ["起诉状", "判决书", "裁定书", "调解书", "律师", "法院", "诉讼",
                        "仲裁", "证据", "辩护", "原告", "被告", "证人", "裁定", "裁决",
                        "传票", "通知书", "公告", "行政复议", "法律援助", "委托代理"],
            "人事资料": ["简历", "入职", "离职", "薪资", "考勤", "绩效", "社保",
                        "劳动合同", "试用期", "转正", "年终奖", "福利", "招聘", "岗位",
                        "培训", "考核", "晋升", "调薪", "离职证明", "工作证明"],
            "财务报表": ["资产负债表", "利润表", "现金流量表", "所有者权益", "营业收入",
                        "营业成本", "净利润", "毛利润", "费用", "预算", "决算", "审计",
                        "财务分析", "盈利", "亏损", "负债", "资产", "折旧", "摊销"],
            
            # ============ 技术开发类 ============
            "技术文档": ["代码", "编程", "开发", "API", "接口", "架构", "数据库",
                        "算法", "框架", "调试", "部署", "服务器", "前端", "后端",
                        "文档", "SDK", "SDK文档", "开发指南", "技术方案", "设计文档",
                        "接口文档", "数据库设计", "ER图", "流程图", "架构图"],
            "项目文档": ["需求", "需求文档", "PRD", "产品需求", "BRD", "MRD",
                        "原型", "UI设计", "UE设计", "交互设计", "PRD文档",
                        "项目计划", "里程碑", "进度报告", "周报", "日报", "月报"],
            "运维文档": ["部署", "安装", "配置", "运维", "监控", "日志", "备份",
                        "恢复", "迁移", "升级", "维护", "故障", "排查", "巡检",
                        "安全", "权限", "用户管理", "系统配置"],
            
            # ============ 学习教育类 ============
            "学术论文": ["摘要", "关键词", "参考文献", "引言", "结论", "实验",
                        "研究", "论文", "期刊", "发表", "引用", "DOI", "基金",
                        "学位", "学士", "硕士", "博士", "答辩", "开题", "综述",
                        "文献综述", "研究方法", "数据分析", "结论与展望"],
            "考试资料": ["真题", "模拟题", "试卷", "答案", "解析", "考点",
                        "考研", "高考", "公务员", "资格证", "题库", "考纲", "大纲",
                        "历年真题", "模拟卷", "押题", "冲刺", "备考", "复习资料"],
            "教材课件": ["教材", "课本", "教程", "课件", "PPT", "幻灯片", "讲义",
                        "教学", "课程", "章节", "习题", "练习", "答案解析",
                        "教学大纲", "教学计划", "教案", "教学设计"],
            "笔记资料": ["笔记", "学习笔记", "读书笔记", "摘录", "摘抄", "要点",
                        "总结", "归纳", "整理", "知识点", "考点", "重点", "难点"],
            
            # ============ 办公商务类 ============
            "会议纪要": ["会议", "纪要", "议题", "决议", "参会", "主持",
                        "议程", "记录", "讨论", "决定", "行动项", "待办事项",
                        "会议纪要", "会议记录", "决议事项", "落实情况"],
            "报告总结": ["报告", "总结", "汇报", "述职", "计划", "复盘",
                        "分析", "数据", "指标", "进度", "完成率", "工作总结",
                        "年度总结", "季度总结", "月度总结", "述职报告"],
            "工作文档": ["工作", "办公", "通知", "函", "请示", "批复", "决定",
                        "公告", "启事", "说明", "备忘录", "便签", "事务",
                        "行政", "公文", "红头文件", "红头"],
            
            # ============ 商务营销类 ============
            "营销资料": ["营销", "推广", "策划", "方案", "市场", "客户", "销售",
                        "推广方案", "营销策划", "市场分析", "竞品分析", "SWOT",
                        "营销计划", "推广计划", "销售策略", "客户画像", "渠道"],
            "商务报价": ["报价", "报价单", "价格", "报价表", "预算", "方案报价",
                        "价格表", "价目表", "收费标准", "合同金额", "付款方式",
                        "报价方案", "工程报价", "项目报价", "产品报价"],
            
            # ============ 设计创意类 ============
            "设计方案": ["设计", "方案", "创意", "灵感", "风格", "配色", "版式",
                        "设计稿", "设计图", "效果图", "草图", "线框图", "原型图",
                        "设计说明", "设计理念", "设计思路", "设计规范"],
            "图片素材": ["图片", "素材", "图标", "插画", "海报", "宣传图", "banner",
                        "封面", "背景图", "配图", "图库", "摄影", "图片素材"],
            
            # ============ 音视频类 ============
            "音频资料": ["音频", "音乐", "MP3", "WAV", "FLAC", "音频文件",
                        "歌曲", "配乐", "背景音乐", "音效", "语音", "录音"],
            "视频资料": ["视频", "MP4", "AVI", "MOV", "视频文件", "影片", "电影",
                        "纪录片", "教程视频", "宣传片", "短视频", "直播回放"],
            
            # ============ 数据表格类 ============
            "数据表格": ["表格", "数据", "Excel", "CSV", "数据表", "统计表",
                        "清单", "明细", "台账", "登记表", "汇总表", "对比表",
                        "数据导出", "数据统计", "数据分析", "数据报告"],
            
            # ============ 压缩安装类 ============
            "压缩文件": ["压缩", "ZIP", "RAR", "7Z", "压缩包", "打包", "解压"],
            "安装程序": ["安装", "安装包", "setup", "install", "installer", "exe", "msi"],
            
            # ============ 其他常用类 ============
            "邮件存档": ["邮件", "Email", "收发件", "主题", "正文", "附件", "收件箱",
                        "发件箱", "已发送", "草稿箱", "转发", "回复", "抄送", "密送"],
            "备份存档": ["备份", "备份文件", "存档", "历史版本", "旧版本", "备份数据",
                        "备份包", "数据备份", "文件备份", "系统备份"],
            "临时文件": ["临时", "temp", "tmp", "缓存", "cache", "临时文件", "草稿",
                        "未完成", "进行中", "处理中", "备份~"],
        }
        
        # 加载自定义词典
        if JIEBA_AVAILABLE:
            self.load_custom_dict()
    
    def is_available(self):
        """检查AI内容分类功能是否可用"""
        return JIEBA_AVAILABLE
    
    def is_semantic_available(self):
        """语义分类功能不可用"""
        return False
    
    def load_custom_dict(self):
        """加载自定义词典以提高分词准确性"""
        custom_dict_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'custom_dict.txt')
        custom_dict_path = os.path.abspath(custom_dict_path)
        if os.path.exists(custom_dict_path):
            try:
                jieba.load_userdict(custom_dict_path)
            except Exception as e:
                print(f"加载自定义词典失败: {e}")
    
    def extract_text_from_file(self, file_path):
        """从不同类型的文件中提取文本内容"""
        ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if ext == '.txt':
                return self._extract_txt(file_path)
            elif ext == '.pdf':
                if PDFPLUMBER_AVAILABLE:
                    return self._extract_pdf(file_path)
                else:
                    return ""
            elif ext == '.docx':
                if DOCX_AVAILABLE:
                    return self._extract_docx(file_path)
                else:
                    return ""
            else:
                return ""
        except Exception as e:
            print(f"提取文件 {file_path} 内容失败: {e}")
            return ""
    
    def _extract_txt(self, file_path):
        """提取TXT文件内容"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, 'r', encoding='gbk') as f:
                    return f.read()
            except:
                return ""
    
    def _extract_pdf(self, file_path):
        """提取PDF文件内容"""
        try:
            with open_pdf(file_path) as pdf:
                text = ""
                for page in pdf.pages:
                    text += page.extract_text() or ""
                return text
        except Exception as e:
            print(f"PDF提取失败 {file_path}: {e}")
            return ""
    
    def _extract_docx(self, file_path):
        """提取Word文档内容"""
        try:
            doc = Document(file_path)
            return '\n'.join([para.text for para in doc.paragraphs])
        except Exception as e:
            print(f"DOCX提取失败 {file_path}: {e}")
            return ""
    
    def get_keywords(self, text, top_n=20):
        """使用jieba提取关键词"""
        # 判空：如果传入文本为空，直接返回空列表
        if not text:
            return []
        # 检测jieba库是否可用，环境异常则返回空列表
        if not JIEBA_AVAILABLE:
            print("jieba不可用，无法提取关键词")
            return []
        
        # 优先使用TF-IDF提取关键词
        try:
            # 提取topK个关键词，不返回权重值
            keywords = jieba.analyse.extract_tags(text, topK=top_n, withWeight=False)
            return keywords
        
        # 如果TF-IDF失败，进入降级方案：基础分词处理
        except Exception as e:
            print(f"关键词提取失败: {e}")
            # 对全文进行普通中文分词，返回分词列表（列表结构）
            words = jieba.lcut(text)
            # 列表推导式：过滤单字、过滤停用词
            filtered = [w for w in words if len(w) > 1 and not self._is_stopword(w)]
            # 统计词频，取出出现频次最高的 top_n 个词汇作为关键词
            return Counter(filtered).most_common(top_n)
    
    def _is_stopword(self, word):
        """判断是否为停用词"""
        stopwords = {'的', '是', '在', '有', '和', '了', '我', '你', '他', '她', '它',
                     '这', '那', '这个', '那个', '什么', '怎么', '为什么', '因为',
                     '所以', '但是', '如果', '虽然', '还是', '或者', '就是', '都'}
        return word in stopwords
    
    def classify_by_content(self, file_path):
        """根据文件内容进行分类（使用关键词分类）"""
        text = self.extract_text_from_file(file_path)
        
        if not text:
            return "其他文档"
        
        keywords = self.get_keywords(text)
        
        # 统计每个分类的关键词匹配数
        scores = {}
        for category, keywords_list in self.category_rules.items():
            score = 0
            for kw in keywords:
                if kw in keywords_list:
                    score += 1
            scores[category] = score
        
        # 找到得分最高的分类
        max_score = max(scores.values())
        
        if max_score >= 2:
            for category, score in scores.items():
                if score == max_score:
                    return f"【AI分类】{category}"
        else:
            return "【AI分类】其他文档"
    
    def get_category_rules(self):
        """获取当前的分类规则"""
        return self.category_rules
    
    def add_category_rule(self, category_name, keywords):
        """添加新的分类规则"""
        self.category_rules[category_name] = keywords
    
    def batch_classify(self, directory):
        """批量分类目录中的文档"""
        results = []
        
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            
            if not os.path.isfile(file_path):
                continue
            
            ext = os.path.splitext(filename)[1].lower()
            if ext not in ['.txt', '.pdf', '.docx']:
                continue
            
            category = self.classify_by_content(file_path)
            results.append({
                "filename": filename,
                "path": file_path,
                "category": category
            })
        
        return results
