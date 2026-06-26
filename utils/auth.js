/**
 * 登录状态管理
 * 管理用户登录状态、用户信息
 */

// 全局用户状态
let _userInfo = null;
let _isLoggedIn = false;

/**
 * 初始化：从本地存储恢复登录状态
 */
export function init() {
	try {
		const data = uni.getStorageSync('user_info');
		if (data) {
			_userInfo = JSON.parse(data);
			_isLoggedIn = true;
			console.log('[auth] 已恢复登录状态:', _userInfo);
		}
	} catch (e) {
		console.log('[auth] 恢复登录状态失败:', e);
	}
}

/**
 * 是否已登录
 */
export function isLoggedIn() {
	return _isLoggedIn;
}

/**
 * 获取用户信息
 */
export function getUserInfo() {
	return _userInfo;
}

/**
 * 保存用户信息（登录成功后调用）
 */
export function saveUserInfo(info) {
	_userInfo = info;
	_isLoggedIn = true;
	try {
		uni.setStorageSync('user_info', JSON.stringify(info));
	} catch (e) {
		console.error('[auth] 保存用户信息失败:', e);
	}
	console.log('[auth] 用户信息已保存:', info);
}

/**
 * 退出登录
 */
export function logout() {
	_userInfo = null;
	_isLoggedIn = false;
	try {
		uni.removeStorageSync('user_info');
	} catch (e) {}
	console.log('[auth] 已退出登录');
}

/**
 * 微信小程序登录流程
 */
export function wxLogin() {
	return new Promise((resolve, reject) => {
		// #ifdef MP-WEIXIN
		uni.login({
			provider: 'weixin',
			success: (loginRes) => {
				console.log('[auth] wx.login 成功, code:', loginRes.code);
				resolve({ code: loginRes.code });
			},
			fail: (err) => {
				console.error('[auth] wx.login 失败:', err);
				reject(err);
			},
		});
		// #endif

		// #ifdef H5
		console.log('[auth] H5 端暂不支持微信登录');
		resolve({ code: null });
		// #endif
	});
}
