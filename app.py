# -*- coding: utf-8 -*-
"""
WebTwin 网站提取工具 - Flask Web应用

主要功能:
- 提供Web界面用于输入URL和配置选项
- 处理网站提取请求
- 实时显示提取进度
- 提供文件下载服务

Author: WebTwin Team
Version: 1.0.0
"""

import os
import uuid
import json
import threading
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
from werkzeug.utils import secure_filename

# 导入配置和核心模块
try:
    from config import *
except ImportError:
    # 默认配置
    DEBUG = True
    HOST = '127.0.0.1'
    PORT = 5001
    OUTPUT_DIR = 'downloads'
    SELENIUM_TIMEOUT = 30

# 创建Flask应用实例
app = Flask(__name__)
app.config['SECRET_KEY'] = 'webtwin-secret-key-2024'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB

# 全局变量存储任务状态
tasks = {}
task_lock = threading.Lock()

# 定义目录路径
OUTPUT_DIR = os.path.join(os.getcwd(), 'output')
TEMP_DIR = os.path.join(os.getcwd(), 'temp')
LOG_DIR = os.path.join(os.getcwd(), 'logs')

# 服务器配置
HOST = '127.0.0.1'
PORT = 5000
DEBUG = True

# 确保输出目录存在
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs('static', exist_ok=True)
os.makedirs('templates', exist_ok=True)

class TaskStatus:
    """任务状态管理类"""
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'

class ExtractionTask:
    """提取任务数据模型"""
    def __init__(self, url, config=None):
        self.task_id = str(uuid.uuid4())
        self.url = url
        self.status = TaskStatus.PENDING
        self.progress = 0
        self.current_step = '准备开始提取...'
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.config = config or {}
        self.output_path = ''
        self.download_url = ''
        self.error_message = ''
        self.extracted_resources = []
        
    def update_progress(self, progress, step, status=None):
        """更新任务进度"""
        self.progress = progress
        self.current_step = step
        self.updated_at = datetime.now()
        if status:
            self.status = status
            
    def to_dict(self):
        """转换为字典格式"""
        return {
            'task_id': self.task_id,
            'url': self.url,
            'status': self.status,
            'progress': self.progress,
            'current_step': self.current_step,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'config': self.config,
            'download_url': self.download_url,
            'error_message': self.error_message,
            'resource_count': len(self.extracted_resources)
        }

@app.route('/')
def index():
    """主页面 - 显示URL输入表单和配置选项"""
    return render_template('index.html')

@app.route('/extract', methods=['POST'])
def extract_website():
    """网站提取API端点"""
    try:
        # 获取请求数据
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({
                'success': False,
                'message': '请提供有效的URL地址'
            }), 400
            
        url = data['url'].strip()
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        # 创建提取任务
        config = {
            'use_selenium': data.get('use_selenium', False),
            'depth': data.get('depth', 1),
            'include_assets': data.get('include_assets', True),
            'timeout': data.get('timeout', SELENIUM_TIMEOUT)
        }
        
        task = ExtractionTask(url, config)
        
        # 存储任务
        with task_lock:
            tasks[task.task_id] = task
            
        # 启动后台提取线程
        extraction_thread = threading.Thread(
            target=run_extraction_task,
            args=(task.task_id,)
        )
        extraction_thread.daemon = True
        extraction_thread.start()
        
        return jsonify({
            'success': True,
            'task_id': task.task_id,
            'message': '提取任务已启动'
        })
        
    except Exception as e:
        app.logger.error(f'提取请求处理错误: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'服务器错误: {str(e)}'
        }), 500

@app.route('/progress/<task_id>')
def get_progress(task_id):
    """获取提取进度API端点"""
    with task_lock:
        task = tasks.get(task_id)
        
    if not task:
        return jsonify({
            'error': '任务不存在'
        }), 404
        
    return jsonify(task.to_dict())

@app.route('/download/<filename>')
def download_file(filename):
    """文件下载端点"""
    try:
        # 安全文件名检查
        safe_filename = secure_filename(filename)
        file_path = os.path.join(OUTPUT_DIR, safe_filename)
        
        if not os.path.exists(file_path):
            return jsonify({
                'error': '文件不存在'
            }), 404
            
        return send_file(
            file_path,
            as_attachment=True,
            download_name=safe_filename
        )
        
    except Exception as e:
        app.logger.error(f'文件下载错误: {str(e)}')
        return jsonify({
            'error': f'下载失败: {str(e)}'
        }), 500

