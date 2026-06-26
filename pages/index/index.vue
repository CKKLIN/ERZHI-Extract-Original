<template>
	<view class="container">
		<!-- 顶部标题 -->
		<view class="header">
			<text class="title">二支原片提取</text>
			<text class="subtitle">粘贴视频链接，一键解析下载</text>
		</view>

		<!-- 输入区域 -->
		<view class="input-card">
			<textarea class="url-input" v-model="inputUrl" placeholder="请粘贴视频链接或分享口令" placeholder-class="placeholder"
				:maxlength="-1" auto-height />
			<view class="btn-row">
				<view class="btn-paste" @tap="handlePaste">
					<text>粘贴</text>
				</view>
				<view class="btn-clear" @tap="handleClear" v-if="inputUrl">
					<text>清空</text>
				</view>
			</view>
		</view>

		<!-- 解析按钮 -->
		<view class="btn-parse" :class="{ disabled: !inputUrl || loading }" @tap="handleParse">
			<view v-if="!loading" class="btn-content">
				<text>开始解析</text>
			</view>
			<view v-else class="btn-content loading">
				<view class="loading-spinner"></view>
				<text>解析中...</text>
			</view>
		</view>

		<!-- 支持平台 -->
		<view class="platform-section">
			<text class="section-title">支持平台</text>
			<view class="platform-list">
				<view class="platform-item" v-for="item in platforms" :key="item.name">
					<image class="platform-icon" mode="aspectFit" :src="item.icon" />
					<text class="platform-name">{{ item.name }}</text>
				</view>
			</view>
		</view>

		<!-- 解析历史 -->
		<view class="history-section" v-if="history.length > 0">
			<view class="section-header">
				<text class="section-title">解析历史</text>
				<text class="btn-clear-history" @tap="clearHistory">清空</text>
			</view>
			<view class="history-list">
				<view class="history-item" v-for="(item, index) in history" :key="index" @tap="reuseHistory(item)">
					<view class="history-info">
						<text class="history-platform">{{ item.platform }}</text>
						<text class="history-title">{{ item.title || item.url }}</text>
					</view>
					<text class="history-arrow">›</text>
				</view>
			</view>
		</view>

		<!-- 登录弹窗 -->
		<login-modal :visible="showLoginModal" @close="showLoginModal = false" @login-success="onLoginSuccess" />
	</view>
</template>



<script>
import config from '@/config/index.js';
import { isLoggedIn, getUserInfo, saveUserInfo } from '@/utils/auth.js';
import loginModal from '@/components/login-modal.vue';

export default {
	components: {
		'login-modal': loginModal,
	},
	data() {
		return {
			inputUrl: '',
			loading: false,
			showLoginModal: false,
			pendingParse: false,
			platforms: [
				{ name: '抖音', icon: '/static/douyin.svg' },
				{ name: '小红书', icon: '/static/xiaohoshu.svg' },
				{ name: 'B站', icon: '/static/bilibili.svg' },
				{ name: '快手', icon: '/static/kuaisho.svg' },
				{ name: '视频号', icon: '/static/shipinghao.svg' },
				{ name: 'YouTube', icon: '/static/youtube.svg' },
			],
			history: [],
		}
	},
	onLoad() {
		this.loadHistory();
	},
	onShow() {
		// 每次显示页面时检查登录状态
		console.log('[index] 当前登录状态:', isLoggedIn());
		if (isLoggedIn()) {
			console.log('[index] 用户信息:', getUserInfo());
		}
	},
	methods: {
		// 粘贴
		async handlePaste() {
			// #ifdef H5
			try {
				const text = await navigator.clipboard.readText();
				this.inputUrl = text;
			} catch (e) {
				uni.showToast({ title: '请手动粘贴', icon: 'none' });
			}
			// #endif
			// #ifdef MP-WEIXIN
			uni.getClipboardData({
				success: (res) => {
					if (res.data) {
						this.inputUrl = res.data;
					}
				},
			});
			// #endif
		},

		// 清空输入
		handleClear() {
			this.inputUrl = '';
		},

		// 解析按钮点击
		handleParse() {
			if (!this.inputUrl || this.loading) return;

			// 检查登录状态
			if (!isLoggedIn()) {
				console.log('[index] 用户未登录，弹出登录框');
				this.pendingParse = true;
				this.showLoginModal = true;
				return;
			}

			// 已登录，直接解析
			this.doParse();
		},

		// 登录成功回调
		onLoginSuccess(userInfo) {
			console.log('[index] 登录成功回调:', userInfo);
			saveUserInfo(userInfo);
			this.showLoginModal = false;
			uni.showToast({ title: '登录成功', icon: 'success' });

			// 如果是因为点击解析而触发的登录，登录后自动解析
			if (this.pendingParse) {
				this.pendingParse = false;
				this.doParse();
			}
		},

		// 执行解析
		doParse() {
			this.loading = true;

			// #ifdef H5
			const apiUrl = '/api/video/info';
			// #endif
			// #ifdef MP-WEIXIN
			const apiUrl = config.apiBase + '/api/video/info';
			// #endif

			uni.request({
				url: apiUrl,
				method: 'POST',
				header: { 'Content-Type': 'application/json' },
				data: { url: this.inputUrl.trim() },
				success: (res) => {
					console.log('[index] 请求成功:', JSON.stringify(res.data));
					const data = res.data;

					if (data.success) {
						// 保存到历史
						this.saveHistory({
							url: this.inputUrl.trim(),
							title: data.data.title,
							platform: data.data.platform,
							time: Date.now(),
						});

						// 跳转结果页
						uni.navigateTo({
							url: '/pages/result/result?data=' + encodeURIComponent(JSON.stringify(data.data)),
						});
					} else {
						uni.showToast({ title: data.error || '解析失败', icon: 'none' });
					}
				},
				fail: (err) => {
					console.error('[index] 请求失败:', JSON.stringify(err));
					uni.showToast({ title: '网络请求失败', icon: 'none' });
				},
				complete: () => {
					this.loading = false;
				},
			});
		},

		// 点击历史记录，填充输入框并滚到顶部
		reuseHistory(item) {
			this.inputUrl = item.url;
			uni.pageScrollTo({ scrollTop: 0, duration: 200 });
		},

		// 加载历史
		loadHistory() {
			try {
				const data = uni.getStorageSync('parse_history');
				if (data) {
					this.history = JSON.parse(data);
				}
			} catch (e) { }
		},

		// 保存历史
		saveHistory(item) {
			this.history.unshift(item);
			if (this.history.length > 20) {
				this.history = this.history.slice(0, 20);
			}
			try {
				uni.setStorageSync('parse_history', JSON.stringify(this.history));
			} catch (e) { }
		},

		// 清空历史
		clearHistory() {
			uni.showModal({
				title: '提示',
				content: '确定清空所有解析历史？',
				success: (res) => {
					if (res.confirm) {
						this.history = [];
						try {
							uni.removeStorageSync('parse_history');
						} catch (e) { }
					}
				},
			});
		},
	},
}
</script>

