<script>
	import { init, autoLogin, isLoggedIn } from '@/utils/auth.js';

	export default {
		async onLaunch() {
			console.log('App Launch');
			// 1. 恢复本地存储的登录状态
			init();

			// 2. 后台静默登录（没有 openid 则自动 wx.login → 后端换）
			if (!isLoggedIn()) {
				console.log('[App] 未登录，开始后台静默登录...');
				await autoLogin();
			} else {
				console.log('[App] 已登录，跳过后台登录');
			}
		},
		onShow() {
			console.log('App Show');
		},
		onHide() {
			console.log('App Hide');
		}
	}
</script>

<style>
	/* 全局公共样式 */
	page {
		font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
		background: linear-gradient(180deg, #ffffff 0%, #f0f9f0 50%, #e8f5e9 100%);
		min-height: 100vh;
	}
</style>
