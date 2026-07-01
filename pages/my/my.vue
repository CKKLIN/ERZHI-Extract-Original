<template>
	<view class="container">
		<!-- 用户信息卡片 -->
		<view class="user-card" @tap="handleUserCardTap">
			<view class="avatar-wrap">
				<image
					class="avatar"
					:src="(userInfo && userInfo.avatarUrl) || '/static/logo.png'"
					mode="aspectFill"
				/>
			</view>
			<view class="user-info">
				<text class="username">{{ (userInfo && userInfo.nickName) || '点击完善资料' }}</text>
				<text class="user-desc" v-if="userInfo && isAdmin">管理员</text>
				<text class="user-desc" v-else-if="userInfo && userInfo.nickName">已登录</text>
				<text class="user-desc" v-else>设置头像和昵称</text>
			</view>
			<text class="logout-btn" v-if="userInfo && userInfo.openid" @tap.stop="handleLogout">退出</text>
		</view>

		<!-- 统计信息 -->
		<view class="stats-card">
			<view class="stat-item">
				<text class="stat-num">{{ totalCount }}</text>
				<text class="stat-label">累计解析</text>
			</view>
			<view class="stat-divider"></view>
			<view class="stat-item">
				<text class="stat-num">{{ todayCount }}</text>
				<text class="stat-label">今日解析</text>
			</view>
			<view class="stat-divider"></view>
			<view class="stat-item">
				<text class="stat-num">{{ platformCount }}</text>
				<text class="stat-label">支持平台</text>
			</view>
		</view>

		<!-- 管理员：视频号 Cookie 配置 -->
		<view class="admin-section" v-if="isAdmin">
			<text class="section-title">管理员设置</text>
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
		</view>

		<!-- 功能列表 -->
		<view class="menu-section">
			<view class="menu-item" @tap="handleMenu('history')">
				<text class="menu-icon">历史</text>
				<text class="menu-text">解析历史</text>
				<text class="menu-arrow">›</text>
			</view>
			<view class="menu-item" @tap="handleMenu('feedback')">
				<text class="menu-icon">反馈</text>
				<text class="menu-text">意见反馈</text>
				<text class="menu-arrow">›</text>
			</view>
			<view class="menu-item" @tap="handleMenu('about')">
				<text class="menu-icon">关于</text>
				<text class="menu-text">关于我们</text>
				<text class="menu-arrow">›</text>
			</view>
		</view>

		<!-- 底部版本 -->
		<view class="footer">
			<text class="version">v1.0.0</text>
		</view>

		<!-- 资料完善弹窗（后台已自动登录） -->
		<login-modal
			:visible="showLoginModal"
			@close="showLoginModal = false"
			@login-success="onLoginSuccess"
		/>
	</view>
</template>