<style scoped>
.container {
	min-height: 100vh;
	background: transparent;
	padding: 30rpx;
	padding-bottom: 160rpx;
}

.header {
	padding: 40rpx 0 30rpx;
}

.title {
	font-size: 48rpx;
	font-weight: bold;
	color: #1a1a2e;
	display: block;
}

.subtitle {
	font-size: 28rpx;
	color: #999;
	margin-top: 10rpx;
	display: block;
}

/* 输入卡片 */
.input-card {
	background: rgba(255, 255, 255, 0.9);
	border-radius: 20rpx;
	padding: 30rpx;
	box-shadow: 0 4rpx 20rpx rgba(76, 175, 80, 0.1);
	backdrop-filter: blur(10px);
}

.url-input {
	width: 100%;
	min-height: 120rpx;
	font-size: 30rpx;
	color: #333;
	line-height: 1.6;
}

.placeholder {
	color: #ccc;
}

.btn-row {
	display: flex;
	gap: 20rpx;
	margin-top: 20rpx;
}

.btn-paste,
.btn-clear {
	padding: 12rpx 24rpx;
	border-radius: 12rpx;
	font-size: 26rpx;
}

.btn-paste {
	background: #e8f5e9;
	color: #2e7d32;
}

.btn-clear {
	background: #fce4ec;
	color: #c62828;
}

/* 解析按钮 */
.btn-parse {
	margin: 30rpx 0;
	background: linear-gradient(135deg, #5cc261 0%, #5dce63 50%, #0be612 100%);
	border-radius: 20rpx;
	padding: 28rpx;
	text-align: center;
	color: #fff;
	font-size: 32rpx;
	font-weight: 600;
	box-shadow: 0 8rpx 30rpx rgba(76, 175, 80, 0.25);
}

.btn-parse.disabled {
	opacity: 0.5;
}

.btn-content {
	display: flex;
	align-items: center;
	justify-content: center;
	gap: 12rpx;
}

.loading-spinner {
	width: 32rpx;
	height: 32rpx;
	border: 4rpx solid rgba(255, 255, 255, 0.3);
	border-top-color: #fff;
	border-radius: 50%;
	animation: spin 0.8s linear infinite;
}

@keyframes spin {
	to {
		transform: rotate(360deg);
	}
}

/* 支持平台 */
.platform-section {
	margin-top: 40rpx;
}

.section-title {
	font-size: 30rpx;
	font-weight: 600;
	color: #2e7d32;
	margin-bottom: 20rpx;
	display: block;
}

.platform-list {
	display: flex;
	flex-wrap: wrap;
	gap: 20rpx;
}

.platform-item {
	background: rgba(255, 255, 255, 0.9);
	border-radius: 16rpx;
	padding: 20rpx 28rpx;
	display: flex;
	align-items: center;
	gap: 10rpx;
	box-shadow: 0 2rpx 10rpx rgba(76, 175, 80, 0.08);
	backdrop-filter: blur(10px);
}

.platform-icon {
	width: 40rpx;
	height: 40rpx;
	margin-right: 10rpx;
	/* background-color: yellowgreen; */
}

.platform-name {
	font-size: 26rpx;
	color: #333;
}

/* 历史记录 */
.history-section {
	margin-top: 40rpx;
}

.section-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	margin-bottom: 20rpx;
}

.btn-clear-history {
	font-size: 26rpx;
	color: #4caf50;
}

.history-list {
	background: rgba(255, 255, 255, 0.9);
	border-radius: 20rpx;
	overflow: hidden;
	box-shadow: 0 2rpx 10rpx rgba(76, 175, 80, 0.08);
	backdrop-filter: blur(10px);
}

.history-item {
	display: flex;
	justify-content: space-between;
	align-items: center;
	padding: 28rpx 30rpx;
	border-bottom: 1rpx solid #f5f5f5;
}

.history-item:last-child {
	border-bottom: none;
}

.history-info {
	flex: 1;
	overflow: hidden;
}

.history-platform {
	font-size: 22rpx;
	color: #2e7d32;
	background: #e8f5e9;
	padding: 4rpx 12rpx;
	border-radius: 6rpx;
	margin-right: 12rpx;
}

.history-title {
	font-size: 28rpx;
	color: #333;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}

.history-arrow {
	font-size: 36rpx;
	color: #ccc;
	margin-left: 20rpx;
}
</style>
