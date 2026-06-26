<template>
	<view class="modal-mask" v-if="visible" @tap.stop="handleClose">
		<view class="modal-content" @tap.stop>
			<!-- 关闭按钮 -->
			<view class="btn-close" @tap.stop="handleClose">
				<text class="close-icon">✕</text>
			</view>

			<!-- 顶部装饰 -->
			<view class="header-decor">
				<view class="decor-circle c1"></view>
				<view class="decor-circle c2"></view>
				<view class="decor-circle c3"></view>
			</view>

			<!-- 标题 -->
			<view class="modal-header">
				<text class="modal-title">欢迎使用</text>
				<text class="modal-subtitle">登录后解锁完整功能</text>
			</view>

			<!-- 头像选择 -->
			<view class="avatar-section">
				<button
					class="avatar-btn"
					open-type="chooseAvatar"
					@chooseavatar="onChooseAvatar"
				>
					<view class="avatar-wrapper">
						<view class="avatar-img" v-if="!avatarUrl">
							<text class="avatar-icon"></text>
						</view>
						<image
							v-else
							class="avatar-img"
							:src="avatarUrl"
							mode="aspectFill"
						/>
						<view class="avatar-badge">
							<text class="badge-icon">📷</text>
						</view>
					</view>
					<text class="avatar-tip">{{ avatarUrl ? '更换头像' : '选择头像' }}</text>
				</button>
			</view>

			<!-- 昵称输入 -->
			<view class="input-section">
				<view class="input-wrapper">
					<text class="input-icon"></text>
					<input
						class="nickname-input"
						type="nickname"
						:value="nickname"
						placeholder="给自己取个名字吧"
						placeholder-class="input-placeholder"
						@input="onNicknameInput"
					/>
				</view>
			</view>

			<!-- 登录按钮 -->
			<view class="btn-login" :class="{ disabled: loading }" @tap="handleLogin">
				<view class="btn-inner">
					<view class="loading-spinner" v-if="loading"></view>
					<text class="btn-text">{{ loading ? '登录中...' : '一键登录' }}</text>
				</view>
			</view>

			<!-- 底部提示 -->
			<view class="footer-tip">
				<text class="tip-text">登录即表示同意</text>
				<text class="link">《用户协议》</text>
				<text class="tip-text">和</text>
				<text class="link">《隐私政策》</text>
			</view>
		</view>
	</view>
</template>

<script>
	import config from '@/config/index.js';

	export default {
		name: 'login-modal',
		props: {
			visible: {
				type: Boolean,
				default: false,
			},
		},
		data() {
			return {
				avatarUrl: '',
				nickname: '',
				loading: false,
			}
		},
		methods: {
			// 选择头像回调
			onChooseAvatar(e) {
				const avatarUrl = e.detail.avatarUrl;
				console.log('[login-modal] 选择头像:', avatarUrl);
				this.avatarUrl = avatarUrl;
			},

			// 昵称输入
			onNicknameInput(e) {
				this.nickname = e.detail.value;
			},

			// 关闭弹窗
			handleClose() {
				this.$emit('close');
			},

			// 登录
			async handleLogin() {
				if (this.loading) return;

				this.loading = true;

				try {
					// #ifdef MP-WEIXIN
					// 1. 获取 wx.login code
					const loginRes = await new Promise((resolve, reject) => {
						uni.login({
							provider: 'weixin',
							success: resolve,
							fail: reject,
						});
					});

					console.log('[login-modal] wx.login 成功, code:', loginRes.code);

					// 2. 发送 code 到后端换取 openid
					let openid = '';
					const openidRes = await new Promise((resolve) => {
						uni.request({
							url: config.apiBase + '/api/weixin/login',
							method: 'POST',
							header: { 'Content-Type': 'application/json' },
							data: { code: loginRes.code },
							success: (res) => {
								console.log('[login-modal] 后端响应:', JSON.stringify(res.data));
								if (res.data && res.data.success) {
									resolve(res.data.data.openid || '');
								} else {
									resolve('');
								}
							},
							fail: (err) => {
								console.warn('[login-modal] 请求失败:', JSON.stringify(err));
								resolve('');
							},
						});
					});
					openid = openidRes;
					console.log('[login-modal] 获取到 openid:', openid);

					const userInfo = {
						nickName: this.nickname.trim() || '微信用户',
						avatarUrl: this.avatarUrl || '',
						code: loginRes.code,
						openid: openid,
					};

					// 打印用户信息到控制台
					console.log('========== 用户登录信息 ==========');
					console.log('昵称:', userInfo.nickName);
					console.log('头像:', userInfo.avatarUrl);
					console.log('微信 code:', userInfo.code);
					console.log('openid:', userInfo.openid || '未获取');
					console.log('==================================');

					this.$emit('login-success', userInfo);
					// #endif

					// #ifdef H5
					const userInfo = {
						nickName: this.nickname.trim() || '用户',
						avatarUrl: this.avatarUrl || '',
						code: null,
						openid: '',
					};

					console.log('========== 用户登录信息 ==========');
					console.log('昵称:', userInfo.nickName);
					console.log('头像:', userInfo.avatarUrl);
					console.log('==================================');

					this.$emit('login-success', userInfo);
					// #endif
				} catch (err) {
					console.error('[login-modal] 登录失败:', err);
					uni.showToast({ title: '登录失败，请重试', icon: 'none' });
				} finally {
					this.loading = false;
				}
			},
		},
	}
