#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebTwin 配置文件
包含应用的所有配置参数
"""

import os
from pathlib import Path

# 基础路径
BASE_DIR = Path(__file__).parent.absolute()
STATIC_DIR = BASE_DIR / 'static'
TEMPLATES_DIR = BASE_DIR / 'templates'
DOWNLOADS_DIR = BASE_DIR / 'downloads'
LOGS_DIR = BASE_DIR / 'logs'
TEMP_DIR = BASE_DIR / 'temp'

# 确保目录存在
for directory in [DOWNLOADS_DIR, LOGS_DIR, TEMP_DIR]:
    directory.mkdir(exist_ok=True)

class Config:
    """基础配置类"""
    
    # Flask 配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'webtwin-secret-key-change-in-production'
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    HOST = os.environ.get('FLASK_HOST', '127.0.0.1')
    PORT = int(os.environ.get('FLASK_PORT', 5000))
    
    # 应用配置
    APP_NAME = 'WebTwin'
    APP_VERSION = '1.0.0'
    APP_DESCRIPTION = 'Advanced Website Extraction Tool'
    
    # 文件路径配置
    STATIC_FOLDER = str(STATIC_DIR)
    TEMPLATE_FOLDER = str(TEMPLATES_DIR)
    DOWNLOADS_FOLDER = str(DOWNLOADS_DIR)
    LOGS_FOLDER = str(LOGS_DIR)
    TEMP_FOLDER = str(TEMP_DIR)
    
    # 提取配置
    DEFAULT_DEPTH = 2
    MAX_DEPTH = 10
    DEFAULT_TIMEOUT = 30
    MAX_TIMEOUT = 300
    DEFAULT_RETRIES = 3
    MAX_RETRIES = 10
    DEFAULT_CONCURRENT_REQUESTS = 5
    MAX_CONCURRENT_REQUESTS = 20
    
    # 文件大小限制（字节）
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    MAX_TOTAL_SIZE = 1024 * 1024 * 1024  # 1GB
    
    # 支持的文件类型
    SUPPORTED_EXTENSIONS = {
        'html': ['.html', '.htm', '.xhtml'],
        'css': ['.css'],
        'js': ['.js', '.jsx', '.ts', '.tsx'],
        'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.ico'],
        'font': ['.woff', '.woff2', '.ttf', '.otf', '.eot'],
        'other': ['.pdf', '.txt', '.xml', '.json', '.csv']
    }
    
    # 默认包含的资源类型
    DEFAULT_RESOURCE_TYPES = ['html', 'css', 'js', 'image']
    
    # 排除模式（正则表达式）
    DEFAULT_EXCLUDE_PATTERNS = [
        r'.*\.(exe|zip|rar|7z|tar|gz)$',  # 压缩文件和可执行文件
        r'.*/(ads?|advertisement|tracking|analytics)/',  # 广告和跟踪
        r'.*/\.(git|svn|hg)/',  # 版本控制目录
        r'.*/(node_modules|vendor|bower_components)/',  # 依赖目录
        r'.*\.(log|tmp|temp|cache)$',  # 临时文件
    ]
    
    # Selenium 配置
    SELENIUM_ENABLED = True
    SELENIUM_BROWSER = 'chrome'  # chrome, firefox, edge
    SELENIUM_HEADLESS = True
    SELENIUM_PAGE_LOAD_TIMEOUT = 30
    SELENIUM_IMPLICIT_WAIT = 10
    SELENIUM_WINDOW_SIZE = (1920, 1080)
    SELENIUM_DISABLE_IMAGES = True
    SELENIUM_DISABLE_CSS = False
    SELENIUM_DISABLE_JAVASCRIPT = False
    
    # Chrome 选项
    CHROME_OPTIONS = [
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--disable-extensions',
        '--disable-plugins',
        '--disable-images' if SELENIUM_DISABLE_IMAGES else '',
        '--disable-javascript' if SELENIUM_DISABLE_JAVASCRIPT else '',
        '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    ]
    
    # Firefox 选项
    FIREFOX_OPTIONS = [
        '--headless' if SELENIUM_HEADLESS else '',
    ]
    
    # 请求配置
    REQUEST_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    # 会话配置
    SESSION_POOL_SIZE = 10
    SESSION_POOL_MAXSIZE = 20
    
    # 日志配置
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5
    
    # 任务配置
    TASK_CLEANUP_INTERVAL = 3600  # 1小时
    TASK_MAX_AGE = 24 * 3600  # 24小时
    MAX_CONCURRENT_TASKS = 5
    
    # 缓存配置
    CACHE_ENABLED = True
    CACHE_TTL = 3600  # 1小时
    CACHE_MAX_SIZE = 1000
    
    # 安全配置
    ALLOWED_DOMAINS = []  # 空列表表示允许所有域名
    BLOCKED_DOMAINS = [
        'localhost',
        '127.0.0.1',
        '0.0.0.0',
        '::1'
    ]
    
    # 速率限制
    RATE_LIMIT_ENABLED = True
    RATE_LIMIT_REQUESTS = 100  # 每分钟请求数
    RATE_LIMIT_WINDOW = 60  # 时间窗口（秒）
    
    # 监控配置
    METRICS_ENABLED = True
    HEALTH_CHECK_ENABLED = True
    
    @classmethod
    def get_chrome_options(cls):
        """获取Chrome选项"""
        from selenium.webdriver.chrome.options import Options
        options = Options()
        
        for option in cls.CHROME_OPTIONS:
            if option:  # 跳过空字符串
                options.add_argument(option)
        
        if cls.SELENIUM_HEADLESS:
            options.add_argument('--headless')
        
        # 设置窗口大小
        options.add_argument(f'--window-size={cls.SELENIUM_WINDOW_SIZE[0]},{cls.SELENIUM_WINDOW_SIZE[1]}')
        
        # 禁用图片加载以提高速度
        if cls.SELENIUM_DISABLE_IMAGES:
            prefs = {"profile.managed_default_content_settings.images": 2}
            options.add_experimental_option("prefs", prefs)
        
        return options
    
    @classmethod
    def get_firefox_options(cls):
        """获取Firefox选项"""
        from selenium.webdriver.firefox.options import Options
        options = Options()
        
        if cls.SELENIUM_HEADLESS:
            options.add_argument('--headless')
        
        # 设置用户代理
        options.set_preference('general.useragent.override', cls.REQUEST_HEADERS['User-Agent'])
        
        # 禁用图片加载
        if cls.SELENIUM_DISABLE_IMAGES:
            options.set_preference('permissions.default.image', 2)
        
        return options
    
    @classmethod
    def get_edge_options(cls):
        """获取Edge选项"""
        from selenium.webdriver.edge.options import Options
        options = Options()
        
        for option in cls.CHROME_OPTIONS:  # Edge使用类似Chrome的选项
            if option:
                options.add_argument(option)
        
        if cls.SELENIUM_HEADLESS:
            options.add_argument('--headless')
        
        options.add_argument(f'--window-size={cls.SELENIUM_WINDOW_SIZE[0]},{cls.SELENIUM_WINDOW_SIZE[1]}')
        
        return options
    
    @classmethod
    def is_allowed_url(cls, url):
        """检查URL是否被允许"""
        from urllib.parse import urlparse
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # 检查被阻止的域名
            for blocked in cls.BLOCKED_DOMAINS:
                if blocked in domain:
                    return False
            
            # 检查允许的域名（如果设置了）
            if cls.ALLOWED_DOMAINS:
                for allowed in cls.ALLOWED_DOMAINS:
                    if allowed in domain:
                        return True
                return False
            
            return True
        except Exception:
            return False
    
    @classmethod
    def get_file_type(cls, filename):
        """根据文件名获取文件类型"""
        ext = Path(filename).suffix.lower()
        
        for file_type, extensions in cls.SUPPORTED_EXTENSIONS.items():
            if ext in extensions:
                return file_type
        
        return 'other'
    
    @classmethod
    def is_supported_file(cls, filename):
        """检查文件是否被支持"""
        return cls.get_file_type(filename) != 'other' or Path(filename).suffix.lower() in cls.SUPPORTED_EXTENSIONS['other']


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'
    SELENIUM_HEADLESS = False  # 开发时显示浏览器
    CACHE_ENABLED = False  # 开发时禁用缓存
    RATE_LIMIT_ENABLED = False  # 开发时禁用速率限制


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    LOG_LEVEL = 'WARNING'
    SELENIUM_HEADLESS = True
    CACHE_ENABLED = True
    RATE_LIMIT_ENABLED = True
    
    # 生产环境安全配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(32).hex()
    
    # 更严格的文件大小限制
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    MAX_TOTAL_SIZE = 500 * 1024 * 1024  # 500MB


class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    DEBUG = True
    LOG_LEVEL = 'DEBUG'
    SELENIUM_HEADLESS = True
    CACHE_ENABLED = False
    RATE_LIMIT_ENABLED = False
    
    # 测试用的较小限制
    MAX_FILE_SIZE = 1024 * 1024  # 1MB
    MAX_TOTAL_SIZE = 10 * 1024 * 1024  # 10MB
    DEFAULT_TIMEOUT = 5
    MAX_CONCURRENT_REQUESTS = 2


# 配置映射
config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(config_name=None):
    """获取配置对象"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')
    
    return config_map.get(config_name, DevelopmentConfig)