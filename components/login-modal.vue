<template>
	<view class="modal-mask" v-if="visible" @tap="handleClose">
		<view class="modal-content" @tap.stop>
			<!-- 关闭按钮 -->
			<view class="btn-close" @tap="handleClose">
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

			<!-- ========== 头像 ========== -->
			<!-- button open-type="chooseAvatar" 获取微信真实头像 -->
			<view class="avatar-section">
				<button
					class="avatar-btn-native"
					open-type="chooseAvatar"
					@chooseavatar="onChooseAvatar"
				>
					<view class="avatar-wrapper">
						<image
							v-if="avatarUrl"
							class="avatar-img"
							:src="avatarUrl"
							mode="aspectFill"
						/>
						<view v-else class="avatar-placeholder">
							<text class="placeholder-icon">👤</text>
						</view>
						<view class="avatar-badge">
							<text class="badge-icon">📷</text>
						</view>
					</view>
				</button>
				<text class="avatar-tip" @tap="handleAvatarFallback">
					{{ avatarUrl ? '点击更换头像' : '点击设置头像' }}
				</text>
			</view>

			<!-- ========== 昵称 ========== -->
			<!-- input type="nickname"：键盘弹出「微信昵称」快捷填入按钮 -->
			<view class="input-section">
				<view class="input-wrapper">
					<input
						class="nickname-input"
						type="nickname"
						:value="nickname"
						placeholder="点击输入昵称（可使用微信昵称）"
						placeholder-class="input-placeholder"
						:focus="nicknameFocus"
						@input="onNicknameInput"
						@nicknamereview="onNicknameReview"
						@blur="onNicknameBlur"
					/>
					<text
						class="input-arrow"
						v-if="!nickname"
						@tap.stop="handleNicknameFallback"
					>›</text>
				</view>
			</view>

			<!-- 确认登录 -->
			<view class="btn-login" :class="{ disabled: loading }" @tap="handleLogin">
				<view class="btn-inner">
					<view class="loading-spinner" v-if="loading"></view>
					<text class="btn-text">{{ loading ? '登录中...' : '确认登录' }}</text>
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
	import { getOpenId } from '@/utils/auth.js';

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
				nicknameFocus: false,
			}
		},
		methods: {
			// ======== 头像 —— 首选：chooseAvatar 原生回调 ========
			onChooseAvatar(e) {
				console.log('[login-modal] chooseAvatar 触发');
				const url = e.detail?.avatarUrl || e.avatarUrl || '';
				if (url) {
					this.avatarUrl = url;
					console.log('[login-modal] 微信头像设置成功:', url);
				}
			},

			// ======== 头像 —— 兜底：点击下方文字直接选择 ========
			handleAvatarFallback() {
				console.log('[login-modal] 头像兜底 —— 打开相册');
				uni.chooseImage({
					count: 1,
					sizeType: ['compressed'],
					sourceType: ['album', 'camera'],
					success: (res) => {
						this.avatarUrl = res.tempFilePaths[0];
						console.log('[login-modal] 相册头像:', this.avatarUrl);
					},
				});
			},

			// ======== 昵称 —— 首选：type="nickname" 原生输入 ========
			onNicknameInput(e) {
				const val = e.detail?.value ?? e.value ?? '';
				if (val) {
					this.nickname = val;
					console.log('[login-modal] 昵称输入:', val);
				}
			},

			onNicknameReview(e) {
				console.log('[login-modal] nicknamereview:', JSON.stringify(e));
			},

			onNicknameBlur() {
				this.nicknameFocus = false;
			},

			// ======== 昵称 —— 兜底：点击箭头直接手动输入 ========
			handleNicknameFallback() {
				if (this.nickname) return;
				console.log('[login-modal] 昵称兜底 —— 聚焦输入框');
				this.focusNickname();
			},

			// 聚焦输入框
			focusNickname() {
				this.$nextTick(() => {
					this.nicknameFocus = true;
				});
			},

			// ======== 关闭 ========
			handleClose() {
				this.$emit('close');
			},

			// ======== 确认（登录已在后台完成，这里只保存资料） ========
			handleLogin() {
				if (this.loading) return;

				const userInfo = {
					nickName: this.nickname.trim() || ('微信用户' + (getOpenId().slice(-6) || '')),
					avatarUrl: this.avatarUrl || '',
					openid: getOpenId(),
				};

				console.log('[login-modal] 保存用户资料:', JSON.stringify(userInfo));
				this.$emit('login-success', userInfo);
			},
		},
	}
</script>