@app.route('/result/<task_id>')
def show_result(task_id):
    """显示提取结果页面"""
    with task_lock:
        task = tasks.get(task_id)
        
    if not task:
        return redirect(url_for('index'))
        
    return render_template('result.html', task=task)

@app.route('/settings')
def settings():
    """设置页面"""
    return render_template('settings.html')

@app.route('/api/tasks')
def list_tasks():
    """获取所有任务列表API"""
    with task_lock:
        task_list = [task.to_dict() for task in tasks.values()]
        
    # 按创建时间倒序排列
    task_list.sort(key=lambda x: x['created_at'], reverse=True)
    
    return jsonify({
        'tasks': task_list,
        'total': len(task_list)
    })

@app.route('/api/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    """删除任务API"""
    with task_lock:
        if task_id in tasks:
            task = tasks[task_id]
            # 清理输出文件
            if task.output_path and os.path.exists(task.output_path):
                try:
                    os.remove(task.output_path)
                except:
                    pass
            del tasks[task_id]
            return jsonify({'success': True})
        else:
            return jsonify({'error': '任务不存在'}), 404

def run_extraction_task(task_id):
    """运行提取任务的后台函数"""
    with task_lock:
        task = tasks.get(task_id)
        
    if not task:
        return
        
    try:
        # 更新任务状态
        task.update_progress(0, '初始化提取引擎...', TaskStatus.RUNNING)
        
        # 导入提取引擎
        try:
            from extractor import WebsiteExtractor
        except ImportError:
            # 如果extractor模块不存在，使用简单的模拟提取
            simulate_extraction(task)
            return
            
        # 创建提取器实例
        extractor = WebsiteExtractor(task.config)
        
        # 执行提取
        result = extractor.extract_website(
            task.url,
            progress_callback=lambda p, s: task.update_progress(p, s)
        )
        
        if result['success']:
            task.output_path = result['output_path']
            task.download_url = f'/download/{os.path.basename(result["output_path"])}'
            task.extracted_resources = result.get('resources', [])
            task.update_progress(100, '提取完成！', TaskStatus.COMPLETED)
        else:
            task.error_message = result.get('error', '未知错误')
            task.update_progress(0, f'提取失败: {task.error_message}', TaskStatus.FAILED)
            
    except Exception as e:
        app.logger.error(f'任务 {task_id} 执行错误: {str(e)}')
        task.error_message = str(e)
        task.update_progress(0, f'提取失败: {str(e)}', TaskStatus.FAILED)

def simulate_extraction(task):
    """模拟提取过程（用于测试）"""
    steps = [
        (10, '分析网站结构...'),
        (25, '下载HTML内容...'),
        (40, '提取CSS样式...'),
        (60, '下载JavaScript文件...'),
        (80, '获取图片资源...'),
        (95, '打包文件...'),
        (100, '提取完成！')
    ]
    
    for progress, step in steps:
        task.update_progress(progress, step)
        time.sleep(1)  # 模拟处理时间
        
    # 创建模拟输出文件
    output_filename = f'webtwin_{task.task_id[:8]}.zip'
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    
    # 创建一个简单的ZIP文件
    import zipfile
    with zipfile.ZipFile(output_path, 'w') as zf:
        zf.writestr('index.html', f'<html><body><h1>WebTwin提取结果</h1><p>URL: {task.url}</p></body></html>')
        zf.writestr('README.txt', f'WebTwin提取结果\n目标URL: {task.url}\n提取时间: {datetime.now()}')
    
    task.output_path = output_path
    task.download_url = f'/download/{output_filename}'
    task.update_progress(100, '提取完成！', TaskStatus.COMPLETED)

@app.errorhandler(404)
def not_found_error(error):
    """404错误处理"""
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """500错误处理"""
    return render_template('500.html'), 500

if __name__ == '__main__':
    import argparse
    
    # 命令行参数解析
    parser = argparse.ArgumentParser(description='WebTwin 网站提取工具')
    parser.add_argument('--host', default=HOST, help='服务器地址')
    parser.add_argument('--port', type=int, default=PORT, help='服务器端口')
    parser.add_argument('--debug', action='store_true', help='调试模式')
    
    args = parser.parse_args()
    
    print(f"""\n🚀 WebTwin 网站提取工具启动中...
📍 访问地址: http://{args.host}:{args.port}
🔧 调试模式: {'开启' if args.debug or DEBUG else '关闭'}
📁 输出目录: {os.path.abspath(OUTPUT_DIR)}
""")
    
    # 启动Flask应用
    app.run(
        host=args.host,
        port=args.port,
        debug=args.debug or DEBUG,
        threaded=True
    )