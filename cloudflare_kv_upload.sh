#!/bin/bash

# Cloudflare KV 上传脚本
# 适用于 GitHub Actions 环境

set -e  # 遇到错误立即退出

echo "=== Cloudflare KV 文件上传开始 ==="

# 从环境变量获取配置
CF_DOMAIN="${CF_DOMAIN}"
CF_TOKEN="${CF_TOKEN}"
FOLDER_PATH="${FOLDER_PATH:-output}"  # 修改为相对路径，指向项目根目录的output

# 检查必要的环境变量
if [ -z "$CF_DOMAIN" ] || [ -z "$CF_TOKEN" ]; then
    echo "错误: 必须设置 CF_DOMAIN 和 CF_TOKEN 环境变量"
    echo "请在 GitHub Secrets 中设置这些变量"
    exit 1
fi

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FULL_FOLDER_PATH="$PROJECT_ROOT/output"

echo "项目根目录: $PROJECT_ROOT"
echo "输出目录: $FULL_FOLDER_PATH"

# 检查目标文件夹是否存在
if [ ! -d "$FULL_FOLDER_PATH" ]; then
    echo "错误: 文件夹 $FULL_FOLDER_PATH 不存在"
    echo "当前目录: $(pwd)"
    echo "项目根目录内容:"
    ls -la "$PROJECT_ROOT"
    exit 1
fi

echo "上传目录: $FULL_FOLDER_PATH"
echo "目标域名: $CF_DOMAIN"

# 自定义URL编码函数
urlencode() {
    local string="$1"
    local encoded=""
    local pos c o

    [ -z "$string" ] && return

    pos=0
    while [ $pos -lt ${#string} ]; do
        c=${string:$pos:1}
        case "$c" in
            [-_.~a-zA-Z0-9]) o="$c" ;;
            *) o=$(printf '%%%02X' "'$c") ;;
        esac
        encoded+="$o"
        pos=$((pos + 1))
    done

    echo "$encoded"
}

# 统计变量
total_files=0
success_count=0
fail_count=0

echo "开始扫描文件..."

# 进入输出目录
cd "$FULL_FOLDER_PATH"

# 遍历文件夹中所有 .txt 文件
for FILENAME in *.txt; do
    # 检查文件是否存在（处理无匹配的情况）
    if [ ! -f "$FILENAME" ]; then
        echo "未找到 .txt 文件，跳过"
        continue
    fi

    ((total_files++))
    
    # 获取文件名（不含路径）
    FILENAME_ONLY=$(basename "$FILENAME")

    echo "处理文件: $FILENAME_ONLY"

    # 检查文件大小
    file_size=$(stat -f%z "$FILENAME" 2>/dev/null || stat -c%s "$FILENAME" 2>/dev/null)
    if [ "$file_size" -eq 0 ]; then
        echo "警告: 文件为空，跳过"
        ((fail_count++))
        continue
    fi

    # 读取文件的前10行内容并进行Base64编码
    BASE64_TEXT=$(head -n 10 "$FILENAME" | base64 -w 0)

    # URL编码文件名
    FILENAME_URL=$(urlencode "$FILENAME_ONLY")

    # 构建URL
    URL="https://${CF_DOMAIN}/${FILENAME_URL}?token=${CF_TOKEN}&b64=${BASE64_TEXT}"

    echo "上传文件: $FILENAME"

    # 使用curl发送请求
    if curl -s -f "$URL" -o /dev/null; then
        echo "✓ 文件 $FILENAME 上传成功"
        ((success_count++))
    else
        echo "✗ 文件 $FILENAME 上传失败"
        ((fail_count++))
    fi
done

# 返回原目录
cd - > /dev/null

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━"
echo "文件总数 : $total_files"
echo "成功上传 : $success_count"
echo "失败数量 : $fail_count"
echo "━━━━━━━━━━━━━━━━━━━━━"

if [ $fail_count -gt 0 ]; then
    exit 1
fi