<style scoped>
	.modal-mask {
		position: fixed;
		top: 0; left: 0; right: 0; bottom: 0;
		background: rgba(0,0,0,0.6);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 999;
	}

	.modal-content {
		position: relative;
		width: 620rpx;
		background: #fff;
		border-radius: 32rpx;
		padding: 60rpx 44rpx 44rpx;
		box-shadow: 0 30rpx 80rpx rgba(0,0,0,0.15);
		overflow: hidden;
	}

	.btn-close {
		position: absolute;
		top: 24rpx; right: 24rpx;
		width: 56rpx; height: 56rpx;
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 10;
	}
	.close-icon { font-size: 32rpx; color: #999; }

	.header-decor {
		position: absolute;
		top: 0; left: 0; right: 0;
		height: 200rpx;
		overflow: hidden;
	}
	.decor-circle { position: absolute; border-radius: 50%; }
	.c1 {
		width: 200rpx; height: 200rpx;
		background: linear-gradient(135deg, rgba(129,199,132,0.3), rgba(102,187,106,0.1));
		top: -60rpx; left: -40rpx;
	}
	.c2 {
		width: 160rpx; height: 160rpx;
		background: linear-gradient(135deg, rgba(76,175,80,0.2), rgba(129,199,132,0.05));
		top: -30rpx; right: 30rpx;
	}
	.c3 {
		width: 100rpx; height: 100rpx;
		background: linear-gradient(135deg, rgba(200,230,201,0.5), rgba(165,214,167,0.2));
		top: 40rpx; left: 50%;
	}

	.modal-header {
		text-align: center;
		margin-bottom: 40rpx;
		position: relative;
		z-index: 1;
	}
	.modal-title { font-size: 44rpx; font-weight: 700; color: #1b5e20; display: block; }
	.modal-subtitle { font-size: 26rpx; color: #81c784; margin-top: 12rpx; display: block; }

	/* 头像 */
	.avatar-section {
		display: flex;
		flex-direction: column;
		align-items: center;
		margin-bottom: 30rpx;
	}

	/* chooseAvatar 按钮：彻底重置样式 */
	.avatar-btn-native {
		padding: 0;
		margin: 0;
		background: transparent;
		border: none;
		border-radius: 0;
		line-height: 1;
		width: 160rpx;
		height: 160rpx;
		display: flex;
		align-items: center;
		justify-content: center;
	}
	.avatar-btn-native::after {
		display: none !important;
		border: none !important;
	}

	.avatar-wrapper {
		position: relative;
		width: 160rpx;
		height: 160rpx;
	}

	.avatar-img {
		width: 160rpx; height: 160rpx;
		border-radius: 50%;
		border: 6rpx solid #fff;
		box-shadow: 0 8rpx 24rpx rgba(76,175,80,0.2);
	}

	.avatar-placeholder {
		width: 160rpx; height: 160rpx;
		border-radius: 50%;
		background: linear-gradient(135deg, #e8f5e9, #c8e6c9);
		display: flex;
		align-items: center;
		justify-content: center;
		border: 6rpx solid #fff;
		box-shadow: 0 8rpx 24rpx rgba(76,175,80,0.2);
	}
	.placeholder-icon { font-size: 64rpx; }

	.avatar-badge {
		position: absolute;
		bottom: 4rpx; right: 4rpx;
		width: 48rpx; height: 48rpx;
		background: linear-gradient(135deg, #66bb6a, #4caf50);
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		border: 4rpx solid #fff;
		box-shadow: 0 4rpx 12rpx rgba(76,175,80,0.3);
	}
	.badge-icon { font-size: 24rpx; }

	.avatar-tip {
		font-size: 24rpx;
		color: #4caf50;
		margin-top: 12rpx;
		font-weight: 500;
	}

	/* 昵称 */
	.input-section { margin-bottom: 36rpx; }
	.input-wrapper {
		display: flex;
		align-items: center;
		background: #f5faf5;
		border: 2rpx solid #e0f0e0;
		border-radius: 20rpx;
		padding: 0 28rpx;
	}
	.nickname-input {
		flex: 1;
		border: none;
		padding: 26rpx 0;
		font-size: 30rpx;
		color: #2e7d32;
		background: transparent;
	}
	.input-placeholder { color: #b0d4b1; }
	.input-arrow { font-size: 36rpx; color: #ccc; }
	.input-done { font-size: 26rpx; color: #4caf50; font-weight: 500; }

	/* 确认登录 */
	.btn-login {
		background: linear-gradient(135deg, #66bb6a, #4caf50 50%, #43a047);
		border-radius: 24rpx;
		overflow: hidden;
		box-shadow: 0 10rpx 30rpx rgba(76,175,80,0.3);
	}
	.btn-login.disabled { opacity: 0.6; }
	.btn-inner {
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 28rpx;
		gap: 12rpx;
	}
	.btn-text { color: #fff; font-size: 32rpx; font-weight: 600; letter-spacing: 4rpx; }

	.loading-spinner {
		width: 32rpx; height: 32rpx;
		border: 4rpx solid rgba(255,255,255,0.3);
		border-top-color: #fff;
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}
	@keyframes spin { to { transform: rotate(360deg); } }

	.footer-tip { text-align: center; margin-top: 20rpx; }
	.tip-text { font-size: 22rpx; color: #b0b0b0; }
	.link { font-size: 22rpx; color: #66bb6a; font-weight: 500; }
</style>
