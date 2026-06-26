/**
 * 统一配置文件
 * 通过 process.env.NODE_ENV 自动切换环境
 * H5 端走代理，小程序端直连服务器
 */

// 测试环境配置
const dev = {
	// 服务器地址（小程序直连用）
	apiBase: 'http://192.168.1.47:3001',
}

// 正式环境配置
const prod = {
	// 服务器地址（正式域名，部署后修改）
	apiBase: 'https://your-domain.com',
}

// 根据编译环境自动选择
const isDev = process.env.NODE_ENV !== 'production'
const envConfig = isDev ? dev : prod

export default {
	...envConfig,
	isDev,
}
