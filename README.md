IP处理工具使用说明
功能概述
这是一个强大的IP地址处理工具，主要功能包括：

从TXT/CSV文件中提取IP地址

检测IP的可用性（支持Ping和端口检测）

自动上传有效的IP到Cloudflare DNS

支持多线程并发处理

生成详细的处理日志

环境要求
系统要求
Windows/Linux/macOS

Python 3.7 或更高版本

Python依赖包
bash
复制
pip install requests tqdm
快速开始
1. 下载和准备
将Python脚本保存为 ip_processor.py

2. 首次运行配置
首次运行会自动创建配置文件：

bash
复制
python ip_processor.py
3. 目录结构准备
程序会自动创建以下目录结构：

复制
项目目录/
├── ip_processor.py      # 主程序文件
├── config.ini          # 配置文件（自动生成）
├── ips/                # 输入目录（存放原始IP文件）
│   ├── HK.txt          # 示例：香港IP文件
│   ├── US.csv          # 示例：美国IP文件
│   └── ...
├── output/             # 输出目录（处理结果）
└── ip_processor.log    # 日志文件
配置文件详解
基本配置说明
编辑 config.ini文件进行配置：

ini
复制
[IP_CHECK]
# IP检测功能开关
ENABLE_IP_CHECK = true

# 检测方法：ping（ICMP检测）或 port（TCP端口检测）
CHECK_METHOD = port

# 端口检测时使用的端口号
CHECK_PORT = 443

# 检测超时时间（秒）
CHECK_TIMEOUT = 2

# 并发检测线程数
CHECK_THREADS = 50

[INPUT]
# 输入文件存放目录
INPUT_DIR = ips

[OUTPUT]
# 输出文件存放目录
OUTPUT_DIR = output
Cloudflare配置（可选）
如需使用Cloudflare自动上传功能：

ini
复制
[cloudflare]
# 启用Cloudflare功能
enable = true

# 通过环境变量设置敏感信息（推荐）
api_token = ${CF_API_TOKEN}
zone_id = ${CF_ZONE_ID}
domain = ${CF_DOMAIN}

# 或直接在配置文件中设置（不推荐，因为会暴露敏感信息）
# api_token = your_api_token_here
# zone_id = your_zone_id_here
# domain = your-domain.com

# DNS记录配置
record_name = ip      # 记录名前缀，如设置为ip则生成 ip-HK.your-domain.com
record_type = A       # 记录类型
ttl = 1               # TTL值（1=自动）
proxied = false       # 是否通过Cloudflare代理
max_records_per_line = 5    # 每个标签最大IP数量
upload_dir = output         # 上传文件目录
upload_files = all          # 上传文件列表（all或指定文件名，如：HK,US）
环境变量设置（推荐用于敏感信息）
Windows（命令提示符）
cmd
复制
set CF_API_TOKEN=your_cloudflare_api_token
set CF_ZONE_ID=your_zone_id
set CF_DOMAIN=your-domain.com
Windows（PowerShell）
powershell
复制
$env:CF_API_TOKEN="your_cloudflare_api_token"
$env:CF_ZONE_ID="your_zone_id"
$env:CF_DOMAIN="your-domain.com"
Linux/macOS
bash
复制
export CF_API_TOKEN=your_cloudflare_api_token
export CF_ZONE_ID=your_zone_id
export CF_DOMAIN=your-domain.com
输入文件格式
TXT文件格式
每行一个IP地址，可包含端口和标签：

复制
1.1.1.1
8.8.8.8:443
192.168.1.1:8080#香港节点
CSV文件格式
第一列为IP地址，第二列为端口（可选）：

csv
复制
ip,port,description
1.1.1.1,443,主要节点
8.8.8.8,53,DNS服务器
运行步骤
1. 准备输入文件
在 ips目录中放置IP文件：

文件名将作为标签名称（如：HK.txt的标签为 HK）

支持 .txt和 .csv格式

2. 运行程序
bash
复制
python ip_processor.py
3. 查看结果
处理后的文件保存在 output目录

详细日志查看 ip_processor.log

控制台会显示实时进度和结果摘要

Cloudflare DNS上传功能
功能说明
自动将有效的IP上传到Cloudflare DNS

为每个地区/标签创建对应的子域名

支持记录的新增、更新和删除

生成的DNS记录示例
假设有以下文件：

HK.txt→ 生成子域名：ip-HK.your-domain.com

US.txt→ 生成子域名：ip-US.your-domain.com

权限要求
Cloudflare API Token需要以下权限：

Zone:Zone:Read

Zone:DNS:Edit

高级用法
批量处理示例
bash
复制
# 一次性处理所有IP文件
python ip_processor.py

# 只处理特定文件（通过配置upload_files设置）
定时任务（Linux/macOS）
使用crontab设置定时任务：

bash
复制
# 每天凌晨2点执行
0 2 * * * cd /path/to/script && python ip_processor.py
日志查看
bash
复制
# 实时查看日志
tail -f ip_processor.log

# 查看错误信息
grep -i error ip_processor.log
故障排除
常见问题
​输入目录不存在​

复制
错误：ips目录不存在
解决：自动创建ips目录，或手动创建并放入IP文件
​Cloudflare API错误​

复制
错误：API Token无效或权限不足
解决：检查Token权限和Zone ID是否正确
​IP检测全部失败​

复制
错误：所有IP检测都失败
解决：检查网络连接，调整超时时间或检测方法
​文件编码问题​

复制
错误：读取文件时出错
解决：确保文件使用UTF-8编码
调试模式
如需更详细日志，可修改日志级别：

python
下载
复制
运行
logging.basicConfig(level=logging.DEBUG, ...)
输出示例
控制台输出
复制
2024-01-15 10:30:00 - INFO - 开始处理文件: HK.txt
2024-01-15 10:30:05 - INFO - 从文件中提取到 100 个IP
2024-01-15 10:30:20 - INFO - IP检测完成: 85/100 个IP有效
2024-01-15 10:30:21 - INFO - 成功处理文件: HK.txt -> HK.txt (找到 85 个IP)
输出文件格式
复制
1.1.1.1:443#HK
8.8.8.8:443#HK
...
注意事项
​API限制​：Cloudflare API有调用频率限制，程序已内置延迟

​文件备份​：重要IP文件请定期备份

​网络安全​：确保只在可信环境中运行

​权限管理​：使用最小权限原则设置Cloudflare API Token

技术支持
如遇问题请检查：

查看 ip_processor.log文件中的详细错误信息

确认配置文件中的参数设置正确

验证网络连接和API权限

检查输入文件格式是否符合要求

这个工具可以显著简化IP管理和Cloudflare DNS配置的工作流程，提高运维效率。

