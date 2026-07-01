#!/bin/bash
# ============================================================
# CentOS 7 下修复 Playwright 的脚本
# 在宝塔面板 → 终端 中执行此脚本
# ============================================================
set -e

echo "========================================="
echo "  Playwright CentOS 7 兼容性修复"
echo "========================================="

# 1. 安装 Chromium 系统依赖
echo ""
echo "[1/3] 安装 Chromium 系统依赖..."
yum install -y \
    alsa-lib atk cups-libs gtk3 libdrm mesa-libgbm \
    nspr nss libXcomposite libXdamage libXrandr \
    libXScrnSaver pango at-spi2-atk \
    libxkbcommon nss-tools 2>&1 | tail -5

# 2. 安装 Node.js 16.20.2 (兼容 CentOS 7 的 GLIBC 2.17)
echo ""
echo "[2/3] 安装 Node.js 16.20.2..."
NODE_PATH=/opt/node-v16.20.2-linux-x64
if [ ! -f "$NODE_PATH/bin/node" ]; then
    cd /tmp
    wget -q https://nodejs.org/dist/v16.20.2/node-v16.20.2-linux-x64.tar.xz
    tar xf node-v16.20.2-linux-x64.tar.xz -C /opt/
    rm -f node-v16.20.2-linux-x64.tar.xz
    echo "Node.js 安装到: $NODE_PATH"
else
    echo "Node.js 已存在: $NODE_PATH"
fi

# 验证版本
$NODE_PATH/bin/node -v

# 3. 检查当前 Java 项目 PID 并重启
echo ""
echo "[3/3] 完成！"
echo ""
echo "========================================="
echo "  后续步骤（在宝塔面板中操作）："
echo "========================================="
echo ""
echo "1. 打开 网站 → Java项目 → Extract-Original → 设置"
echo "2. 环境变量选择「指定变量」，添加："
echo ""
echo "   PLAYWRIGHT_NODEJS_PATH=$NODE_PATH/bin/node"
echo ""
echo "3. 点击「保存当前配置」"
echo "4. 项目会自动重启"
echo "5. 测试：curl http://localhost:3001/api/health"
echo ""
echo "Node.js 路径: $NODE_PATH/bin/node"
echo "========================================="
