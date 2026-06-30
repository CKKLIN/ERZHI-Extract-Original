/**
 * 登录状态管理
 * 管理用户登录状态、用户信息
 * 支持后台静默登录 + 用户主动完善资料
 */

import config from '@/config/index.js';

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
			// 有 openid 就算已登录（后台静默登录完成）
			_isLoggedIn = !!(_userInfo && _userInfo.openid);
			// 兜底：如果之前没有昵称，自动生成默认昵称
			if (_isLoggedIn && !_userInfo.nickName) {
				_userInfo.nickName = '微信用户' + (_userInfo.openid.slice(-6) || '');
				uni.setStorageSync('user_info', JSON.stringify(_userInfo));
			}
			console.log('[auth] 已恢复登录状态, openid:', _userInfo?.openid);
		}
	} catch (e) {
		console.log('[auth] 恢复登录状态失败:', e);
	}
}

/**
 * 是否已登录（有 openid 即视为已登录）
 */
export function isLoggedIn() {
	return _isLoggedIn;
}

/**
 * 是否为管理员（role === 0）
 */
export function isAdmin() {
	return _isLoggedIn && _userInfo && _userInfo.role === 0;
}

/**
 * 是否已完善资料（有头像或昵称）
 */
export function hasProfile() {
	return _isLoggedIn && _userInfo && !!(
		(_userInfo.nickName && _userInfo.nickName !== '微信用户') ||
		_userInfo.avatarUrl
	);
}

/**
 * 获取用户信息
 */
export function getUserInfo() {
	return _userInfo;
}

/**
 * 获取 openid
 */
export function getOpenId() {
	return _userInfo?.openid || '';
}

/**
 * 保存用户信息
 */
export function saveUserInfo(info) {
	// 合并而非覆盖，避免丢失已有的 openid
	_userInfo = { ..._userInfo, ...info };
	_isLoggedIn = !!(_userInfo && _userInfo.openid);
	try {
		uni.setStorageSync('user_info', JSON.stringify(_userInfo));
	} catch (e) {
		console.error('[auth] 保存用户信息失败:', e);
	}
	console.log('[auth] 用户信息已保存:', _userInfo);
	// 同步到后端数据库
	syncProfile();
}

/**
 * 将用户资料同步到后端数据库
 */
export function syncProfile() {
	if (!_isLoggedIn || !_userInfo?.openid) return;
	const data = {
		openid: _userInfo.openid,
		nickname: _userInfo.nickName || '',
		avatarUrl: _userInfo.avatarUrl || '',
	};
	uni.request({
		url: config.apiBase + '/api/weixin/update-profile',
		method: 'POST',
		header: { 'Content-Type': 'application/json' },
		data: data,
		success: (res) => {
			console.log('[auth] 资料已同步到后端');
		},
		fail: (err) => {
			console.warn('[auth] 同步资料失败:', JSON.stringify(err));
		},
	});
}

/**
 * 后台静默登录 —— App 启动时调用
 * wx.login 获取 code → 后端换 openid → 静默存储
 */
export function autoLogin() {
	return new Promise(async (resolve) => {
		// #ifdef MP-WEIXIN
		// 如果已有 openid，跳过
		if (_isLoggedIn && _userInfo?.openid) {
			console.log('[auth] 已有 openid，跳过自动登录');
			resolve(_userInfo);
			return;
		}

		try {
			// 1. wx.login
			const loginRes = await new Promise((resolve, reject) => {
				uni.login({
					provider: 'weixin',
					success: resolve,
					fail: reject,
				});
			});

			console.log('[auth] 后台 wx.login 成功, code:', loginRes.code);

			// 2. 后端换 openid
			const res = await new Promise((resolve) => {
				uni.request({
					url: config.apiBase + '/api/weixin/login',
					method: 'POST',
					header: { 'Content-Type': 'application/json' },
					data: { code: loginRes.code },
					success: (res) => {
						console.log('[auth] 后端登录响应:', JSON.stringify(res.data));
						resolve(res.data);
					},
					fail: (err) => {
						console.warn('[auth] 后端登录请求失败:', JSON.stringify(err));
						resolve(null);
					},
				});
			});

			if (res && res.success) {
				const openid = res.data?.openid || '';
				// 优先使用后端数据库中的资料，没有则自动生成默认昵称
				const backendNickname = res.data?.nickname;
				const backendAvatar = res.data?.avatarUrl;
				const info = {
					openid: openid,
					role: res.data?.role !== undefined ? Number(res.data.role) : 1,
					nickName: backendNickname || ('微信用户' + (openid.slice(-6) || '')),
					avatarUrl: backendAvatar || '',
				};
				saveUserInfo(info);
				console.log('[auth] 后台静默登录成功, openid:', info.openid);
			} else {
				console.warn('[auth] 后台静默登录失败, 后端返回:', res);
				_isLoggedIn = false;
			}
		} catch (e) {
			console.error('[auth] 后台静默登录异常:', e);
			_isLoggedIn = false;
		}
		// #endif

		// #ifdef H5
		console.log('[auth] H5 端无需后台登录');
		// #endif

		resolve(_userInfo);
	});
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
 * 微信小程序登录流程（供需要主动登录的场景调用）
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
