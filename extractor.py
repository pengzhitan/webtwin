# -*- coding: utf-8 -*-
"""
WebTwin 网站提取核心引擎

主要功能:
- 使用Selenium WebDriver进行高级网页渲染
- 下载HTML、CSS、JavaScript、图片等资源
- 处理动态加载的内容
- 生成完整的网站副本

Author: WebTwin Team
Version: 1.0.0
"""

import os
import re
import time
import zipfile
import requests
import urllib.parse
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote
from bs4 import BeautifulSoup

# Selenium imports
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("警告: Selenium未安装，将使用基础模式")

class WebsiteExtractor:
    """网站提取器主类"""
    
    def __init__(self, config=None):
        """初始化提取器
        
        Args:
            config (dict): 配置参数
        """
        self.config = config or {}
        self.use_selenium = self.config.get('use_selenium', False)
        self.timeout = self.config.get('timeout', 30)
        self.depth = self.config.get('depth', 1)
        self.include_assets = self.config.get('include_assets', True)
        
        # 会话对象用于HTTP请求
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'WebTwin-Extractor/1.0 (Website Extraction Tool)'
        })
        
        # 资源统计
        self.extracted_resources = []
        self.failed_resources = []
        
        # WebDriver实例
        self.driver = None
        
    def extract_website(self, url, progress_callback=None):
        """提取网站主函数
        
        Args:
            url (str): 目标网站URL
            progress_callback (callable): 进度回调函数
            
        Returns:
            dict: 提取结果
        """
        try:
            self.progress_callback = progress_callback or (lambda p, s: None)
            self.base_url = url
            self.domain = urlparse(url).netloc
            
            # 创建输出目录
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            self.output_dir = f'webtwin_{self.domain}_{timestamp}'
            self.full_output_path = os.path.join('downloads', self.output_dir)
            os.makedirs(self.full_output_path, exist_ok=True)
            
            self.progress_callback(5, '初始化完成，开始提取网站...')
            
            # 根据配置选择提取方式
            if self.use_selenium and SELENIUM_AVAILABLE:
                html_content = self._extract_with_selenium(url)
            else:
                html_content = self._extract_with_requests(url)
                
            if not html_content:
                return {
                    'success': False,
                    'error': '无法获取网站内容'
                }
                
            self.progress_callback(30, '网页内容获取完成，开始解析资源...')
            
            # 解析HTML并提取资源
            soup = BeautifulSoup(html_content, 'html.parser')
            self._extract_resources(soup, url)
            
            self.progress_callback(80, '资源提取完成，正在打包文件...')
            
            # 保存主HTML文件
            self._save_html(soup, 'index.html')
            
            # 创建ZIP文件
            zip_path = self._create_zip_archive()
            
            self.progress_callback(100, '提取完成！')
            
            return {
                'success': True,
                'output_path': zip_path,
                'resources': self.extracted_resources,
                'failed_resources': self.failed_resources,
                'stats': {
                    'total_resources': len(self.extracted_resources),
                    'failed_resources': len(self.failed_resources),
                    'output_size': os.path.getsize(zip_path) if os.path.exists(zip_path) else 0
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            self._cleanup()
            
    def _extract_with_selenium(self, url):
        """使用Selenium提取网页内容"""
        try:
            self.progress_callback(10, '启动Chrome浏览器...')
            
            # 配置Chrome选项
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-plugins')
            
            # 创建WebDriver
            try:
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            except Exception:
                # 尝试使用系统PATH中的chromedriver
                self.driver = webdriver.Chrome(options=chrome_options)
                
            self.driver.set_page_load_timeout(self.timeout)
            
            self.progress_callback(15, '正在加载网页...')
            
            # 加载页面
            self.driver.get(url)
            
            # 等待页面加载完成
            WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, 'body'))
            )
            
            # 等待JavaScript执行
            time.sleep(3)
            
            self.progress_callback(25, '页面加载完成，获取渲染后的HTML...')
            
            # 获取渲染后的HTML
            html_content = self.driver.page_source
            
            return html_content
            
        except Exception as e:
            self.progress_callback(0, f'Selenium提取失败: {str(e)}')
            # 回退到requests方式
            return self._extract_with_requests(url)
            
    def _extract_with_requests(self, url):
        """使用requests提取网页内容"""
        try:
            self.progress_callback(10, '发送HTTP请求...')
            
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            # 检测编码
            if response.encoding == 'ISO-8859-1':
                response.encoding = response.apparent_encoding
                
            self.progress_callback(25, 'HTTP请求完成，获取页面内容...')
            
            return response.text
            
        except Exception as e:
            raise Exception(f'HTTP请求失败: {str(e)}')
            
    def _extract_resources(self, soup, base_url):
        """提取页面中的所有资源"""
        if not self.include_assets:
            return
            
        # 资源类型映射
        resource_selectors = {
            'css': {
                'selector': 'link[rel="stylesheet"]',
                'attr': 'href',
                'folder': 'css'
            },
            'js': {
                'selector': 'script[src]',
                'attr': 'src', 
                'folder': 'js'
            },
            'images': {
                'selector': 'img[src]',
                'attr': 'src',
                'folder': 'images'
            },
            'fonts': {
                'selector': 'link[href*=".woff"], link[href*=".ttf"], link[href*=".eot"]',
                'attr': 'href',
                'folder': 'fonts'
            }
        }
        
        total_resources = 0
        processed_resources = 0
        
        # 计算总资源数
        for resource_type, config in resource_selectors.items():
            elements = soup.select(config['selector'])
            total_resources += len(elements)
            
        self.progress_callback(35, f'发现 {total_resources} 个资源，开始下载...')
        
        # 下载各类资源
        for resource_type, config in resource_selectors.items():
            elements = soup.select(config['selector'])
            
            for element in elements:
                try:
                    resource_url = element.get(config['attr'])
                    if not resource_url:
                        continue
                        
                    # 转换为绝对URL
                    absolute_url = urljoin(base_url, resource_url)
                    
                    # 下载资源
                    local_path = self._download_resource(
                        absolute_url, 
                        config['folder'],
                        resource_type
                    )
                    
                    if local_path:
                        # 更新HTML中的链接
                        relative_path = os.path.relpath(local_path, self.full_output_path).replace('\\', '/')
                        element[config['attr']] = relative_path
                        
                        self.extracted_resources.append({
                            'type': resource_type,
                            'original_url': absolute_url,
                            'local_path': local_path,
                            'size': os.path.getsize(local_path) if os.path.exists(local_path) else 0
                        })
                        
                except Exception as e:
                    self.failed_resources.append({
                        'url': resource_url,
                        'error': str(e),
                        'type': resource_type
                    })
                    
                processed_resources += 1
                progress = 35 + int((processed_resources / total_resources) * 40)
                self.progress_callback(progress, f'已处理 {processed_resources}/{total_resources} 个资源...')
                
    def _download_resource(self, url, folder, resource_type):
        """下载单个资源文件"""
        try:
            # 解析URL获取文件名
            parsed_url = urlparse(url)
            filename = os.path.basename(unquote(parsed_url.path))
            
            if not filename or '.' not in filename:
                # 生成默认文件名
                ext_map = {
                    'css': '.css',
                    'js': '.js', 
                    'images': '.jpg',
                    'fonts': '.woff'
                }
                filename = f'resource_{len(self.extracted_resources)}{ext_map.get(resource_type, ".txt")}'
                
            # 创建目标目录
            target_dir = os.path.join(self.full_output_path, folder)
            os.makedirs(target_dir, exist_ok=True)
            
            # 确保文件名唯一
            target_path = os.path.join(target_dir, filename)
            counter = 1
            while os.path.exists(target_path):
                name, ext = os.path.splitext(filename)
                target_path = os.path.join(target_dir, f'{name}_{counter}{ext}')
                counter += 1
                
            # 下载文件
            response = self.session.get(url, timeout=10, stream=True)
            response.raise_for_status()
            
            with open(target_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            return target_path
            
        except Exception as e:
            print(f'下载资源失败 {url}: {str(e)}')
            return None
            
    def _save_html(self, soup, filename):
        """保存HTML文件"""
        html_path = os.path.join(self.full_output_path, filename)
        
        # 美化HTML
        html_content = soup.prettify()
        
        # 添加WebTwin标识
        html_content = html_content.replace(
            '<head>',
            '<head>\n    <!-- Extracted by WebTwin - Website Extraction Tool -->\n    <meta name="generator" content="WebTwin v1.0">'
        )
        
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
    def _create_zip_archive(self):
        """创建ZIP压缩包"""
        zip_filename = f'{self.output_dir}.zip'
        zip_path = os.path.join('downloads', zip_filename)
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 遍历输出目录中的所有文件
            for root, dirs, files in os.walk(self.full_output_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    # 计算相对路径
                    arcname = os.path.relpath(file_path, self.full_output_path)
                    zipf.write(file_path, arcname)
                    
            # 添加提取信息文件
            info_content = f"""WebTwin 提取信息
===================

目标URL: {self.base_url}
提取时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
提取模式: {'Selenium (高级渲染)' if self.use_selenium else 'HTTP请求 (基础模式)'}

资源统计:
- 成功提取: {len(self.extracted_resources)} 个文件
- 提取失败: {len(self.failed_resources)} 个文件

文件结构:
- index.html: 主页面文件
- css/: CSS样式文件
- js/: JavaScript脚本文件
- images/: 图片资源文件
- fonts/: 字体文件

使用说明:
1. 解压此ZIP文件到任意目录
2. 使用浏览器打开 index.html 文件
3. 或在代码编辑器中打开进行分析

由 WebTwin v1.0 生成
"""
            zipf.writestr('WebTwin_Info.txt', info_content)
            
        return zip_path
        
    def _cleanup(self):
        """清理资源"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
                
        # 清理临时目录
        if hasattr(self, 'full_output_path') and os.path.exists(self.full_output_path):
            try:
                import shutil
                shutil.rmtree(self.full_output_path)
            except:
                pass

class ResourceDownloader:
    """资源下载器辅助类"""
    
    def __init__(self, session=None):
        self.session = session or requests.Session()
        
    def download_css_resources(self, css_content, base_url, output_dir):
        """下载CSS中引用的资源"""
        # 查找CSS中的url()引用
        url_pattern = r'url\(["\']?([^"\')]+)["\']?\)'
        urls = re.findall(url_pattern, css_content)
        
        for url in urls:
            try:
                absolute_url = urljoin(base_url, url)
                # 下载并替换URL
                # 这里可以扩展实现
                pass
            except:
                continue
                
        return css_content

if __name__ == '__main__':
    # 测试代码
    def test_progress(progress, step):
        print(f'[{progress}%] {step}')
        
    extractor = WebsiteExtractor({
        'use_selenium': True,
        'include_assets': True,
        'depth': 1
    })
    
    result = extractor.extract_website('https://example.com', test_progress)
    print('提取结果:', result)