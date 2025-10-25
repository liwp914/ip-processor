import os
import re
import csv
import ipaddress
from pathlib import Path
import socket
import subprocess
import platform
import concurrent.futures
import threading
from tqdm import tqdm
import time
import configparser
import requests
import json
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('ip_processor.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

def load_config():
    """加载配置文件，支持环境变量替换"""
    config = configparser.ConfigParser()
    
    # 设置默认配置
    config['IP_CHECK'] = {
        'ENABLE_IP_CHECK': 'true',
        'CHECK_METHOD': 'ping',
        'CHECK_PORT': '443',
        'CHECK_TIMEOUT': '2',
        'CHECK_THREADS': '50'
    }
    config['OUTPUT'] = {
        'OUTPUT_DIR': 'output'
    }
    config['INPUT'] = {
        'INPUT_DIR': 'ips'
    }
    config['cloudflare'] = {
        'enable': 'false',
        'api_token': '',
        'zone_id': '',
        'domain': '',
        'record_name': 'ip',
        'record_type': 'A',
        'ttl': '1',
        'proxied': 'false',
        'max_records_per_line': '5',
        'upload_dir': 'output',
        'upload_files': 'all'
    }
    
    # 读取配置文件
    if os.path.exists('config.ini'):
        config.read('config.ini', encoding='utf-8')
        logger.info("已加载配置文件: config.ini")
        
        # 环境变量替换
        for section in config.sections():
            for key in config[section]:
                value = config[section][key]
                # 检查是否是环境变量格式 ${VAR_NAME}
                if value.startswith('${') and value.endswith('}'):
                    env_var_name = value[2:-1]  # 提取变量名
                    env_value = os.getenv(env_var_name, '')  # 从环境变量获取值
                    if env_value:
                        config[section][key] = env_value
                        logger.debug(f"替换环境变量: {env_var_name} -> {env_value[:10]}...")
                    else:
                        logger.warning(f"环境变量未设置: {env_var_name}")
    else:
        logger.info("未找到配置文件，使用默认配置")
        # 创建带注释的默认配置文件
        create_config_file_with_comments()
        config.read('config.ini', encoding='utf-8')
        logger.info("已创建带注释的默认配置文件: config.ini")
    
    return config

def create_config_file_with_comments():
    """创建带注释的配置文件"""
    config_content = """# IP处理工具配置文件
# 请根据您的需求修改以下配置

[IP_CHECK]
# 是否启用IP检测功能 (true/false)
ENABLE_IP_CHECK = true

# IP检测方法 (ping/port)
# ping: 使用ping命令检测IP是否可达
# port: 检测指定端口是否开放
CHECK_METHOD = port

# 如果使用端口检测，指定要检测的端口号
CHECK_PORT = 443

# 检测超时时间（秒）
CHECK_TIMEOUT = 2

# 并发检测线程数
CHECK_THREADS = 50

[INPUT]
# 输入目录，存放原始IP文件的目录
INPUT_DIR = ips

[OUTPUT]
# 输出目录，处理后的文件将保存到此目录
OUTPUT_DIR = output

[cloudflare]
# 是否启用Cloudflare DNS上传功能 (true/false)
enable = false

# Cloudflare API Token
# 需要在Cloudflare控制台生成具有DNS编辑权限的Token
api_token = ${CF_API_TOKEN}

# Cloudflare区域ID (Zone ID)
# 在Cloudflare域名概述页面可以找到
zone_id = ${CF_ZONE_ID}

# 主域名，用于创建DNS记录
# 例如: example.com
domain = ${CF_DOMAIN}

# DNS记录名称前缀
# 如果设置为"ip"，则记录名为 ip-标签.域名
# 如果留空，则记录名为 标签.域名
record_name = ip

# DNS记录类型 (通常使用A记录)
record_type = A

# DNS记录TTL值
# 1 = 自动，或设置为60-86400之间的值
ttl = 1

# 是否通过Cloudflare代理 (true/false)
# true: 流量经过Cloudflare CDN
# false: 流量不经过Cloudflare，直接指向源服务器
proxied = false

# 每个标签上传的最大IP数量
max_records_per_line = 5

# 要上传的文件所在目录
upload_dir = output

# 要上传的文件列表
# all: 上传所有文件
# 或指定文件名，如: HK,US,JP (不需要.txt扩展名)
upload_files = all
"""
    
    with open('config.ini', 'w', encoding='utf-8') as f:
        f.write(config_content)

def validate_ip(ip_str):
    """验证IP地址的有效性"""
    try:
        ipaddress.ip_address(ip_str)
        return True
    except ValueError:
        return False

def check_ip_port(ip, port, timeout):
    """检测IP端口是否开放"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            result = s.connect_ex((ip, port))
            return result == 0
    except Exception:
        return False

def check_ip_ping(ip, timeout):
    """检测IP是否可ping通"""
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    command = ['ping', param, '1', '-w', str(int(timeout * 1000)), ip]
    
    try:
        with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
            _, _ = process.communicate()
            return process.returncode == 0
    except Exception:
        return False

def check_ip(ip, port, config):
    """根据配置检测IP"""
    enable_check = config.getboolean('IP_CHECK', 'ENABLE_IP_CHECK')
    if not enable_check:
        return True
    
    check_method = config.get('IP_CHECK', 'CHECK_METHOD')
    timeout = config.getfloat('IP_CHECK', 'CHECK_TIMEOUT')
    
    if check_method == 'port':
        check_port = config.getint('IP_CHECK', 'CHECK_PORT')
        return check_ip_port(ip, port or check_port, timeout)
    elif check_method == 'ping':
        return check_ip_ping(ip, timeout)
    else:
        logger.warning(f"未知的检测方法: {check_method}, 默认使用ping检测")
        return check_ip_ping(ip, timeout)

def check_ips(ip_list, config):
    """批量检测IP可用性"""
    enable_check = config.getboolean('IP_CHECK', 'ENABLE_IP_CHECK')
    if not enable_check:
        logger.info("IP检测已禁用，跳过检测")
        return [True] * len(ip_list)
    
    check_method = config.get('IP_CHECK', 'CHECK_METHOD')
    threads = config.getint('IP_CHECK', 'CHECK_THREADS')
    
    logger.info(f"开始检测 {len(ip_list)} 个IP的可用性 (方法: {check_method})")
    
    valid_results = []
    lock = threading.Lock()
    
    def check_and_record(ip_info):
        ip = ip_info['ip']
        port = ip_info.get('port')
        result = check_ip(ip, port, config)
        with lock:
            valid_results.append((ip_info, result))
    
    # 准备IP信息列表
    ip_infos = []
    for item in ip_list:
        if ':' in item:
            # 处理IP:端口格式
            ip_part, rest = item.split(':', 1)
            ip = ip_part
            port = int(rest.split('#')[0]) if '#' in rest else config.getint('IP_CHECK', 'CHECK_PORT')
        else:
            # 处理纯IP格式
            ip = item.split('#')[0]
            port = config.getint('IP_CHECK', 'CHECK_PORT')
        
        ip_infos.append({'ip': ip, 'port': port, 'original': item})
    
    # 多线程检测
    with tqdm(total=len(ip_infos), desc="检测IP可用性") as pbar:
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            futures = {executor.submit(check_and_record, ip_info): ip_info for ip_info in ip_infos}
            
            for future in concurrent.futures.as_completed(futures):
                pbar.update(1)
    
    # 按原始顺序返回结果
    result_map = {info['original']: result for info, result in valid_results}
    return [result_map.get(item, False) for item in ip_list]

def extract_ips_from_txt(file_path, filename_without_ext):
    """从txt文件中提取IP地址"""
    results = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    # 匹配IP地址格式
                    ip_match = re.match(r'(\d+\.\d+\.\d+\.\d+)', line)
                    if ip_match:
                        ip = ip_match.group(1)
                        if validate_ip(ip):
                            # 使用不带扩展名的文件名作为标签（保持原样，不翻译）
                            results.append(f"{ip}#{filename_without_ext}")
    except Exception as e:
        logger.error(f"读取txt文件 {file_path} 时出错: {e}")
    return results

def find_region_column_index(headers):
    """动态查找国家地区代码列的索引"""
    # 可能的列名列表（按优先级排序）
    possible_names = [
        "源IP位置", "国家", "地区", "Country", "Region", 
        "国家代码", "地区代码", "Country Code", "Region Code"
    ]
    
    # 查找匹配的列名
    for i, header in enumerate(headers):
        header_clean = header.strip().lower()
        for name in possible_names:
            if name.lower() in header_clean:
                logger.info(f"找到地区代码列: '{header}' (索引: {i})")
                return i
    
    # 如果没有找到匹配的列，尝试基于常见模式猜测
    for i, header in enumerate(headers):
        header_clean = header.strip().lower()
        # 检查是否包含地区相关的关键词
        if any(keyword in header_clean for keyword in ['地区', '国家', 'country', 'region', '位置', 'location']):
            logger.info(f"猜测地区代码列: '{header}' (索引: {i})")
            return i
    
    # 如果还是没找到，使用默认的第5列（索引4）
    logger.warning(f"未找到地区代码列，使用默认索引4。表头: {headers}")
    return 4 if len(headers) > 4 else None

def extract_ips_from_csv(file_path, filename_without_ext):
    """从csv文件中提取IP地址、端口和国家地区代码"""
    results = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # 尝试不同的分隔符
            sample = f.read(1024)
            f.seek(0)
            
            # 检测分隔符
            try:
                dialect = csv.Sniffer().sniff(sample)
                has_header = csv.Sniffer().has_header(sample)
            except:
                # 如果检测失败，使用默认的逗号分隔符
                dialect = csv.excel
                has_header = False
            
            reader = csv.reader(f, dialect)
            
            # 如果有表头，跳过第一行
            if has_header:
                headers = next(reader)
                # 动态查找国家地区代码列的索引
                region_index = find_region_column_index(headers)
                logger.info(f"检测到表头: {headers}, 地区代码列索引: {region_index}")
            else:
                headers = []
                region_index = 4  # 默认使用第5列作为地区代码
            
            for row_num, row in enumerate(reader, 1 if has_header else 0):
                if len(row) < 2:  # 确保有IP和端口列
                    continue
                
                ip_str = str(row[0]).strip()
                port_str = str(row[1]).strip()
                
                # 获取国家地区代码
                region_code = filename_without_ext  # 默认使用文件名
                if region_index is not None and len(row) > region_index:
                    region_code = str(row[region_index]).strip()
                    # 如果地区代码为空，使用文件名
                    if not region_code:
                        region_code = filename_without_ext
                
                if ip_str and validate_ip(ip_str):
                    if port_str and port_str.split()[0].isdigit():  # 只取端口数字部分
                        port = port_str.split()[0]
                        results.append(f"{ip_str}:{port}#{region_code}")
                    else:
                        results.append(f"{ip_str}#{region_code}")
                else:
                    logger.warning(f"第{row_num}行IP地址无效: {ip_str}")
                    
    except Exception as e:
        logger.error(f"读取csv文件 {file_path} 时出错: {e}")
    return results

class CloudflareManager:
    """Cloudflare DNS记录管理器"""
    
    def __init__(self, config):
        self.enable = config.getboolean('cloudflare', 'enable')
        if not self.enable:
            logger.info("Cloudflare功能未启用")
            return
            
        self.api_token = config.get('cloudflare', 'api_token')
        self.zone_id = config.get('cloudflare', 'zone_id')
        self.domain = config.get('cloudflare', 'domain')
        
        # 检查必要的配置是否设置
        if not self.api_token:
            logger.error("Cloudflare API Token未设置，请检查config.ini或环境变量")
            self.enable = False
            return
            
        if not self.zone_id:
            logger.error("Cloudflare Zone ID未设置，请检查config.ini或环境变量")
            self.enable = False
            return
            
        if not self.domain:
            logger.error("Cloudflare域名未设置，请检查config.ini或环境变量")
            self.enable = False
            return
        
        self.record_name = config.get('cloudflare', 'record_name')
        self.record_type = config.get('cloudflare', 'record_type')
        self.ttl = config.getint('cloudflare', 'ttl')
        self.proxied = config.getboolean('cloudflare', 'proxied')
        self.max_records = config.getint('cloudflare', 'max_records_per_line')
        self.upload_dir = config.get('cloudflare', 'upload_dir')
        self.upload_files = config.get('cloudflare', 'upload_files')
        
        self.headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json'
        }
        
        logger.info("Cloudflare管理器初始化完成")
        logger.info(f"域名: {self.domain}")
        logger.info(f"Zone ID: {self.zone_id[:10]}...")
    
    def get_existing_records(self, subdomain):
        """获取现有的DNS记录"""
        if not self.enable:
            return []
            
        full_name = f'{subdomain}.{self.domain}'
        url = f'https://api.cloudflare.com/client/v4/zones/{self.zone_id}/dns_records'
        params = {
            'type': self.record_type,
            'name': full_name
        }
        
        try:
            logger.debug(f"获取DNS记录: {full_name}")
            response = requests.get(url, headers=self.headers, params=params)
            if response.status_code == 200:
                result = response.json()
                if result['success']:
                    logger.debug(f"成功获取 {len(result['result'])} 条记录")
                    return result['result']
                else:
                    errors = result.get('errors', [])
                    error_messages = [f"{e.get('code', '未知错误')}: {e.get('message', '无详细信息')}" for e in errors]
                    logger.error(f"获取DNS记录失败: {', '.join(error_messages)}")
            else:
                logger.error(f"HTTP错误: {response.status_code}")
                logger.error(f"响应内容: {response.text}")
        except Exception as e:
            logger.error(f"获取DNS记录时出错: {e}")
            
        return []
    
    def create_dns_record(self, subdomain, ip_address):
        """创建DNS记录"""
        if not self.enable:
            return False
            
        # Cloudflare要求TTL为1（自动）或在60-86400之间
        ttl_value = self.ttl
        if self.proxied:
            # 如果启用了代理，TTL必须为1
            ttl_value = 1
        elif ttl_value < 60 or ttl_value > 86400:
            # 确保TTL在有效范围内
            ttl_value = 1
        
        full_name = f'{subdomain}.{self.domain}'
        record_data = {
            'type': self.record_type,
            'name': full_name,
            'content': ip_address,
            'ttl': ttl_value,
            'proxied': self.proxied
        }
        
        url = f'https://api.cloudflare.com/client/v4/zones/{self.zone_id}/dns_records'
        
        try:
            logger.debug(f"创建DNS记录: {full_name} -> {ip_address}")
            response = requests.post(url, headers=self.headers, json=record_data)
            if response.status_code == 200:
                result = response.json()
                if result['success']:
                    logger.info(f"成功创建记录: {full_name} -> {ip_address}")
                    return True
                else:
                    # 添加详细的错误信息
                    errors = result.get('errors', [])
                    error_messages = [f"{e.get('code', '未知错误')}: {e.get('message', '无详细信息')}" for e in errors]
                    logger.error(f"创建记录失败: {', '.join(error_messages)}")
                    logger.error(f"请求数据: {json.dumps(record_data)}")
            else:
                # 添加详细的错误信息
                logger.error(f"HTTP错误: {response.status_code}")
                logger.error(f"响应内容: {response.text}")
                logger.error(f"请求数据: {json.dumps(record_data)}")
        except Exception as e:
            logger.error(f"创建DNS记录时出错: {e}")
            logger.error(f"请求数据: {json.dumps(record_data)}")
            
        return False
    
    def update_dns_record(self, record_id, subdomain, ip_address):
        """更新DNS记录"""
        if not self.enable:
            return False
            
        # Cloudflare要求TTL为1（自动）或在60-86400之间
        ttl_value = self.ttl
        if self.proxied:
            # 如果启用了代理，TTL必须为1
            ttl_value = 1
        elif ttl_value < 60 or ttl_value > 86400:
            # 确保TTL在有效范围内
            ttl_value = 1
        
        full_name = f'{subdomain}.{self.domain}'
        record_data = {
            'type': self.record_type,
            'name': full_name,
            'content': ip_address,
            'ttl': ttl_value,
            'proxied': self.proxied
        }
        
        url = f'https://api.cloudflare.com/client/v4/zones/{self.zone_id}/dns_records/{record_id}'
        
        try:
            logger.debug(f"更新DNS记录: {full_name} -> {ip_address}")
            response = requests.put(url, headers=self.headers, json=record_data)
            if response.status_code == 200:
                result = response.json()
                if result['success']:
                    logger.info(f"成功更新记录: {full_name} -> {ip_address}")
                    return True
                else:
                    # 添加详细的错误信息
                    errors = result.get('errors', [])
                    error_messages = [f"{e.get('code', '未知错误')}: {e.get('message', '无详细信息')}" for e in errors]
                    logger.error(f"更新记录失败: {', '.join(error_messages)}")
                    logger.error(f"请求数据: {json.dumps(record_data)}")
            else:
                # 添加详细的错误信息
                logger.error(f"HTTP错误: {response.status_code}")
                logger.error(f"响应内容: {response.text}")
                logger.error(f"请求数据: {json.dumps(record_data)}")
        except Exception as e:
            logger.error(f"更新DNS记录时出错: {e}")
            logger.error(f"请求数据: {json.dumps(record_data)}")
            
        return False
    
    def delete_dns_record(self, record_id):
        """删除DNS记录"""
        if not self.enable:
            return False
            
        url = f'https://api.cloudflare.com/client/v4/zones/{self.zone_id}/dns_records/{record_id}'
        
        try:
            logger.debug(f"删除DNS记录: {record_id}")
            response = requests.delete(url, headers=self.headers)
            if response.status_code == 200:
                result = response.json()
                if result['success']:
                    logger.info(f"成功删除记录: {record_id}")
                    return True
                else:
                    # 添加详细的错误信息
                    errors = result.get('errors', [])
                    error_messages = [f"{e.get('code', '未知错误')}: {e.get('message', '无详细信息')}" for e in errors]
                    logger.error(f"删除记录失败: {', '.join(error_messages)}")
            else:
                # 添加详细的错误信息
                logger.error(f"HTTP错误: {response.status_code}")
                logger.error(f"响应内容: {response.text}")
        except Exception as e:
            logger.error(f"删除DNS记录时出错: {e}")
            
        return False
    
    def upload_ips_to_cloudflare(self):
        """上传IP到Cloudflare"""
        if not self.enable:
            logger.info("Cloudflare功能未启用，跳过上传")
            return
            
        upload_path = Path(self.upload_dir)
        if not upload_path.exists():
            logger.error(f"上传目录不存在: {upload_path}")
            return
        
        logger.info(f"开始从目录 {upload_path} 上传IP到Cloudflare")
        
        # 获取要上传的文件列表
        files_to_upload = self.get_files_to_upload()
        
        if not files_to_upload:
            logger.info("没有找到要上传的文件")
            return
        
        logger.info(f"准备上传 {len(files_to_upload)} 个文件: {', '.join([f.stem for f in files_to_upload])}")
        
        # 遍历指定文件
        for file_path in files_to_upload:
            if file_path.is_file() and file_path.suffix.lower() == '.txt':
                self.process_single_file(file_path)
                # 添加延迟，避免请求过于频繁
                time.sleep(1)  # 1秒延迟
    
    def get_files_to_upload(self):
        """获取要上传的文件列表"""
        upload_path = Path(self.upload_dir)
        
        # 获取所有txt文件
        all_txt_files = list(upload_path.glob("*.txt"))
        
        # 如果设置为all，上传所有文件
        if self.upload_files.lower() == 'all':
            return all_txt_files
        
        # 否则，只上传指定的文件
        specified_files = [f.strip() for f in self.upload_files.split(',') if f.strip()]
        files_to_upload = []
        
        for filename in specified_files:
            # 尝试匹配文件（不区分大小写）
            matched_files = [f for f in all_txt_files if f.stem.lower() == filename.lower()]
            if matched_files:
                files_to_upload.extend(matched_files)
            else:
                logger.warning(f"未找到文件: {filename}.txt")
        
        return files_to_upload
    
    def process_single_file(self, file_path):
        """处理单个文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f if line.strip()]
            
            if not lines:
                logger.warning(f"文件为空: {file_path}")
                return
            
            # 提取IP和标签
            ip_data = []
            for line in lines:
                if '#' in line:
                    ip_part, tag = line.split('#', 1)
                    ip_match = re.match(r'(\d+\.\d+\.\d+\.\d+)', ip_part)
                    if ip_match:
                        ip = ip_match.group(1)
                        if validate_ip(ip):
                            ip_data.append((ip, tag))
            
            if not ip_data:
                logger.warning(f"文件中没有有效的IP: {file_path}")
                return
            
            # 只取前max_records个IP
            ip_data = ip_data[:self.max_records]
            
            # 按标签分组（同一个标签的IP放在一起）
            tag_groups = {}
            for ip, tag in ip_data:
                if tag not in tag_groups:
                    tag_groups[tag] = []
                tag_groups[tag].append(ip)
            
            # 为每个标签创建/更新DNS记录
            for tag, ips in tag_groups.items():
                self.process_tag_ips(tag, ips, file_path.stem)
                
        except Exception as e:
            logger.error(f"处理文件 {file_path} 时出错: {e}")
    
    def process_tag_ips(self, tag, ips, filename):
        """处理单个标签的IP"""
        # 生成子域名，添加record_name前缀（如果设置）
        if self.record_name and self.record_name.strip():
            subdomain_part = f"{self.record_name}-{tag}"
        else:
            subdomain_part = tag
            
        # 清理子域名，确保适合作为子域名
        subdomain = self.sanitize_subdomain(subdomain_part)
        
        # 获取现有记录
        existing_records = self.get_existing_records(subdomain)
        
        # 创建记录ID到IP的映射
        existing_ip_map = {record['id']: record['content'] for record in existing_records}
        
        # 删除不在新IP列表中的记录
        for record_id, ip_content in list(existing_ip_map.items()):
            if ip_content not in ips:
                self.delete_dns_record(record_id)
                time.sleep(0.5)
        
        # 重新获取现有记录（因为可能已删除部分记录）
        existing_records = self.get_existing_records(subdomain)
        existing_ips = {record['content'] for record in existing_records}
        
        # 添加不在现有记录中的新IP
        for ip in ips:
            if ip not in existing_ips:
                self.create_dns_record(subdomain, ip)
                time.sleep(0.5)
        
        logger.info(f"处理完成: 标签 '{tag}' -> 子域名 '{subdomain}.{self.domain}', 上传 {len(ips)} 个IP")
    
    def sanitize_subdomain(self, subdomain):
        """清理子域名，使其适合作为子域名"""
        # 移除非法字符，只保留字母、数字、连字符
        cleaned = re.sub(r'[^a-zA-Z0-9-]', '-', subdomain)
        # 确保不以连字符开头或结尾
        cleaned = cleaned.strip('-')
        # 如果为空，使用默认名称
        if not cleaned:
            cleaned = 'ip'
        # 限制长度
        if len(cleaned) > 63:
            cleaned = cleaned[:63]
        
        # 确保子域名不以数字开头
        if cleaned and cleaned[0].isdigit():
            cleaned = 'cf-' + cleaned
        
        return cleaned.lower()  # 子域名通常使用小写

