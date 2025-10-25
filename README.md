# **IP Processor 使用说明**

## **项目概述**

IP Processor 是一个自动化IP地址处理工具，能够从文件中提取IP地址，检测其可用性，并将有效IP上传到Cloudflare DNS。项目适合需要管理大量IP地址的网络管理员和开发人员使用。

## **快速开始**

### **1. 克隆仓库**

```
git clone https://github.com/your-username/ip-processor.git
cd ip-processor
```

### **2. 创建必要目录**

```
mkdir ips output
```

### **3. 添加IP文件**

将您的IP文件放入 `ips`目录：

- 支持 `.txt`和 `.csv`格式
- 文件名将作为标签（如 `HK.txt`将生成 `ip-HK.your-domain.com`）

### **4. 配置文件设置**

编辑 `config.ini`文件：

```
[cloudflare]
enable = true
api_token = ${CF_API_TOKEN}  # 使用环境变量更安全
zone_id = ${CF_ZONE_ID}
domain = pages.dev  # 您的域名
record_name = cfip
```

### **5. 设置环境变量**

在系统或GitHub Secrets中设置：

```
# Linux/macOS
export CF_API_TOKEN=your_cloudflare_api_token
export CF_ZONE_ID=your_zone_id
export CF_DOMAIN=your-domain.com
export CFKV_DOMAIN=your-domain.com
export CFKV_TOKEN=your-token_id

# Windows
set CF_API_TOKEN=your_cloudflare_api_token
set CF_ZONE_ID=your_zone_id
set CF_DOMAIN=your-domain.com
set CFKV_DOMAIN=your-domain.com
set CFKV_TOKEN=your-token_id
```

## **GitHub Actions设置（私有仓库）**

### **1. 添加GitHub Secrets**

在仓库设置中添加：

- `CF_API_TOKEN`：Cloudflare API Token
- `CF_ZONE_ID`：Cloudflare Zone ID
- `CF_DOMAIN`：您的域名
- `CFKV_DOMAIN`：上传到Cloudflare KV存储器的域名（项目：[https://github.com/cmliu/CF-Workers-TEXT2KV）](https://github.com/cmliu/CF-Workers-TEXT2KV%EF%BC%89)
- `CFKV_TOKEN`：Cloudflare KV上传令牌（项目：[https://github.com/cmliu/CF-Workers-TEXT2KV）](https://github.com/cmliu/CF-Workers-TEXT2KV%EF%BC%89)

### **2. 解决私有仓库问题**

私有仓库需要设置账单信息：

1. 访问 GitHub Settings → Billing and plans
2. 添加有效的支付方式
3. 确保有足够的Actions分钟数

### **3. 工作流文件**

`.github/workflows/run-pipeline.yml`已包含在项目中，会自动：

- 每12小时运行一次
- 处理IP文件
- 上传到Cloudflare

## **使用流程**

### **1. 准备IP文件**

在 `ips`目录中添加IP文件：

- `HK.txt`：香港IP
- `US.csv`：美国IP
- 格式示例：
    
    ```
    1.1.1.1
    8.8.8.8:443
    192.168.1.1:8080#香港节点
    ```
    

### **2. 本地运行**

```
python ip_processor.py**3. 查看结果**
```

- 输出文件：`output/`目录
- 日志文件：`ip_processor.log`
- Cloudflare DNS记录：`ip-标签.your-domain.com`

### **4. GitHub Actions运行**

- 自动每12小时运行
- 手动触发：Actions → IP Processor Pipeline → Run workflow

## **高级配置**

### **1. 自定义检测方法**

在 `config.ini`中修改：

```
[IP_CHECK]
CHECK_METHOD = port# ping或portCHECK_PORT = 443# 检测端口CHECK_TIMEOUT = 2# 超时时间(秒)
```

### **2. 调整上传频率**

修改工作流文件中的cron表达式：

```
on:
  schedule:
    - cron: '0 */6 * * *'# 每6小时运行一次
```

### **3. 限制上传IP数量**

```
[cloudflare]
max_records_per_line = 10# 每个标签最多上传10个IP
```

## **常见问题解决**

### **1. GitHub Actions失败**

**错误**："The job was not started because recent account payments have failed"

**解决**：

1. 访问 GitHub Settings → Billing and plans
2. 添加有效的支付方式
3. 确认账单信息正确

### **2. IP检测失败**

**错误**：所有IP检测失败

**解决**：

1. 检查网络连接
2. 增加超时时间：
    
    ```
    [IP_CHECK]
    CHECK_TIMEOUT = 5
    ```
    
3. 尝试不同的检测方法

### **3. Cloudflare上传失败**

**错误**：API返回400错误

**解决**：

1. 检查API Token权限
2. 确认Zone ID和域名正确
3. 验证TTL值在1-86400之间

### **4. 文件未处理**

**错误**：output目录为空

**解决**：

1. 检查ips目录是否有文件
2. 查看日志文件 `ip_processor.log`
3. 确保文件格式正确

## **最佳实践**

1. **使用环境变量**：不要在配置文件中直接存储敏感信息
2. **定期备份**：重要IP文件定期备份
3. **监控日志**：定期检查 `ip_processor.log`
4. **限制权限**：Cloudflare API Token使用最小权限原则
5. **测试配置**：修改配置后先在本地测试

## **技术支持**

遇到问题时：

1. 查看 `ip_processor.log`获取详细错误信息
2. 检查GitHub Actions运行日志
3. 确保所有依赖已安装：
    
    ```
    pip install requests tqdm configparser
    ```
    

如需进一步帮助，请提供：

- 相关日志文件
- 配置文件（去除敏感信息）
- 错误截图

这个工具将帮助您高效管理IP地址，自动化DNS记录更新，节省大量手动操作时间。

## **许可证**

本项目采用 MIT 许可证。详情请查看 LICENSE 文件。

## **更新日志**

### **v1.0.0 (2025-10-25)**

- 初始版本发布
- 支持IP提取和检测
- 支持Cloudflare DNS上传
- 支持GitHub Actions自动化

---

*最后更新：2025-10-25*
