import os
from dotenv import load_dotenv

# 加载.env文件中的环境变量
load_dotenv()

# ============ API配置 ============
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY")
ZHIPU_API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

# ============ 期刊配置（ISSN模式）============
JOURNALS = {
    # 综合性顶刊
    "Nature": "0028-0836",
    "Science": "0036-8075",
    
    # AI顶刊
    "Journal of Machine Learning Research (JMLR)": "1533-7928",
    "Artificial Intelligence (AIJ)": "0004-3702",
    "IEEE Transactions on Pattern Analysis and Machine Intelligence (TPAMI)": "0162-8828",
    "Machine Learning (MLJ)": "0885-6125",
    "Data Mining and Knowledge Discovery (DMKD)": "1384-5810",
    "IEEE Transactions on Neural Networks and Learning Systems (TNNLS)": "2162-237X",
    "Neural Computation": "0899-7667",
    "Journal of Artificial Intelligence Research (JAIR)": "1076-9757",
    "IEEE Transactions on Knowledge and Data Engineering (TKDE)": "1041-4347",
    "ACM Transactions on Intelligent Systems and Technology (TIST)": "2157-6904",
    "ACM Computing Surveys (CSUR)": "0360-0300",
    
    # 计算机视觉与AI
    "International Journal of Computer Vision (IJCV)": "0920-5691",
    "IEEE Transactions on Image Processing (TIP)": "1057-7149",
    "Computer Vision and Image Understanding (CVIU)": "1077-3142",
    
    # 自然语言处理
    "Computational Linguistics": "0891-2017",
    "Transactions of the Association for Computational Linguistics (TACL)": "2307-387X",
    
    # 信息安全
    "IEEE Transactions on Information Forensics and Security (TIFS)": "1556-6013",
    "Computers & Security": "0167-4048",

    # 遥感领域顶刊
    "Remote Sensing of Environment": "0034-4257",
    "ISPRS Journal of Photogrammetry": "0924-2716",
    "IEEE Transactions on Geoscience and Remote Sensing": "0196-2892",
    "IEEE Geoscience and Remote Sensing Letters": "1545-598X",
    "International Journal of Remote Sensing": "0143-1161",
    "Remote Sensing": "2072-4292",
    "IEEE Journal of Selected Topics in Applied Earth Observations": "1939-1404",
    
    # GIS与地理信息科学
    "International Journal of Applied Earth Observation": "1569-8432",
    "International Journal of Geographical Information Science": "1365-8816",
    "GIScience & Remote Sensing": "1548-1603",
    "Transactions in GIS": "1361-1682",
    "GeoInformatica": "1384-6175",
    
    # 地球科学计算
    "Computers & Geosciences": "0098-3004",
    "Earth Science Informatics": "1865-0473",
    
    # 地理人工智能相关
    "Annals of GIS": "1947-5683",
    "Big Earth Data": "2096-4471",
}

# ============ arXiv 分类配置 ============
ARXIV_CATEGORIES = {
    "arXiv - AI": "cs.AI",
    "arXiv - CV": "cs.CV",
    "arXiv - CL (NLP)": "cs.CL",
    "arXiv - LG (ML)": "cs.LG",
    "arXiv - IR": "cs.IR",
    "arXiv - DB": "cs.DB",
    "arXiv - Robotics": "cs.RO",
}

# ============ 会议配置 ============
CONFERENCES = {
    "CVPR / ICCV (IEEE)": {"prefix": "10.1109", "type": "conference"},
    "NeurIPS (MIT Press)": {"prefix": "10.5555", "type": "conference"},
    "ACL / EMNLP (ACL)": {"prefix": "10.18653", "type": "conference"},
    "ACM Conference (ICML/AAAI)": {"prefix": "10.1145", "type": "conference"},
    "Springer Conference (ECCV/ECML)": {"prefix": "10.1007", "type": "conference"},
}

# ============ 研究领域配置 ============
RESEARCH_AREA = """
地理人工智能、遥感、地理信息科学、深度学习、计算机视觉、时空数据分析、
点云处理、LiDAR、图像分割、目标检测、变化检测、地表覆盖分类、
GIScience、摄影测量、地球观测、环境遥感
"""

# ============ 默认配置（用户可在Web界面覆盖）============
DEFAULT_DAYS_BACK = 7
DEFAULT_MAX_RESULTS_PER_JOURNAL = 10

# 兼容旧代码
DAYS_BACK = DEFAULT_DAYS_BACK
MAX_RESULTS_PER_JOURNAL = DEFAULT_MAX_RESULTS_PER_JOURNAL