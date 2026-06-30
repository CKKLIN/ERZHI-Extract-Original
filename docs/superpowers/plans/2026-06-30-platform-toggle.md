# 平台启停管理功能 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 管理员在"我的"页面切换各平台的启用/停用状态，停用的平台在首页完全隐藏。

**Architecture:** 新增 `platform_config` 数据库表持久化平台状态；后端提供公开接口（获取启用列表）和管理接口（查询/更新全部状态，需管理员权限）；首页 `onShow` 时拉取启用列表过滤渲染；"我的"页面管理员区域增加 switch 开关列表。

**Tech Stack:** Java 17 + Spring Boot 2.6.13 + JPA/Hibernate (后端), uni-app Vue 3 (前端)

## Global Constraints

- 管理员权限通过 `X-Openid` header 识别，查询 User 表校验 `role == 0`
- 公开接口 `/api/platforms/enabled` 无需登录，不校验权限
- 前端请求时必须携带 `X-Openid` header（管理员接口需要）
- 遵循现有代码风格：后端使用 Lombok + Builder 模式，前端使用 uni-app API

---

### Task 1: 创建 PlatformConfig 实体

**Files:**
- Create: `ERZHI-Extract-Original-Back-End/src/main/java/com/example/erzhiextractoriginalbackend/model/entity/PlatformConfig.java`

**Interfaces:**
- Produces: `PlatformConfig` entity with fields `id: Long`, `platformKey: String`, `enabled: Integer`, `updatedAt: LocalDateTime`

- [ ] **Step 1: 创建 PlatformConfig.java**

```java
package com.example.erzhiextractoriginalbackend.model.entity;

import lombok.*;
import javax.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "platform_config")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class PlatformConfig {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "platform_key", nullable = false, unique = true, length = 32)
    private String platformKey;

    /**
     * 0=停用, 1=启用
     */
    @Builder.Default
    @Column(nullable = false)
    private Integer enabled = 1;

    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;

    @PrePersist
    protected void onCreate() {
        updatedAt = LocalDateTime.now();
    }

    @PreUpdate
    protected void onUpdate() {
        updatedAt = LocalDateTime.now();
    }
}
```

- [ ] **Step 2: 编译验证**

```bash
cd ERZHI-Extract-Original-Back-End && mvn compile -q
```

Expected: BUILD SUCCESS

---

### Task 2: 创建 PlatformConfigRepository

**Files:**
- Create: `ERZHI-Extract-Original-Back-End/src/main/java/com/example/erzhiextractoriginalbackend/repository/PlatformConfigRepository.java`

**Interfaces:**
- Consumes: `PlatformConfig` entity from Task 1
- Produces: `PlatformConfigRepository` with `findByEnabled(Integer enabled): List<PlatformConfig>` and `findByPlatformKey(String platformKey): Optional<PlatformConfig>`

- [ ] **Step 1: 创建 PlatformConfigRepository.java**

```java
package com.example.erzhiextractoriginalbackend.repository;

import com.example.erzhiextractoriginalbackend.model.entity.PlatformConfig;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface PlatformConfigRepository extends JpaRepository<PlatformConfig, Long> {
    List<PlatformConfig> findByEnabled(Integer enabled);
    Optional<PlatformConfig> findByPlatformKey(String platformKey);
}
```

- [ ] **Step 2: 编译验证**

```bash
cd ERZHI-Extract-Original-Back-End && mvn compile -q
```

Expected: BUILD SUCCESS

---

### Task 3: 创建 AdminController

**Files:**
- Create: `ERZHI-Extract-Original-Back-End/src/main/java/com/example/erzhiextractoriginalbackend/controller/AdminController.java`

**Interfaces:**
- Consumes: `PlatformConfigRepository` from Task 2, `UserRepository` (existing), `ApiResponse` (existing), `Platform` enum (existing)
- Produces: `GET /api/platforms/enabled`, `GET /api/admin/platforms`, `PUT /api/admin/platforms`

- [ ] **Step 1: 创建 AdminController.java**