</script>

<style scoped>
	.modal-mask {
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		bottom: 0;
		background: rgba(0, 0, 0, 0.6);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 999;
		backdrop-filter: blur(4px);
	}

	.modal-content {
		position: relative;
		width: 620rpx;
		background: #ffffff;
		border-radius: 32rpx;
		padding: 60rpx 44rpx 44rpx;
		box-shadow: 0 30rpx 80rpx rgba(0, 0, 0, 0.15);
		overflow: hidden;
	}

	/* 关闭按钮 */
	.btn-close {
		position: absolute;
		top: 24rpx;
		right: 24rpx;
		width: 56rpx;
		height: 56rpx;
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 10;
	}

	.close-icon {
		font-size: 32rpx;
		color: #999;
	}

	/* 顶部装饰 */
	.header-decor {
		position: absolute;
		top: 0;
		left: 0;
		right: 0;
		height: 200rpx;
		overflow: hidden;
	}

	.decor-circle {
		position: absolute;
		border-radius: 50%;
	}

	.decor-circle.c1 {
		width: 200rpx;
		height: 200rpx;
		background: linear-gradient(135deg, rgba(129, 199, 132, 0.3), rgba(102, 187, 106, 0.1));
		top: -60rpx;
		left: -40rpx;
	}

	.decor-circle.c2 {
		width: 160rpx;
		height: 160rpx;
		background: linear-gradient(135deg, rgba(76, 175, 80, 0.2), rgba(129, 199, 132, 0.05));
		top: -30rpx;
		right: 30rpx;
	}

	.decor-circle.c3 {
		width: 100rpx;
		height: 100rpx;
		background: linear-gradient(135deg, rgba(200, 230, 201, 0.5), rgba(165, 214, 167, 0.2));
		top: 40rpx;
		left: 50%;
	}

	/* 标题 */
	.modal-header {
		text-align: center;
		margin-bottom: 40rpx;
		position: relative;
		z-index: 1;
	}

	.modal-title {
		font-size: 44rpx;
		font-weight: 700;
		color: #1b5e20;
		display: block;
		letter-spacing: 2rpx;
	}

	.modal-subtitle {
		font-size: 26rpx;
		color: #81c784;
		margin-top: 12rpx;
		display: block;
	}

	/* 头像 */
	.avatar-section {
		display: flex;
		justify-content: center;
		margin-bottom: 36rpx;
		position: relative;
		z-index: 1;
	}

	.avatar-btn {
		background: none;
		border: none;
		padding: 0;
		margin: 0;
		line-height: normal;
		display: flex;
		flex-direction: column;
		align-items: center;
	}

	.avatar-btn::after {
		display: none;
	}

	.avatar-wrapper {
		position: relative;
		width: 160rpx;
		height: 160rpx;
	}

	.avatar-img {
		width: 160rpx;
		height: 160rpx;
		border-radius: 50%;
		background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
		display: flex;
		align-items: center;
		justify-content: center;
		border: 6rpx solid #ffffff;
		box-shadow: 0 8rpx 24rpx rgba(76, 175, 80, 0.2);
	}

	.avatar-icon {
		font-size: 64rpx;
	}

	.avatar-badge {
		position: absolute;
		bottom: 4rpx;
		right: 4rpx;
		width: 48rpx;
		height: 48rpx;
		background: linear-gradient(135deg, #66bb6a, #4caf50);
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		border: 4rpx solid #ffffff;
		box-shadow: 0 4rpx 12rpx rgba(76, 175, 80, 0.3);
	}

	.badge-icon {
		font-size: 24rpx;
	}

	.avatar-tip {
		font-size: 24rpx;
		color: #4caf50;
		margin-top: 16rpx;
		font-weight: 500;
	}

	/* 昵称 */
	.input-section {
		margin-bottom: 36rpx;
		position: relative;
		z-index: 1;
	}

	.input-wrapper {
		display: flex;
		align-items: center;
		background: #f5faf5;
		border: 2rpx solid #e0f0e0;
		border-radius: 20rpx;
		padding: 0 28rpx;
		transition: border-color 0.2s;
	}

	.input-icon {
		font-size: 36rpx;
		margin-right: 16rpx;
	}

	.nickname-input {
		flex: 1;
		border: none;
		padding: 26rpx 0;
		font-size: 30rpx;
		color: #2e7d32;
		background: transparent;
	}

	.input-placeholder {
		color: #b0d4b1;
	}

	/* 登录按钮 */
	.btn-login {
		background: linear-gradient(135deg, #66bb6a 0%, #4caf50 50%, #43a047 100%);
		border-radius: 24rpx;
		padding: 0;
		overflow: hidden;
		box-shadow: 0 10rpx 30rpx rgba(76, 175, 80, 0.3);
		position: relative;
		z-index: 1;
	}

	.btn-inner {
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 30rpx;
		gap: 12rpx;
	}

	.btn-text {
		color: #fff;
		font-size: 32rpx;
		font-weight: 600;
		letter-spacing: 4rpx;
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

	.btn-login.disabled {
		opacity: 0.6;
	}

	/* 底部提示 */
	.footer-tip {
		text-align: center;
		margin-top: 28rpx;
		position: relative;
		z-index: 1;
	}

	.tip-text {
		font-size: 22rpx;
		color: #b0b0b0;
	}

	.footer-tip .link {
		font-size: 22rpx;
		color: #66bb6a;
		font-weight: 500;
	}
</style>
