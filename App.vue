<script>
	import { init } from '@/utils/auth.js';

	export default {
		onLaunch: function() {
			console.log('App Launch');
			// 初始化登录状态
			init();
		},
		onShow: function() {
			console.log('App Show');
		},
		onHide: function() {
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