```java
package com.example.erzhiextractoriginalbackend.controller;

import com.example.erzhiextractoriginalbackend.model.dto.ApiResponse;
import com.example.erzhiextractoriginalbackend.model.entity.PlatformConfig;
import com.example.erzhiextractoriginalbackend.model.entity.User;
import com.example.erzhiextractoriginalbackend.model.enums.Platform;
import com.example.erzhiextractoriginalbackend.repository.PlatformConfigRepository;
import com.example.erzhiextractoriginalbackend.repository.UserRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.*;
import java.util.stream.Collectors;

@RestController
public class AdminController {

    private static final Logger log = LoggerFactory.getLogger(AdminController.class);

    private final PlatformConfigRepository platformConfigRepository;
    private final UserRepository userRepository;

    public AdminController(PlatformConfigRepository platformConfigRepository,
                           UserRepository userRepository) {
        this.platformConfigRepository = platformConfigRepository;
        this.userRepository = userRepository;
    }

    /**
     * GET /api/platforms/enabled
     * 公开接口，返回当前启用的平台 key 列表。
     */
    @GetMapping("/api/platforms/enabled")
    public ResponseEntity<ApiResponse<?>> getEnabledPlatforms() {
        List<PlatformConfig> enabled = platformConfigRepository.findByEnabled(1);
        List<String> keys = enabled.stream()
                .map(PlatformConfig::getPlatformKey)
                .collect(Collectors.toList());
        return ResponseEntity.ok(ApiResponse.ok(keys));
    }

    /**
     * GET /api/admin/platforms
     * 管理员接口，返回全部平台的启用/停用状态。
     * 需要在请求头中传入 X-Openid。
     */
    @GetMapping("/api/admin/platforms")
    public ResponseEntity<ApiResponse<?>> getAllPlatforms(
            @RequestHeader(value = "X-Openid", required = false) String openid) {
        if (!isAdmin(openid)) {
            return ResponseEntity.status(403)
                    .body(ApiResponse.fail("无管理员权限"));
        }

        List<PlatformConfig> configs = platformConfigRepository.findAll();

        // 确保 6 个平台都有记录（首次访问时自动初始化）
        Set<String> existingKeys = configs.stream()
                .map(PlatformConfig::getPlatformKey)
                .collect(Collectors.toSet());

        for (Platform p : Platform.values()) {
            if (!existingKeys.contains(p.getKey())) {
                PlatformConfig pc = PlatformConfig.builder()
                        .platformKey(p.getKey())
                        .enabled(1)
                        .build();
                platformConfigRepository.save(pc);
                configs.add(pc);
            }
        }

        List<Map<String, Object>> result = new ArrayList<>();
        for (PlatformConfig pc : configs) {
            Platform platform = Platform.fromKey(pc.getPlatformKey());
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("platformKey", pc.getPlatformKey());
            item.put("name", platform != null ? platform.getName() : pc.getPlatformKey());
            item.put("enabled", pc.getEnabled() == 1);
            result.add(item);
        }

        return ResponseEntity.ok(ApiResponse.ok(result));
    }

    /**
     * PUT /api/admin/platforms
     * 管理员接口，批量更新平台启用/停用状态。
     * 需要在请求头中传入 X-Openid。
     */
    @PutMapping("/api/admin/platforms")
    public ResponseEntity<ApiResponse<?>> updatePlatforms(
            @RequestHeader(value = "X-Openid", required = false) String openid,
            @RequestBody Map<String, Object> body) {
        if (!isAdmin(openid)) {
            return ResponseEntity.status(403)
                    .body(ApiResponse.fail("无管理员权限"));
        }

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> platforms = (List<Map<String, Object>>) body.get("platforms");
        if (platforms == null || platforms.isEmpty()) {
            return ResponseEntity.badRequest()
                    .body(ApiResponse.fail("platforms 不能为空"));
        }

        int updated = 0;
        for (Map<String, Object> item : platforms) {
            String key = (String) item.get("platformKey");
            Boolean enabled = (Boolean) item.get("enabled");
            if (key == null || enabled == null) continue;

            Optional<PlatformConfig> opt = platformConfigRepository.findByPlatformKey(key);
            PlatformConfig pc;
            if (opt.isPresent()) {
                pc = opt.get();
            } else {
                // 不存在则创建
                pc = PlatformConfig.builder()
                        .platformKey(key)
                        .enabled(1)
                        .build();
            }
            pc.setEnabled(enabled ? 1 : 0);
            platformConfigRepository.save(pc);
            updated++;
        }

        log.info("[admin/platforms] {} platforms updated by admin", updated);
        return ResponseEntity.ok(ApiResponse.ok(Map.of("updated", updated)));
    }

    /**
     * 校验管理员权限。
     */
    private boolean isAdmin(String openid) {
        if (openid == null || openid.isEmpty()) {
            return false;
        }
        Optional<User> userOpt = userRepository.findByOpenid(openid);
        return userOpt.isPresent() && userOpt.get().isAdmin();
    }
}
```

