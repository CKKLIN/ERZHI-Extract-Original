# 平台启停管理功能 — 设计文档

**日期**: 2026-06-30  
**概述**: 管理员可在"我的"页面动态启用/停用 6 个视频解析平台，停用后前端完全隐藏。

---

## 1. 需求

- 管理员在"我的"页面的管理员设置区域，看到 6 个平台的开关列表
- 切换某个平台为停用后，首页平台列表不再显示该平台
- 停用状态持久化到数据库，重启后保留
- 普通用户无感知——只看到启用的平台

## 2. 数据库

新增 `platform_config` 表：

```sql
CREATE TABLE `platform_config` (
    `id`           BIGINT    NOT NULL AUTO_INCREMENT,
    `platform_key` VARCHAR(32) NOT NULL COMMENT '平台标识: douyin/xiaohongshu/...',
    `enabled`      TINYINT   NOT NULL DEFAULT 1 COMMENT '0=停用, 1=启用',
    `updated_at`   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_platform_key` (`platform_key`)
);

INSERT INTO platform_config (platform_key, enabled) VALUES
('douyin', 1), ('xiaohongshu', 1), ('bilibili', 1),
('kuaishou', 1), ('youtube', 1), ('weixin', 1);
```

对应 Java 实体：`PlatformConfig.java`（JPA Entity）  
对应 Repository：`PlatformConfigRepository.java`

## 3. 后端 API

### 3.1 公开接口 — 获取启用平台

| 方法 | 路径 |
|------|------|
| `GET` | `/api/platforms/enabled` |

无需登录。返回当前所有 `enabled=1` 的平台列表。

响应：
```json
{
  "code": 0,
  "data": ["douyin", "xiaohongshu", "bilibili", "kuaishou", "youtube", "weixin"]
}
```

### 3.2 管理接口 — 获取全部平台状态

| 方法 | 路径 |
|------|------|
| `GET` | `/api/admin/platforms` |

需要管理员权限（role=0）。

响应：
```json
{
  "code": 0,
  "data": [
    { "platformKey": "douyin", "name": "抖音", "enabled": true },
    ...
  ]
}
```

### 3.3 管理接口 — 批量更新平台状态

| 方法 | 路径 |
|------|------|
| `PUT` | `/api/admin/platforms` |

需要管理员权限（role=0）。支持部分更新。

请求体：
```json
{
  "platforms": [
    { "platformKey": "douyin", "enabled": false },
    { "platformKey": "bilibili", "enabled": true }
  ]
}
```

### 新增文件清单（后端）

- `model/entity/PlatformConfig.java` — JPA 实体
- `repository/PlatformConfigRepository.java` — 数据访问
- `controller/AdminController.java` — 管理 API + 公开 `/api/platforms/enabled`

## 4. 前端

### 4.1 首页 [pages/index/index.vue](pages/index/index.vue)

- `onLoad` / `onShow` 中调用 `GET /api/platforms/enabled`
- 用返回的 enabled 列表过滤本地 `platforms` 数组后再渲染
- 如果某平台被停用，即使解析链接也不显示该平台入口

### 4.2 "我的"页面 [pages/my/my.vue](pages/my/my.vue)

- 在现有"管理员设置"区域内，Cookie 配置下方新增"平台管理"区域
- 用 `uni.request` 获取平台列表（`GET /api/admin/platforms`）
- 每个平台显示名称 + `switch` 组件
- 切换时收集变更，调用 `PUT /api/admin/platforms`

### 新增文件清单（前端）

无新增文件，仅修改现有文件：
- `pages/index/index.vue` — 添加动态过滤逻辑
- `pages/my/my.vue` — 添加平台开关 UI 和相关方法

## 5. 数据流

```
管理员切换开关
    → PUT /api/admin/platforms (带 openid header)
    → AdminController 校验 role=0
    → 更新 platform_config 表
    → 返回成功

普通用户打开首页
    → GET /api/platforms/enabled
    → 查询 platform_config WHERE enabled=1
    → 返回 platform_key 列表
    → 前端过滤 platforms 数组 → 只渲染启用的平台
```
