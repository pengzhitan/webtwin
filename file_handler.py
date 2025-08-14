#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebTwin 文件处理和ZIP打包模块
处理文件操作、压缩和管理功能
"""

import os
import shutil
import zipfile
import mimetypes
import hashlib
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
import logging
from urllib.parse import urlparse, unquote
import re

from config import Config


class FileHandler:
    """文件处理器"""
    
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.logger = logging.getLogger(__name__)
        
        # 确保必要目录存在
        self._ensure_directories()
    
    def _ensure_directories(self):
        """确保必要的目录存在"""
        directories = [
            self.config.DOWNLOADS_FOLDER,
            self.config.TEMP_FOLDER,
            self.config.LOGS_FOLDER
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    def sanitize_filename(self, filename: str) -> str:
        """清理文件名，移除非法字符"""
        # 移除或替换非法字符
        illegal_chars = r'[<>:"/\\|?*]'
        filename = re.sub(illegal_chars, '_', filename)
        
        # 移除控制字符
        filename = ''.join(char for char in filename if ord(char) >= 32)
        
        # 限制长度
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            filename = name[:255-len(ext)] + ext
        
        # 避免保留名称
        reserved_names = {
            'CON', 'PRN', 'AUX', 'NUL',
            'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        }
        
        name_without_ext = os.path.splitext(filename)[0].upper()
        if name_without_ext in reserved_names:
            filename = f"_{filename}"
        
        return filename or 'unnamed_file'
    
    def get_safe_path(self, base_path: str, relative_path: str) -> str:
        """获取安全的文件路径，防止路径遍历攻击"""
        # 清理相对路径
        relative_path = relative_path.lstrip('/')
        relative_path = os.path.normpath(relative_path)
        
        # 分割路径并清理每个部分
        path_parts = []
        for part in relative_path.split(os.sep):
            if part and part != '.' and part != '..':
                path_parts.append(self.sanitize_filename(part))
        
        # 构建安全路径
        safe_path = os.path.join(base_path, *path_parts)
        
        # 确保路径在基础目录内
        try:
            safe_path = os.path.abspath(safe_path)
            base_path = os.path.abspath(base_path)
            
            if not safe_path.startswith(base_path):
                # 路径遍历攻击，使用安全的默认路径
                filename = self.sanitize_filename(os.path.basename(relative_path))
                safe_path = os.path.join(base_path, filename)
        except Exception as e:
            self.logger.warning(f"路径处理错误: {e}")
            filename = self.sanitize_filename(os.path.basename(relative_path))
            safe_path = os.path.join(base_path, filename)
        
        return safe_path
    
    def save_file(self, content: bytes, file_path: str, create_dirs: bool = True) -> bool:
        """保存文件到指定路径"""
        try:
            if create_dirs:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'wb') as f:
                f.write(content)
            
            self.logger.debug(f"文件已保存: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"保存文件失败 {file_path}: {e}")
            return False
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """获取文件信息"""
        try:
            stat = os.stat(file_path)
            file_path_obj = Path(file_path)
            
            # 获取MIME类型
            mime_type, _ = mimetypes.guess_type(file_path)
            
            # 计算文件哈希
            file_hash = self.calculate_file_hash(file_path)
            
            return {
                'name': file_path_obj.name,
                'path': str(file_path_obj),
                'size': stat.st_size,
                'mime_type': mime_type,
                'extension': file_path_obj.suffix.lower(),
                'created_time': datetime.fromtimestamp(stat.st_ctime),
                'modified_time': datetime.fromtimestamp(stat.st_mtime),
                'hash': file_hash,
                'type': self.config.get_file_type(file_path_obj.name)
            }
            
        except Exception as e:
            self.logger.error(f"获取文件信息失败 {file_path}: {e}")
            return {}
    
    def calculate_file_hash(self, file_path: str, algorithm: str = 'md5') -> str:
        """计算文件哈希值"""
        try:
            hash_obj = hashlib.new(algorithm)
            
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    hash_obj.update(chunk)
            
            return hash_obj.hexdigest()
            
        except Exception as e:
            self.logger.error(f"计算文件哈希失败 {file_path}: {e}")
            return ''
    
    def get_directory_size(self, directory: str) -> int:
        """获取目录总大小"""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(directory):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(file_path)
                    except (OSError, IOError):
                        continue
        except Exception as e:
            self.logger.error(f"计算目录大小失败 {directory}: {e}")
        
        return total_size
    
    def cleanup_directory(self, directory: str, max_age_hours: int = 24) -> int:
        """清理目录中的旧文件"""
        cleaned_count = 0
        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
        
        try:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        if os.path.getmtime(file_path) < cutoff_time:
                            os.remove(file_path)
                            cleaned_count += 1
                            self.logger.debug(f"已清理旧文件: {file_path}")
                    except Exception as e:
                        self.logger.warning(f"清理文件失败 {file_path}: {e}")
                
                # 清理空目录
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    try:
                        if not os.listdir(dir_path):
                            os.rmdir(dir_path)
                            self.logger.debug(f"已清理空目录: {dir_path}")
                    except Exception as e:
                        self.logger.warning(f"清理目录失败 {dir_path}: {e}")
        
        except Exception as e:
            self.logger.error(f"清理目录失败 {directory}: {e}")
        
        return cleaned_count


class ZipPackager:
    """ZIP打包器"""
    
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.logger = logging.getLogger(__name__)
    
    def create_zip(self, source_directory: str, zip_path: str, 
                   include_patterns: List[str] = None,
                   exclude_patterns: List[str] = None,
                   compression_level: int = 6) -> Tuple[bool, Dict[str, Any]]:
        """创建ZIP文件"""
        stats = {
            'total_files': 0,
            'total_size': 0,
            'compressed_size': 0,
            'compression_ratio': 0.0,
            'files_by_type': {},
            'errors': []
        }
        
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, 
                               compresslevel=compression_level) as zipf:
                
                for root, dirs, files in os.walk(source_directory):
                    for file in files:
                        file_path = os.path.join(root, file)
                        
                        # 检查包含/排除模式
                        if not self._should_include_file(file_path, include_patterns, exclude_patterns):
                            continue
                        
                        try:
                            # 计算相对路径
                            relative_path = os.path.relpath(file_path, source_directory)
                            
                            # 添加到ZIP
                            zipf.write(file_path, relative_path)
                            
                            # 更新统计信息
                            file_size = os.path.getsize(file_path)
                            file_type = self.config.get_file_type(file)
                            
                            stats['total_files'] += 1
                            stats['total_size'] += file_size
                            stats['files_by_type'][file_type] = stats['files_by_type'].get(file_type, 0) + 1
                            
                            self.logger.debug(f"已添加到ZIP: {relative_path}")
                            
                        except Exception as e:
                            error_msg = f"添加文件到ZIP失败 {file_path}: {e}"
                            self.logger.warning(error_msg)
                            stats['errors'].append(error_msg)
            
            # 计算压缩后大小和压缩比
            if os.path.exists(zip_path):
                stats['compressed_size'] = os.path.getsize(zip_path)
                if stats['total_size'] > 0:
                    stats['compression_ratio'] = 1 - (stats['compressed_size'] / stats['total_size'])
            
            self.logger.info(f"ZIP文件创建成功: {zip_path}")
            self.logger.info(f"压缩统计: {stats['total_files']} 文件, "
                           f"原始大小: {self._format_size(stats['total_size'])}, "
                           f"压缩后: {self._format_size(stats['compressed_size'])}, "
                           f"压缩比: {stats['compression_ratio']:.1%}")
            
            return True, stats
            
        except Exception as e:
            error_msg = f"创建ZIP文件失败 {zip_path}: {e}"
            self.logger.error(error_msg)
            stats['errors'].append(error_msg)
            return False, stats
    
    def extract_zip(self, zip_path: str, extract_to: str) -> Tuple[bool, List[str]]:
        """解压ZIP文件"""
        extracted_files = []
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zipf:
                # 检查ZIP文件完整性
                bad_file = zipf.testzip()
                if bad_file:
                    raise zipfile.BadZipFile(f"ZIP文件损坏: {bad_file}")
                
                # 解压所有文件
                for member in zipf.infolist():
                    try:
                        # 安全检查：防止路径遍历
                        if self._is_safe_path(member.filename):
                            zipf.extract(member, extract_to)
                            extracted_files.append(member.filename)
                            self.logger.debug(f"已解压: {member.filename}")
                        else:
                            self.logger.warning(f"跳过不安全的路径: {member.filename}")
                    
                    except Exception as e:
                        self.logger.warning(f"解压文件失败 {member.filename}: {e}")
            
            self.logger.info(f"ZIP文件解压成功: {len(extracted_files)} 个文件")
            return True, extracted_files
            
        except Exception as e:
            self.logger.error(f"解压ZIP文件失败 {zip_path}: {e}")
            return False, []
    
    def get_zip_info(self, zip_path: str) -> Dict[str, Any]:
        """获取ZIP文件信息"""
        info = {
            'file_count': 0,
            'total_size': 0,
            'compressed_size': 0,
            'compression_ratio': 0.0,
            'files': [],
            'created_time': None
        }
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zipf:
                for member in zipf.infolist():
                    file_info = {
                        'filename': member.filename,
                        'size': member.file_size,
                        'compressed_size': member.compress_size,
                        'date_time': datetime(*member.date_time),
                        'crc': member.CRC
                    }
                    
                    info['files'].append(file_info)
                    info['file_count'] += 1
                    info['total_size'] += member.file_size
                    info['compressed_size'] += member.compress_size
            
            # 计算压缩比
            if info['total_size'] > 0:
                info['compression_ratio'] = 1 - (info['compressed_size'] / info['total_size'])
            
            # 获取文件创建时间
            if os.path.exists(zip_path):
                info['created_time'] = datetime.fromtimestamp(os.path.getctime(zip_path))
            
        except Exception as e:
            self.logger.error(f"获取ZIP信息失败 {zip_path}: {e}")
        
        return info
    
    def _should_include_file(self, file_path: str, 
                           include_patterns: List[str] = None,
                           exclude_patterns: List[str] = None) -> bool:
        """检查文件是否应该被包含"""
        # 检查排除模式
        if exclude_patterns:
            for pattern in exclude_patterns:
                if re.search(pattern, file_path, re.IGNORECASE):
                    return False
        
        # 检查包含模式
        if include_patterns:
            for pattern in include_patterns:
                if re.search(pattern, file_path, re.IGNORECASE):
                    return True
            return False
        
        return True
    
    def _is_safe_path(self, path: str) -> bool:
        """检查路径是否安全（防止路径遍历）"""
        # 规范化路径
        normalized = os.path.normpath(path)
        
        # 检查是否包含危险的路径组件
        dangerous_patterns = ['..', '~', '//', '\\\\']
        for pattern in dangerous_patterns:
            if pattern in normalized:
                return False
        
        # 检查是否为绝对路径
        if os.path.isabs(normalized):
            return False
        
        return True
    
    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes == 0:
            return '0 B'
        
        size_names = ['B', 'KB', 'MB', 'GB', 'TB']
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f} {size_names[i]}"


class ProjectManager:
    """项目管理器"""
    
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.logger = logging.getLogger(__name__)
        self.file_handler = FileHandler(config)
        self.zip_packager = ZipPackager(config)
    
    def create_project(self, project_name: str, url: str) -> str:
        """创建新项目目录"""
        # 清理项目名称
        safe_name = self.file_handler.sanitize_filename(project_name)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        project_dir_name = f"{safe_name}_{timestamp}"
        
        project_path = os.path.join(self.config.DOWNLOADS_FOLDER, project_dir_name)
        
        try:
            os.makedirs(project_path, exist_ok=True)
            
            # 创建项目信息文件
            project_info = {
                'name': project_name,
                'url': url,
                'created_time': datetime.now().isoformat(),
                'version': self.config.APP_VERSION
            }
            
            info_path = os.path.join(project_path, 'project_info.json')
            with open(info_path, 'w', encoding='utf-8') as f:
                json.dump(project_info, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"项目目录已创建: {project_path}")
            return project_path
            
        except Exception as e:
            self.logger.error(f"创建项目目录失败: {e}")
            raise
    
    def finalize_project(self, project_path: str) -> Tuple[str, Dict[str, Any]]:
        """完成项目并创建ZIP包"""
        try:
            # 生成ZIP文件名
            project_name = os.path.basename(project_path)
            zip_filename = f"{project_name}.zip"
            zip_path = os.path.join(self.config.DOWNLOADS_FOLDER, zip_filename)
            
            # 创建ZIP包
            success, stats = self.zip_packager.create_zip(
                project_path, 
                zip_path,
                exclude_patterns=self.config.DEFAULT_EXCLUDE_PATTERNS
            )
            
            if success:
                # 更新项目信息
                self._update_project_info(project_path, stats)
                
                self.logger.info(f"项目已完成并打包: {zip_path}")
                return zip_path, stats
            else:
                raise Exception("ZIP打包失败")
                
        except Exception as e:
            self.logger.error(f"完成项目失败: {e}")
            raise
    
    def _update_project_info(self, project_path: str, stats: Dict[str, Any]):
        """更新项目信息"""
        info_path = os.path.join(project_path, 'project_info.json')
        
        try:
            # 读取现有信息
            if os.path.exists(info_path):
                with open(info_path, 'r', encoding='utf-8') as f:
                    project_info = json.load(f)
            else:
                project_info = {}
            
            # 更新统计信息
            project_info.update({
                'completed_time': datetime.now().isoformat(),
                'stats': stats
            })
            
            # 保存更新后的信息
            with open(info_path, 'w', encoding='utf-8') as f:
                json.dump(project_info, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            self.logger.warning(f"更新项目信息失败: {e}")
    
    def cleanup_old_projects(self, max_age_hours: int = 24) -> int:
        """清理旧项目"""
        cleaned_count = 0
        
        try:
            # 清理项目目录
            cleaned_count += self.file_handler.cleanup_directory(
                self.config.DOWNLOADS_FOLDER, max_age_hours
            )
            
            # 清理临时文件
            cleaned_count += self.file_handler.cleanup_directory(
                self.config.TEMP_FOLDER, max_age_hours // 2  # 临时文件更快清理
            )
            
            self.logger.info(f"已清理 {cleaned_count} 个旧文件")
            
        except Exception as e:
            self.logger.error(f"清理旧项目失败: {e}")
        
        return cleaned_count
    
    def get_project_stats(self) -> Dict[str, Any]:
        """获取项目统计信息"""
        stats = {
            'total_projects': 0,
            'total_size': 0,
            'disk_usage': {
                'downloads': 0,
                'temp': 0,
                'logs': 0
            }
        }
        
        try:
            # 统计下载目录
            downloads_path = Path(self.config.DOWNLOADS_FOLDER)
            if downloads_path.exists():
                stats['disk_usage']['downloads'] = self.file_handler.get_directory_size(
                    str(downloads_path)
                )
                
                # 统计项目数量
                for item in downloads_path.iterdir():
                    if item.is_dir():
                        stats['total_projects'] += 1
            
            # 统计临时目录
            temp_path = Path(self.config.TEMP_FOLDER)
            if temp_path.exists():
                stats['disk_usage']['temp'] = self.file_handler.get_directory_size(
                    str(temp_path)
                )
            
            # 统计日志目录
            logs_path = Path(self.config.LOGS_FOLDER)
            if logs_path.exists():
                stats['disk_usage']['logs'] = self.file_handler.get_directory_size(
                    str(logs_path)
                )
            
            stats['total_size'] = sum(stats['disk_usage'].values())
            
        except Exception as e:
            self.logger.error(f"获取项目统计失败: {e}")
        
        return stats