def process_files(config):
    """处理ips目录下的所有文件"""
    # 创建目录
    input_dir = Path(config.get('INPUT', 'INPUT_DIR'))
    output_dir = Path(config.get('OUTPUT', 'OUTPUT_DIR'))
    output_dir.mkdir(exist_ok=True)
    
    logger.info(f"输入目录: {input_dir.absolute()}")
    logger.info(f"输出目录: {output_dir.absolute()}")
    
    if not input_dir.exists():
        logger.error(f"{input_dir} 目录不存在，请创建目录并放入文件")
        # 列出当前目录内容用于调试
        logger.info("当前目录内容:")
        for item in Path('.').iterdir():
            logger.info(f"  {item.name}")
        return
    
    # 初始化Cloudflare管理器
    cf_manager = CloudflareManager(config)
    
    # 检查输入目录中的文件
    file_count = 0
    for file_path in input_dir.iterdir():
        if file_path.is_file():
            file_count += 1
            logger.info(f"找到文件: {file_path.name}")
    
    if file_count == 0:
        logger.warning(f"输入目录 {input_dir} 中没有找到任何文件")
        # 创建示例文件
        example_file = input_dir / "example.txt"
        example_file.write_text("8.8.8.8\n1.1.1.1\n", encoding='utf-8')
        logger.info(f"已创建示例文件: {example_file}")
    
    # 遍历输入目录下的所有文件
    for file_path in input_dir.iterdir():
        if file_path.is_file():
            filename_without_ext = file_path.stem  # 获取不带扩展名的文件名
            results = []
            
            logger.info(f"处理文件: {file_path.name}")
            
            if file_path.suffix.lower() == '.txt':
                results = extract_ips_from_txt(file_path, filename_without_ext)
            elif file_path.suffix.lower() == '.csv':
                results = extract_ips_from_csv(file_path, filename_without_ext)
            else:
                logger.info(f"跳过不支持的文件类型: {file_path}")
                continue
            
            logger.info(f"从文件中提取到 {len(results)} 个IP")
            
            # 检测IP可用性
            if results and config.getboolean('IP_CHECK', 'ENABLE_IP_CHECK'):
                valid_results = check_ips(results, config)
                # 只保留有效的IP
                filtered_results = [result for result, valid in zip(results, valid_results) if valid]
                logger.info(f"IP检测完成: {len(filtered_results)}/{len(results)} 个IP有效")
                results = filtered_results
            
            # 写入输出文件
            if results:
                output_file = output_dir / f"{file_path.stem}.txt"
                try:
                    with open(output_file, 'w', encoding='utf-8') as f:
                        for result in results:
                            f.write(result + '\n')
                    logger.info(f"成功处理文件: {file_path.name} -> {output_file.name} (找到 {len(results)} 个IP)")
                except Exception as e:
                    logger.error(f"写入文件 {output_file} 时出错: {e}")
            else:
                logger.info(f"文件 {file_path.name} 中没有找到有效的IP地址")
    
    # 上传到Cloudflare
    cf_manager.upload_ips_to_cloudflare()