<script>
	import config from '@/config/index.js';
	import { getUserInfo, saveUserInfo, logout, isAdmin, getOpenId } from '@/utils/auth.js';
	import loginModal from '@/components/login-modal.vue';

	export default {
		components: {
			'login-modal': loginModal,
		},
		data() {
			return {
				userInfo: null,
				showLoginModal: false,
				totalCount: 0,
				todayCount: 0,
				platformCount: 6,
				wxCookie: '',
				cookieStatus: '',
				adminPlatforms: [],
				platformSaving: false,
			}
		},
		computed: {
			isAdmin() {
				return isAdmin();
			},
		},
		onShow() {
			this.userInfo = getUserInfo();
			this.calcStats();
			console.log('[my] 当前用户信息:', this.userInfo);
			if (this.isAdmin) {
				console.log('[my] 管理员已登录');
				this.loadCookie();
				this.loadPlatforms();
			}
		},
		methods: {
			// 点击用户卡片 → 打开资料完善弹窗
			handleUserCardTap() {
				this.showLoginModal = true;
			},

			// 资料保存成功
			onLoginSuccess(info) {
				saveUserInfo(info);
				this.userInfo = getUserInfo();
				this.showLoginModal = false;
				uni.showToast({ title: '资料已保存', icon: 'success' });
				if (this.isAdmin) {
					this.loadCookie();
				}
			},

			// 退出登录
			handleLogout() {
				uni.showModal({
					title: '提示',
					content: '确定退出登录？重新进入小程序将自动登录。',
					success: (res) => {
						if (res.confirm) {
							logout();
							this.userInfo = null;
							uni.showToast({ title: '已退出登录', icon: 'none' });
						}
					},
				});
			},

			// Cookie 输入
			onCookieInput(e) {
				this.wxCookie = e.detail.value;
			},

			// 加载已保存的 cookie
			loadCookie() {
				try {
					const saved = uni.getStorageSync('wx_cookie');
					if (saved) {
						this.wxCookie = saved;
						console.log('[my] 已加载本地 cookie');
					}
				} catch (e) {}
			},

			// 保存 cookie
			saveCookie() {
				if (!this.wxCookie.trim()) {
					uni.showToast({ title: '请输入 cookie', icon: 'none' });
					return;
				}

				try {
					uni.setStorageSync('wx_cookie', this.wxCookie.trim());
				} catch (e) {}

				this.cookieStatus = '保存中...';
				uni.request({
					url: config.apiBase + '/api/weixin/set-cookie',
					method: 'POST',
					header: { 'Content-Type': 'application/json' },
					data: { cookie: this.wxCookie.trim() },
					success: (res) => {
						if (res.data && res.data.success) {
							this.cookieStatus = 'Cookie 已生效，视频号解析已启用';
							uni.showToast({ title: '保存成功', icon: 'success' });
						} else {
							this.cookieStatus = '保存失败：' + (res.data.error || '未知错误');
						}
					},
					fail: (err) => {
						console.error('[my] 保存 cookie 失败:', JSON.stringify(err));
						this.cookieStatus = '网络请求失败';
					},
				});
			},

			// 清空 cookie
			clearCookie() {
				uni.showModal({
					title: '提示',
					content: '确定清空视频号 Cookie？',
					success: (res) => {
						if (res.confirm) {
							this.wxCookie = '';
							this.cookieStatus = '';
							try {
								uni.removeStorageSync('wx_cookie');
							} catch (e) {}
							uni.showToast({ title: '已清空', icon: 'none' });
						}
					},
				});
			},

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
						uni.showToast({ title: '加载平台状态失败', icon: 'none' });
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

			// 计算统计数据
			calcStats() {
				try {
					const data = uni.getStorageSync('parse_history');
					if (data) {
						const history = JSON.parse(data);
						this.totalCount = history.length;

						const today = new Date();
						today.setHours(0, 0, 0, 0);
						const todayTs = today.getTime();
						this.todayCount = history.filter(item => item.time >= todayTs).length;
					}
				} catch (e) {}
			},

			// 菜单点击
			handleMenu(type) {
				switch (type) {
					case 'history':
						uni.showToast({ title: '功能开发中', icon: 'none' });
						break;
					case 'feedback':
						uni.showToast({ title: '功能开发中', icon: 'none' });
						break;
					case 'about':
						uni.showModal({
							title: '关于我们',
							content: '一款免费的多平台视频解析工具，支持抖音、小红书、B站、快手、YouTube、视频号等平台的无水印视频下载。',
							showCancel: false,
						});
						break;
				}
			},
		},
	}
</script>

