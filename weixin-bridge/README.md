# WeixinProxyBridge

视频号 MITM 代理桥接服务。运行在 Windows 上，拦截微信 PC 客户端的 HTTPS 视频流量，通过 REST API 暴露给 Java 后端。

## 快速开始

1. 安装 Python 3.9+
2. 双击 `start.bat`（首次运行会自动创建 venv 并安装依赖）
3. 首次运行后，安装 CA 证书：
   - 证书位置：`%USERPROFILE%\.mitmproxy\mitmproxy-ca-cert.cer`
   - 双击安装 → "本地计算机" → "受信任的根证书颁发机构"
4. 设置 Windows 代理：
   - 设置 → 网络和 Internet → 代理
   - 手动设置代理 → 地址: `127.0.0.1` 端口: `8899`
5. 打开微信 PC 客户端，确保已登录

## API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/parse` | POST | 提交视频号链接，等待捕获结果 |
| `/api/health` | GET | 健康检查 |
| `/api/videos` | GET | 最近捕获的视频列表 |
| `/api/proxy/status` | GET | 代理运行状态 |
| `/api/proxy/start` | POST | 启动代理 |
| `/api/proxy/stop` | POST | 停止代理 |

### POST /api/parse

```json
// 请求
{ "url": "https://channels.weixin.qq.com/...", "waitSeconds": 60 }

// 成功响应
{
  "success": true,
  "data": {
    "title": "视频标题",
    "videoUrl": "https://finder.video.qq.com/...",
    "downloadLinks": { "combined": { "url": "...", "quality": "..." } }
  }
}

// 超时响应
{ "success": false, "error": "解析超时..." }
```

## 调试

- 健康检查: `curl http://127.0.0.1:9600/api/health`
- 查看捕获: `curl http://127.0.0.1:9600/api/videos`
- 查看代理状态: `curl http://127.0.0.1:9600/api/proxy/status`
