#!/bin/bash

# WebDAV 上传脚本
# 适用于 GitHub Actions 环境

set -e  # 遇到错误立即退出

echo "=== WebDAV 文件上传开始 ==="

# WebDAV配置（从环境变量获取）
WEBDAV_URL="${WEBDAV_URL}"
USERNAME="${WEBDAV_USERNAME}"
PASSWORD="${WEBDAV_PASSWORD}"

# 检查必要的环境变量
if [ -z "$WEBDAV_URL" ] || [ -z "$USERNAME" ] || [ -z "$PASSWORD" ]; then
    echo "错误: 必须设置 WEBDAV_URL, WEBDAV_USERNAME 和 WEBDAV_PASSWORD 环境变量"
    echo "请在 GitHub Secrets 中设置这些变量"
    exit 1
fi

# 检查output目录是否存在
if [ ! -d "output" ]; then
    echo "错误：output目录不存在"
    exit 1
fi

# 进入output目录
cd output || exit 1

# 获取所有文件列表
shopt -s nullglob
files=( * )
if [ ${#files[@]} -eq 0 ]; then
    echo "错误：output目录为空"
    exit 1
fi

# 统计变量
total_files=${#files[@]}
success_count=0
fail_count=0

# 遍历上传文件
for file in "${files[@]}"; do
    if [ -d "$file" ]; then
        echo "跳过目录: $file"
        continue
    fi
    
    echo "正在上传: $file"
    
    # 执行上传操作
    http_code=$(curl -s -o /dev/null -w "%{http_code}" \
        -X PUT "${WEBDAV_URL}/${file}" \
        --user "${USERNAME}:${PASSWORD}" \
        -T "$file")
    
    # 结果判断
    case $http_code in
        201|204)
            echo "√ 上传成功"
            ((success_count++))
            ;;
        409)
            echo "× 冲突错误（文件可能已存在）"
            ((fail_count++))
            ;;
        401)
            echo "× 认证失败，请检查账号密码"
            exit 2
            ;;
        *)
            echo "× 上传失败 (HTTP $http_code)"
            ((fail_count++))
            ;;
    esac
done

# 返回原目录
cd ..

# 输出统计结果
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━"
echo "文件总数 : $total_files"
echo "成功上传 : $success_count"
echo "失败数量 : $fail_count"
echo "━━━━━━━━━━━━━━━━━━━━━"