<style scoped>
	.container {
		min-height: 100vh;
		background-color: #f5f6fa;
		padding: 30rpx;
		padding-bottom: 160rpx;
	}

	/* 用户卡片 */
	.user-card {
	background: linear-gradient(135deg, #5cc261 0%, #5dce63 50%, #0be612 100%);
		border-radius: 24rpx;
		padding: 50rpx 40rpx;
		display: flex;
		align-items: center;
		gap: 30rpx;
		margin-bottom: 30rpx;
	}

	.avatar-wrap {
		width: 120rpx;
		height: 120rpx;
		border-radius: 50%;
		overflow: hidden;
		border: 4rpx solid rgba(255, 255, 255, 0.3);
		flex-shrink: 0;
	}

	.avatar {
		width: 100%;
		height: 100%;
	}

	.user-info {
		flex: 1;
	}

	.username {
		font-size: 36rpx;
		font-weight: bold;
		color: #fff;
		display: block;
	}

	.user-desc {
		font-size: 26rpx;
		color: rgba(255, 255, 255, 0.8);
		margin-top: 8rpx;
		display: block;
	}

	.logout-btn {
		font-size: 26rpx;
		color: rgb(255, 255, 255);
		background: rgba(255, 255, 255, 0.2);
		padding: 10rpx 24rpx;
		border-radius: 20rpx;
	}

	/* 统计卡片 */
	.stats-card {
		background: #fff;
		border-radius: 20rpx;
		padding: 40rpx;
		display: flex;
		align-items: center;
		justify-content: space-around;
		margin-bottom: 30rpx;
		box-shadow: 0 4rpx 20rpx rgba(0, 0, 0, 0.05);
	}

	.stat-item {
		display: flex;
		flex-direction: column;
		align-items: center;
	}

	.stat-num {
		font-size: 44rpx;
		font-weight: bold;
		color: #667eea;
	}

	.stat-label {
		font-size: 24rpx;
		color: #999;
		margin-top: 8rpx;
	}

	.stat-divider {
		width: 1rpx;
		height: 60rpx;
		background: #eee;
	}

	/* 管理员设置 */
	.admin-section {
		margin-bottom: 30rpx;
	}

	.section-title {
		font-size: 30rpx;
		font-weight: 600;
		color: #1a1a2e;
		margin-bottom: 20rpx;
		display: block;
	}

	.cookie-card {
		background: #fff;
		border-radius: 20rpx;
		padding: 30rpx;
		box-shadow: 0 4rpx 20rpx rgba(0, 0, 0, 0.05);
	}

	.cookie-label {
		font-size: 28rpx;
		color: #333;
		margin-bottom: 16rpx;
		display: block;
	}

	.cookie-input {
		width: 100%;
		min-height: 160rpx;
		font-size: 26rpx;
		color: #333;
		background: #f8f8f8;
		border-radius: 12rpx;
		padding: 20rpx;
		line-height: 1.5;
	}

	.cookie-placeholder {
		color: #ccc;
	}

	.cookie-btn-row {
		display: flex;
		gap: 20rpx;
		margin-top: 20rpx;
	}

	.btn-save-cookie {
	background: linear-gradient(135deg, #5cc261 0%, #5dce63 50%, #0be612 100%);
		color: #fff;
		padding: 18rpx 48rpx;
		border-radius: 12rpx;
		font-size: 28rpx;
	}

	.btn-clear-cookie {
		background: #fff0f0;
		color: #e74c3c;
		padding: 18rpx 48rpx;
		border-radius: 12rpx;
		font-size: 28rpx;
	}

	.cookie-status {
		font-size: 24rpx;
		color: #666;
		margin-top: 16rpx;
		display: block;
	}

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

	/* 功能菜单 */
	.menu-section {
		background: #fff;
		border-radius: 20rpx;
		overflow: hidden;
		box-shadow: 0 4rpx 20rpx rgba(0, 0, 0, 0.05);
	}

	.menu-item {
		display: flex;
		align-items: center;
		padding: 34rpx 30rpx;
		border-bottom: 1rpx solid #f5f5f5;
	}

	.menu-item:last-child {
		border-bottom: none;
	}

	.menu-icon {
		font-size: 40rpx;
		margin-right: 24rpx;
	}

	.menu-text {
		flex: 1;
		font-size: 30rpx;
		color: #333;
	}

	.menu-arrow {
		font-size: 36rpx;
		color: #ccc;
	}

	/* 底部版本 */
	.footer {
		text-align: center;
		margin-top: 60rpx;
	}

	.version {
		font-size: 24rpx;
		color: #ccc;
	}
</style>