- [ ] **Step 2: 编译验证**

```bash
cd ERZHI-Extract-Original-Back-End && mvn compile -q
```

Expected: BUILD SUCCESS

---

### Task 4: 更新数据库 Schema

**Files:**
- Modify: `ERZHI-Extract-Original-Back-End/src/main/resources/schema.sql`

**Interfaces:**
- Consumes: `PlatformConfig` entity from Task 1
- Produces: DDL for `platform_config` table

- [ ] **Step 1: 在 schema.sql 末尾追加 platform_config 建表语句**

在文件末尾追加以下内容：

```sql
-- 平台启停配置
CREATE TABLE IF NOT EXISTS `platform_config` (
    `id`           BIGINT       NOT NULL AUTO_INCREMENT,
    `platform_key` VARCHAR(32)  NOT NULL COMMENT '平台标识: douyin/xiaohongshu/bilibili/kuaishou/youtube/weixin',
    `enabled`      TINYINT      NOT NULL DEFAULT 1 COMMENT '0=停用, 1=启用',
    `updated_at`   TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_platform_key` (`platform_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='平台启停配置';

-- 预填充 6 个平台，默认全部启用（使用 IGNORE 避免重复插入报错）
INSERT IGNORE INTO `platform_config` (`platform_key`, `enabled`) VALUES
('douyin', 1),
('xiaohongshu', 1),
('bilibili', 1),
('kuaishou', 1),
('youtube', 1),
('weixin', 1);
```

---

### Task 5: 修改首页 — 动态过滤平台列表

**Files:**
- Modify: `pages/index/index.vue`

**Interfaces:**
- Consumes: `GET /api/platforms/enabled` (返回 `["douyin", "xiaohongshu", ...]`)
- Produces: 首页平台列表仅展示启用的平台

- [ ] **Step 1: 在 data 中添加完整平台映射和加载状态**

修改 `pages/index/index.vue` 中 `data()` 的 `platforms` 定义。将原来的硬编码列表替换为空的初始值，并新增 `allPlatforms` 作为完整映射表。

找到第 81-88 行：
```javascript
platforms: [
    { name: '抖音', icon: '/static/douyin.svg' },
    { name: '小红书', icon: '/static/xiaohoshu.svg' },
    { name: 'B站', icon: '/static/bilibili.svg' },
    { name: '快手', icon: '/static/kuaisho.svg' },
    { name: '视频号', icon: '/static/shipinghao.svg' },
    { name: 'YouTube', icon: '/static/youtube.svg' },
],
```

替换为：
```javascript
platforms: [],
allPlatforms: {
    douyin:      { name: '抖音',   icon: '/static/douyin.svg' },
    xiaohongshu: { name: '小红书', icon: '/static/xiaohoshu.svg' },
    bilibili:    { name: 'B站',    icon: '/static/bilibili.svg' },
    kuaishou:    { name: '快手',   icon: '/static/kuaisho.svg' },
    weixin:      { name: '视频号', icon: '/static/shipinghao.svg' },
    youtube:     { name: 'YouTube', icon: '/static/youtube.svg' },
},
```

- [ ] **Step 2: 新增 loadEnabledPlatforms 方法，在 onLoad 和 onShow 中调用**

在 `methods` 中新增 `loadEnabledPlatforms` 方法：

```javascript
// 从后端获取当前启用的平台列表
loadEnabledPlatforms() {
    // #ifdef H5
    const url = '/api/platforms/enabled';
    // #endif
    // #ifdef MP-WEIXIN
    const url = config.apiBase + '/api/platforms/enabled';
    // #endif

    uni.request({
        url: url,
        method: 'GET',
        success: (res) => {
            if (res.data && res.data.success && Array.isArray(res.data.data)) {
                const enabledKeys = res.data.data;
                this.platforms = enabledKeys
                    .filter(key => this.allPlatforms[key])
                    .map(key => this.allPlatforms[key]);
            } else {
                // 降级：接口失败时显示全部平台
                this.platforms = Object.values(this.allPlatforms);
            }
        },
        fail: () => {
            // 降级：网络失败时显示全部平台
            this.platforms = Object.values(this.allPlatforms);
        },
    });
},
```

- [ ] **Step 3: 在 onLoad 中调用 loadEnabledPlatforms**

修改 `onLoad()` 方法，在 `this.loadHistory()` 后添加：

```javascript
onLoad() {
    this.loadHistory();
    this.loadEnabledPlatforms();
},
```

- [ ] **Step 4: 在 onShow 中刷新平台列表**

修改 `onShow()` 方法，追加 `this.loadEnabledPlatforms()`：

```javascript
onShow() {
    console.log('[index] 当前登录状态:', isLoggedIn());
    if (isLoggedIn()) {
        console.log('[index] 用户信息:', getUserInfo());
    }
    this.loadEnabledPlatforms();
},
```

---

### Task 6: 修改"我的"页面 — 添加平台开关 UI

**Files:**
- Modify: `pages/my/my.vue`

**Interfaces:**
- Consumes: `GET /api/admin/platforms`, `PUT /api/admin/platforms` (带 `X-Openid` header)
- Consumes: `getOpenId()` from `@/utils/auth.js`
- Produces: 管理员可见的平台开关列表

- [ ] **Step 1: 在 import 中增加 getOpenId**

修改第 100 行：
```javascript
import { getUserInfo, saveUserInfo, logout, isAdmin, getOpenId } from '@/utils/auth.js';
```

- [ ] **Step 2: 在 data 中增加平台相关字段**

在 `data()` 返回对象中添加两个字段（放在 `cookieStatus: ''` 之后）：

```javascript
adminPlatforms: [],
platformSaving: false,
```

- [ ] **Step 3: 在模板的管理员设置区域内增加平台管理 UI**

在现有 cookie-card 的 `</view>` 之后、`</view>` (admin-section 结束) 之前，即第 62 行 `</view>`（cookie-card 结束标签）之后，插入平台管理卡片：

```html
            <view class="platform-card">
                <text class="cookie-label">平台管理</text>
                <view class="platform-item" v-for="item in adminPlatforms" :key="item.platformKey">
                    <view class="platform-info">
                        <text class="platform-name-text">{{ item.name }}</text>
                        <text class="platform-status">{{ item.enabled ? '已启用' : '已停用' }}</text>
                    </view>
                    <switch
                        :checked="item.enabled"
                        :disabled="platformSaving"
                        color="#5cc261"
                        @change="onPlatformSwitch($event, item)"
                    />
                </view>
                <text class="cookie-status" v-if="platformSaving">保存中...</text>
            </view>
```

- [ ] **Step 4: 在 onShow 中加载平台状态**

修改 `onShow()` 方法，在已有的管理员判断块中添加 `loadPlatforms()` 调用。将第 127-130 行：
```javascript
if (this.isAdmin) {
    console.log('[my] 管理员已登录');
    this.loadCookie();
}
```

修改为：
```javascript
if (this.isAdmin) {
    console.log('[my] 管理员已登录');
    this.loadCookie();
    this.loadPlatforms();
}
```

- [ ] **Step 5: 新增 loadPlatforms 和 onPlatformSwitch 方法**

在 `methods` 中新增以下两个方法（放在 `calcStats` 之前）：

```javascript
// 加载平台启停状态
loadPlatforms() {
    // #ifdef H5
    const url = '/api/admin/platforms';
    // #endif
    // #ifdef MP-WEIXIN
    const url = config.apiBase + '/api/admin/platforms';
    // #endif

    uni.request({
        url: url,
        method: 'GET',
        header: { 'X-Openid': getOpenId() },
        success: (res) => {
            if (res.data && res.data.success) {
                this.adminPlatforms = res.data.data || [];
            }
        },
        fail: (err) => {
            console.error('[my] 加载平台状态失败:', err);
        },
    });
},

// 切换平台启用/停用
onPlatformSwitch(e, item) {
    const newEnabled = e.detail.value;
    this.platformSaving = true;

    // #ifdef H5
    const url = '/api/admin/platforms';
    // #endif
    // #ifdef MP-WEIXIN
    const url = config.apiBase + '/api/admin/platforms';
    // #endif

    uni.request({
        url: url,
        method: 'PUT',
        header: {
            'Content-Type': 'application/json',
            'X-Openid': getOpenId(),
        },
        data: {
            platforms: [{ platformKey: item.platformKey, enabled: newEnabled }],
        },
        success: (res) => {
            if (res.data && res.data.success) {
                item.enabled = newEnabled;
                uni.showToast({ title: newEnabled ? '已启用' : '已停用', icon: 'success' });
            } else {
                uni.showToast({ title: res.data?.error || '操作失败', icon: 'none' });
            }
        },
        fail: (err) => {
            console.error('[my] 更新平台状态失败:', err);
            uni.showToast({ title: '网络请求失败', icon: 'none' });
        },
        complete: () => {
            this.platformSaving = false;
        },
    });
},
```

- [ ] **Step 6: 新增平台管理卡片的 CSS 样式**

在 `<style scoped>` 中，`.cookie-status` 样式之后追加：

```css
/* 平台管理 */
.platform-card {
    background: #fff;
    border-radius: 20rpx;
    padding: 30rpx;
    margin-top: 20rpx;
    box-shadow: 0 4rpx 20rpx rgba(0, 0, 0, 0.05);
}

.platform-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 24rpx 0;
    border-bottom: 1rpx solid #f5f5f5;
}

.platform-item:last-child {
    border-bottom: none;
}

.platform-info {
    display: flex;
    flex-direction: column;
    gap: 6rpx;
}

.platform-name-text {
    font-size: 28rpx;
    color: #333;
}

.platform-status {
    font-size: 22rpx;
    color: #999;
}
```

---

### Task 7: 验证 — 启动后端并测试 API

- [ ] **Step 1: 启动后端**

```bash
cd ERZHI-Extract-Original-Back-End && mvn spring-boot:run
```

- [ ] **Step 2: 测试公开接口 — 获取启用平台**

```bash
curl http://localhost:3001/api/platforms/enabled
```

Expected: `{"success":true,"data":["douyin","xiaohongshu","bilibili","kuaishou","youtube","weixin"],"timestamp":...}`

- [ ] **Step 3: 测试管理接口 — 无权限访问被拒**

```bash
curl http://localhost:3001/api/admin/platforms
```

Expected: `{"success":false,"error":"无管理员权限","timestamp":...}` (HTTP 403)

- [ ] **Step 4: 先在数据库中设置一个管理员用户，然后用 X-Openid 访问管理接口**

```bash
# 用数据库中实际存在的 openid 替换 YOUR_ADMIN_OPENID
curl -H "X-Openid: YOUR_ADMIN_OPENID" http://localhost:3001/api/admin/platforms
```

Expected: 返回 6 个平台的完整状态列表

- [ ] **Step 5: 测试停用平台**

```bash
curl -X PUT http://localhost:3001/api/admin/platforms \
  -H "Content-Type: application/json" \
  -H "X-Openid: YOUR_ADMIN_OPENID" \
  -d '{"platforms":[{"platformKey":"douyin","enabled":false}]}'
```

Expected: `{"success":true,"data":{"updated":1},"timestamp":...}`

- [ ] **Step 6: 验证公开接口不再返回已停用平台**

```bash
curl http://localhost:3001/api/platforms/enabled
```

Expected: `douyin` 不再出现在 data 数组中

- [ ] **Step 7: 恢复 douyin 为启用状态**

```bash
curl -X PUT http://localhost:3001/api/admin/platforms \
  -H "Content-Type: application/json" \
  -H "X-Openid: YOUR_ADMIN_OPENID" \
  -d '{"platforms":[{"platformKey":"douyin","enabled":true}]}'
```

- [ ] **Step 8: 编译前端确认无语法错误**

```bash
cd d:/money/ERZHI-Extract-Original && npx vue-tsc --noEmit 2>&1 || echo "Skipping typecheck (uni-app project)"
```

Expected: 无编译错误（uni-app 项目通常不做 TS 类型检查，重点是运行时正确）