def print_config_summary(config):
    """打印配置摘要"""
    logger.info("=" * 50)
    logger.info("IP提取和检测工具")
    logger.info("配置参数:")
    logger.info(f"  输入目录: {config.get('INPUT', 'INPUT_DIR')}")
    logger.info(f"  输出目录: {config.get('OUTPUT', 'OUTPUT_DIR')}")
    logger.info(f"  IP检测启用: {config.getboolean('IP_CHECK', 'ENABLE_IP_CHECK')}")
    if config.getboolean('IP_CHECK', 'ENABLE_IP_CHECK'):
        logger.info(f"  检测方法: {config.get('IP_CHECK', 'CHECK_METHOD')}")
        if config.get('IP_CHECK', 'CHECK_METHOD') == 'port':
            logger.info(f"  检测端口: {config.getint('IP_CHECK', 'CHECK_PORT')}")
        logger.info(f"  检测超时: {config.getfloat('IP_CHECK', 'CHECK_TIMEOUT')}秒")
        logger.info(f"  检测线程数: {config.getint('IP_CHECK', 'CHECK_THREADS')}")
    
    # Cloudflare配置
    if config.getboolean('cloudflare', 'enable'):
        logger.info("  Cloudflare配置:")
        logger.info(f"    域名: {config.get('cloudflare', 'domain')}")
        # 隐藏敏感信息的部分显示
        api_token = config.get('cloudflare', 'api_token')
        zone_id = config.get('cloudflare', 'zone_id')
        logger.info(f"    API Token: {'已设置' if api_token else '未设置'}")
        logger.info(f"    Zone ID: {'已设置' if zone_id else '未设置'}")
        logger.info(f"    记录名称前缀: '{config.get('cloudflare', 'record_name')}'")
        logger.info(f"    记录类型: {config.get('cloudflare', 'record_type')}")
        logger.info(f"    每行最大记录数: {config.getint('cloudflare', 'max_records_per_line')}")
        logger.info(f"    上传目录: {config.get('cloudflare', 'upload_dir')}")
        logger.info(f"    上传文件: {config.get('cloudflare', 'upload_files')}")
    else:
        logger.info("  Cloudflare功能: 禁用")
    
    logger.info("=" * 50)

if __name__ == "__main__":
    # 加载配置
    config = load_config()
    
    # 打印配置摘要
    print_config_summary(config)
    
    # 处理文件
    process_files(config)
    logger.info("处理完成！请检查output目录下的文件。")
