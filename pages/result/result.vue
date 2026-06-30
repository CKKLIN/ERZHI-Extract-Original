<template>
	<view class="container">
		<!-- 视频封面 -->
		<view class="cover-section" v-if="data.poster">
			<image class="cover" :src="data.poster" mode="aspectFill" />
		</view>

		<!-- 视频信息 -->
		<view class="info-card">
			<text class="title">{{ data.title || '未知标题' }}</text>
			<view class="meta-row">
				<text class="platform-tag">{{ platformName }}</text>
			</view>
			<text class="desc" v-if="data.description">{{ data.description }}</text>
		</view>

		<!-- 下载链接 -->
		<view class="download-section" v-if="hasDownloadLinks">
			<text class="section-title">下载链接</text>

			<view class="link-item" v-if="data.downloadLinks.combined">
				<view class="link-info">
					<text class="link-type">完整视频</text>
					<text class="link-quality" v-if="data.downloadLinks.combined.quality">{{ data.downloadLinks.combined.quality }}</text>
				</view>
				<view class="btn-actions">
					<view class="btn-download" @tap="handleDownload('combined')">
						<text>下载</text>
					</view>
					<view class="btn-copy" @tap="copyDownloadLink('combined')">
						<text>复制</text>
					</view>
				</view>
			</view>

			<view class="link-item" v-if="data.downloadLinks.video">
				<view class="link-info">
					<text class="link-type">纯画面</text>
					<text class="link-quality" v-if="data.downloadLinks.video.quality">{{ data.downloadLinks.video.quality }}</text>
				</view>
				<view class="btn-actions">
					<view class="btn-download" @tap="handleDownload('video')">
						<text>下载</text>
					</view>
					<view class="btn-copy" @tap="copyDownloadLink('video')">
						<text>复制</text>
					</view>
				</view>
			</view>

			<view class="link-item" v-if="data.downloadLinks.audio">
				<view class="link-info">
					<text class="link-type">纯音频</text>
					<text class="link-quality" v-if="data.downloadLinks.audio.quality">{{ data.downloadLinks.audio.quality }}</text>
				</view>
				<view class="btn-actions">
					<view class="btn-download" @tap="handleDownload('audio')">
						<text>下载</text>
					</view>
					<view class="btn-copy" @tap="copyDownloadLink('audio')">
						<text>复制</text>
					</view>
				</view>
			</view>
		</view>

		<!-- 封面图下载 -->
		<view class="download-section" v-if="data.poster">
			<text class="section-title">封面图</text>
			<view class="link-item">
				<view class="link-info">
					<text class="link-type">封面图片</text>
				</view>
				<view class="btn-actions">
					<view class="btn-download" @tap="handleDownloadPoster">
						<text>下载</text>
					</view>
					<view class="btn-copy" @tap="copyPosterLink">
						<text>复制</text>
					</view>
				</view>
			</view>
		</view>

		<!-- 视频号提示 -->
		<view class="weixin-notice" v-if="data.platform === 'weixin' && !hasDownloadLinks">
			<text class="notice-icon">视频号</text>
			<text class="notice-title">视频号内容</text>
			<text class="notice-desc">请在微信 PC 客户端播放该视频后重试，或联系管理员配置解析服务</text>
			<view class="btn-copy-link" @tap="copyLink">
				<text>复制链接</text>
			</view>
		</view>

		<!-- 视频预览 -->
		<view class="preview-section" v-if="previewUrl">
			<text class="section-title">视频预览</text>
			<video
				class="video-player"
				:src="previewUrl"
				:poster="data.poster"
				controls
				@error="onVideoError"
				@play="onVideoPlay"
			/>
		</view>
	</view>
</template>

<script>
	import config from '@/config/index.js';

	export default {
		data() {
			return {
				data: {},
				previewUrl: '',
			}
		},
		computed: {
			platformName() {
				const map = {
					douyin: '抖音',
					xiaohongshu: '小红书',
					bilibili: 'B站',
					kuaishou: '快手',
					youtube: 'YouTube',
					weixin: '视频号',
				};
				return map[this.data.platform] || this.data.platform || '未知';
			},
			videoUrl() {
				if (this.data.downloadLinks) {
					if (this.data.downloadLinks.combined) {
						return this.data.downloadLinks.combined.url;
					}
					if (this.data.downloadLinks.video) {
						return this.data.downloadLinks.video.url;
					}
				}
				return '';
			},
			imageUrl() {
				if (this.data.picInfo && this.data.picInfo.length > 0) {
					const pic = this.data.picInfo[0];
					return pic.url || pic;
				}
				if (this.data.poster) {
					return this.data.poster;
				}
				return '';
			},
			hasDownloadLinks() {
				if (!this.data.downloadLinks) return false;
				return this.data.downloadLinks.combined ||
					   this.data.downloadLinks.video ||
					   this.data.downloadLinks.audio;
			},
		},
		onLoad(options) {
			if (options.data) {
				try {
					this.data = JSON.parse(decodeURIComponent(options.data));
					// 设置预览地址
					if (this.data.platform === 'weixin') {
						// 视频号：通过后端代理播放（后端会解密 finder.video.qq.com 链接）
						const dl = this.data.downloadLinks;
						const rawUrl = (dl && dl.combined && dl.combined.url)
							|| (dl && dl.video && dl.video.url);
						if (rawUrl) {
							// #ifdef MP-WEIXIN
							this.previewUrl = this.getProxyUrl(rawUrl);
							// #endif
							// #ifdef H5
							this.previewUrl = rawUrl;
							// #endif
						}
					} else if (this.data.downloadLinks && this.data.downloadLinks.combined) {
						const rawUrl = this.data.downloadLinks.combined.url;
						// #ifdef H5
						this.previewUrl = rawUrl;
						// #endif
						// #ifdef MP-WEIXIN
						// 小程序中走代理，绕过 CDN Referer 限制
						this.previewUrl = this.getProxyUrl(rawUrl);
						// #endif
					}
				} catch (e) {
					uni.showToast({ title: '数据解析失败', icon: 'none' });
				}
			}
		},
		methods: {
			// 获取代理下载地址
			getProxyUrl(url) {
				if (!url) return '';
				// #ifdef H5
				return '/api/video/download?url=' + encodeURIComponent(url);
				// #endif
				// #ifdef MP-WEIXIN
				return config.apiBase + '/api/video/download?url=' + encodeURIComponent(url);
				// #endif
			},

			// 复制链接
			copyLink() {
				const link = this.data.url || '';
				if (!link) {
					uni.showToast({ title: '没有可复制的链接', icon: 'none' });
					return;
				}
				// #ifdef MP-WEIXIN
				uni.setClipboardData({
					data: link,
					success: () => {
						uni.showToast({ title: '链接已复制', icon: 'success' });
					},
				});
				// #endif
				// #ifdef H5
				navigator.clipboard.writeText(link).then(() => {
					uni.showToast({ title: '链接已复制', icon: 'success' });
				}).catch(() => {
					uni.showToast({ title: '复制失败', icon: 'none' });
				});
				// #endif
			},

			// 复制视频链接
			copyVideoLink() {
				const link = this.videoUrl;
				if (!link) {
					uni.showToast({ title: '没有可复制的链接', icon: 'none' });
					return;
				}
				// #ifdef MP-WEIXIN
				uni.setClipboardData({
					data: link,
					success: () => {
						uni.showToast({ title: '视频链接已复制', icon: 'success' });
					},
				});
				// #endif
				// #ifdef H5
				navigator.clipboard.writeText(link).then(() => {
					uni.showToast({ title: '视频链接已复制', icon: 'success' });
				}).catch(() => {
					uni.showToast({ title: '复制失败', icon: 'none' });
				});
				// #endif
			},

			// 复制图片链接
			copyImageLink() {
				const link = this.imageUrl;
				if (!link) {
					uni.showToast({ title: '没有可复制的链接', icon: 'none' });
					return;
				}
				// #ifdef MP-WEIXIN
				uni.setClipboardData({
					data: link,
					success: () => {
						uni.showToast({ title: '图片链接已复制', icon: 'success' });
					},
				});
				// #endif
				// #ifdef H5
				navigator.clipboard.writeText(link).then(() => {
					uni.showToast({ title: '图片链接已复制', icon: 'success' });
				}).catch(() => {
					uni.showToast({ title: '复制失败', icon: 'none' });
				});
				// #endif
			},

			// 复制下载链接
			copyDownloadLink(type) {
				const link = this.data.downloadLinks[type];
				if (!link || !link.url) {
					uni.showToast({ title: '链接不存在', icon: 'none' });
					return;
				}
				// #ifdef MP-WEIXIN
				uni.setClipboardData({
					data: link.url,
					success: () => {
						uni.showToast({ title: '链接已复制', icon: 'success' });
					},
				});
				// #endif
				// #ifdef H5
				navigator.clipboard.writeText(link.url).then(() => {
					uni.showToast({ title: '链接已复制', icon: 'success' });
				}).catch(() => {
					uni.showToast({ title: '复制失败', icon: 'none' });
				});
				// #endif
			},

			// 复制封面链接
			copyPosterLink() {
				const link = this.data.poster;
				if (!link) {
					uni.showToast({ title: '封面不存在', icon: 'none' });
					return;
				}
				// #ifdef MP-WEIXIN
				uni.setClipboardData({
					data: link,
					success: () => {
						uni.showToast({ title: '封面链接已复制', icon: 'success' });
					},
				});
				// #endif
				// #ifdef H5
				navigator.clipboard.writeText(link).then(() => {
					uni.showToast({ title: '封面链接已复制', icon: 'success' });
				}).catch(() => {
					uni.showToast({ title: '复制失败', icon: 'none' });
				});
				// #endif
			},

			// 下载封面
			handleDownloadPoster() {
				const link = this.data.poster;
				if (!link) {
					uni.showToast({ title: '封面不存在', icon: 'none' });
					return;
				}

				const proxyUrl = this.getProxyUrl(link);
				const filename = '二支-' + (this.data.title || '封面').substring(0, 10);

				// #ifdef H5
				const a = document.createElement('a');
				a.href = proxyUrl + '&filename=' + encodeURIComponent(filename);
				a.download = filename + '.jpg';
				a.click();
				// #endif

				// #ifdef MP-WEIXIN
				uni.showLoading({ title: '下载中...' });
				uni.downloadFile({
					url: proxyUrl + '&filename=' + encodeURIComponent(filename),
					success: (res) => {
						if (res.statusCode === 200) {
							this.saveImageWithRename(res.tempFilePath, filename);
						} else {
							uni.showToast({ title: '下载失败', icon: 'none' });
						}
					},
					fail: () => {
						uni.showToast({ title: '下载失败', icon: 'none' });
					},
					complete: () => {
						uni.hideLoading();
					},
				});
				// #endif
			},

			// 下载图片
			handleDownloadImage(index) {
				const pic = this.data.picInfo[index];
				if (!pic) {
					uni.showToast({ title: '图片不存在', icon: 'none' });
					return;
				}

				const url = pic.url || pic;
				const proxyUrl = this.getProxyUrl(url);
				const filename = '二支-' + (this.data.title || '图片').substring(0, 10) + '_' + (index + 1);

				// #ifdef H5
				const a = document.createElement('a');
				a.href = proxyUrl + '&filename=' + encodeURIComponent(filename);
				a.download = filename + '.jpg';
				a.click();
				// #endif

				// #ifdef MP-WEIXIN
				uni.showLoading({ title: '下载中...' });
				uni.downloadFile({
					url: proxyUrl + '&filename=' + encodeURIComponent(filename),
					success: (res) => {
						if (res.statusCode === 200) {
							this.saveImageWithRename(res.tempFilePath, filename);
						} else {
							uni.showToast({ title: '下载失败', icon: 'none' });
						}
					},
					fail: () => {
						uni.showToast({ title: '下载失败', icon: 'none' });
					},
					complete: () => {
						uni.hideLoading();
					},
				});
				// #endif
			},

			// 视频播放错误
			onVideoError(e) {
				console.error('[result] 视频播放错误:', JSON.stringify(e));
				if (this.data.platform === 'weixin') {
					// 视频号播放失败，清空预览URL显示提示
					this.previewUrl = '';
				}
				uni.showToast({ title: '视频播放失败', icon: 'none' });
			},

			// 视频开始播放
			onVideoPlay() {
				console.log('[result] 视频开始播放');
			},

			// 下载
			handleDownload(type) {
				const link = this.data.downloadLinks[type];
				if (!link || !link.url) {
					uni.showToast({ title: '下载链接不可用', icon: 'none' });
					return;
				}

				const proxyUrl = this.getProxyUrl(link.url);
				const filename = '二支-' + (this.data.title || 'video').substring(0, 10);

				// #ifdef H5
				const a = document.createElement('a');
				a.href = proxyUrl + '&filename=' + encodeURIComponent(filename);
				a.download = filename + '.mp4';
				a.click();
				// #endif

				// #ifdef MP-WEIXIN
				// 先检查文件大小，小程序 downloadFile 有大小限制（约50MB）
				uni.showLoading({ title: '检查文件...' });
				const sizeApiUrl = config.apiBase + '/api/video/size?url=' + encodeURIComponent(link.url);
				uni.request({
					url: sizeApiUrl,
					method: 'GET',
					success: (sizeRes) => {
						const data = sizeRes.data || {};
						const sizeMB = data.sizeMB || 0;
						console.log('[download] 文件大小:', sizeMB + 'MB');

						if (sizeMB > 45) {
							// 超过小程序限制，提示复制链接到浏览器下载
							uni.hideLoading();
							this.showCopyLinkDialog(proxyUrl, filename);
							return;
						}

						if (sizeMB === 0) {
							// 获取大小失败（接口返回异常），也提示复制链接
							uni.hideLoading();
							this.showCopyLinkDialog(proxyUrl, filename);
							return;
						}

						// 文件大小正常，执行下载
						this.doDownload(proxyUrl, filename);
					},
					fail: (err) => {
						// 获取大小接口请求失败（如404），提示复制链接
						console.warn('[download] 获取文件大小失败:', JSON.stringify(err));
						uni.hideLoading();
						this.showCopyLinkDialog(proxyUrl, filename);
					},
				});
				// #endif
			},

			// 提示复制链接到浏览器下载
			showCopyLinkDialog(proxyUrl, filename) {
				uni.showModal({
					title: '文件较大',
					content: '视频超出小程序下载限制，是否复制链接到浏览器下载？',
					confirmText: '复制链接',
					success: (modalRes) => {
						if (modalRes.confirm) {
							const fullUrl = proxyUrl + '&filename=' + encodeURIComponent(filename);
							uni.setClipboardData({
								data: fullUrl,
								success: () => {
									uni.showToast({ title: '链接已复制，请在浏览器中打开', icon: 'none', duration: 3000 });
								},
							});
						}
					},
				});
			},

		// 保存图片并重命名
		saveImageWithRename(tempFilePath, filename) {
			const fs = uni.getFileSystemManager();
			const destPath = wx.env.USER_DATA_PATH + '/' + filename + '.jpg';
			try {
				try { fs.unlinkSync(destPath); } catch (e) { /* 忽略 */ }
				fs.copyFileSync(tempFilePath, destPath);
				uni.saveImageToPhotosAlbum({
					filePath: destPath,
					success: () => {
						uni.showToast({ title: '已保存到相册', icon: 'success' });
					},
					fail: () => {
						uni.showToast({ title: '保存失败', icon: 'none' });
					},
				});
			} catch (e) {
				uni.saveImageToPhotosAlbum({
					filePath: tempFilePath,
					success: () => {
						uni.showToast({ title: '已保存到相册', icon: 'success' });
					},
					fail: () => {
						uni.showToast({ title: '保存失败', icon: 'none' });
					},
				});
			}
		},
			// 执行实际下载（小程序端）
			doDownload(proxyUrl, filename) {
				uni.showLoading({ title: '下载中...' });
				const downloadTask = uni.downloadFile({
					url: proxyUrl + '&filename=' + encodeURIComponent(filename),
					timeout: {
						downloadTaskTimeout: 600,
					},
					success: (res) => {
						if (res.statusCode === 200) {
							// 复制到 USER_DATA_PATH 并重命名
							const fs = uni.getFileSystemManager();
							const newName = filename + '.mp4';
							const destPath = wx.env.USER_DATA_PATH + '/' + newName;

							try {
								try { fs.unlinkSync(destPath); } catch (e) { /* 忽略 */ }
								fs.copyFileSync(res.tempFilePath, destPath);

								uni.saveVideoToPhotosAlbum({
									filePath: destPath,
									success: () => {
										uni.showToast({ title: '已保存到相册', icon: 'success' });
									},
									fail: (err) => {
										console.error('[download] 保存失败:', JSON.stringify(err));
										uni.showToast({ title: '保存失败', icon: 'none' });
									},
								});
							} catch (copyErr) {
								console.warn('[download] 复制失败，使用原始路径:', copyErr);
								uni.saveVideoToPhotosAlbum({
									filePath: res.tempFilePath,
									success: () => {
										uni.showToast({ title: '已保存到相册', icon: 'success' });
									},
									fail: (err) => {
										console.error('[download] 保存失败:', JSON.stringify(err));
										uni.showToast({ title: '保存失败', icon: 'none' });
									},
								});
							}
						} else {
							uni.showToast({ title: '下载失败(' + res.statusCode + ')', icon: 'none' });
						}
					},
					fail: (err) => {
						console.error('[download] 下载失败:', JSON.stringify(err));
						uni.showToast({ title: '下载失败', icon: 'none' });
					},
					complete: () => {
						uni.hideLoading();
					},
				});
				// 监听下载进度
				if (downloadTask && downloadTask.onProgressUpdate) {
					downloadTask.onProgressUpdate((res) => {
						if (res.totalBytesExpectedToWrite > 0) {
							const percent = Math.round(res.progress);
							console.log('[download] 下载进度:', percent + '%');
						}
					});
				}
			},
		},
	}
</script>

<style scoped>
	.container {
		min-height: 100vh;
		background: transparent;
		padding-bottom: 40rpx;
	}

	/* 封面 */
	.cover-section {
		width: 100%;
		height: 400rpx;
		overflow: hidden;
	}

	.cover {
		width: 100%;
		height: 100%;
	}

	/* 信息卡片 */
	.info-card {
		background: rgba(255, 255, 255, 0.9);
		margin: 20rpx 30rpx;
		border-radius: 20rpx;
		padding: 30rpx;
		box-shadow: 0 4rpx 20rpx rgba(76, 175, 80, 0.1);
		backdrop-filter: blur(10px);
	}

	.title {
		font-size: 34rpx;
		font-weight: bold;
		color: #1b5e20;
		line-height: 1.5;
		display: block;
	}

	.meta-row {
		margin-top: 16rpx;
	}

	.platform-tag {
		font-size: 24rpx;
		color: #2e7d32;
		background: #e8f5e9;
		padding: 6rpx 16rpx;
		border-radius: 8rpx;
	}

	.desc {
		font-size: 28rpx;
		color: #666;
		line-height: 1.6;
		margin-top: 20rpx;
		display: block;
	}

	/* 下载链接 */
	.download-section {
		background: rgba(255, 255, 255, 0.9);
		margin: 20rpx 30rpx;
		border-radius: 20rpx;
		padding: 30rpx;
		box-shadow: 0 4rpx 20rpx rgba(76, 175, 80, 0.1);
		backdrop-filter: blur(10px);
	}

	.section-title {
		font-size: 30rpx;
		font-weight: 600;
		color: #2e7d32;
		margin-bottom: 20rpx;
		display: block;
	}

	.link-item {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 24rpx 0;
		border-bottom: 1rpx solid #f5f5f5;
	}

	.link-item:last-child {
		border-bottom: none;
	}

	.link-info {
		flex: 1;
	}

	.link-type {
		font-size: 30rpx;
		color: #333;
		display: block;
	}

	.link-quality {
		font-size: 24rpx;
		color: #999;
		margin-top: 6rpx;
		display: block;
	}

	.btn-download {
		background: linear-gradient(135deg, #81c784 0%, #66bb6a 50%, #4caf50 100%);
		color: #fff;
		padding: 14rpx 36rpx;
		border-radius: 12rpx;
		font-size: 26rpx;
		box-shadow: 0 4rpx 12rpx rgba(76, 175, 80, 0.2);
	}

	.btn-actions {
		display: flex;
		gap: 16rpx;
	}

	.btn-copy {
		background: #e8f5e9;
		color: #2e7d32;
		padding: 14rpx 28rpx;
		border-radius: 12rpx;
		font-size: 24rpx;
	}

	/* 视频号提示 */
	.weixin-notice {
		background: #fff;
		margin: 20rpx 30rpx;
		border-radius: 20rpx;
		padding: 40rpx 30rpx;
		text-align: center;
		box-shadow: 0 4rpx 20rpx rgba(0, 0, 0, 0.05);
	}

	.notice-icon {
		font-size: 60rpx;
		display: block;
		margin-bottom: 16rpx;
	}

	.notice-title {
		font-size: 32rpx;
		font-weight: bold;
		color: #333;
		display: block;
		margin-bottom: 12rpx;
	}

	.notice-desc {
		font-size: 26rpx;
		color: #999;
		display: block;
		margin-bottom: 30rpx;
	}

	.btn-copy-link {
		background: linear-gradient(135deg, #07c160, #06ad56);
		color: #fff;
		padding: 20rpx 60rpx;
		border-radius: 16rpx;
		font-size: 28rpx;
		display: inline-block;
	}

	/* 视频预览 */
	.preview-section {
		background: rgba(255, 255, 255, 0.9);
		margin: 20rpx 30rpx;
		border-radius: 20rpx;
		padding: 30rpx;
		box-shadow: 0 4rpx 20rpx rgba(76, 175, 80, 0.1);
		backdrop-filter: blur(10px);
	}

	.video-player {
		width: 100%;
		border-radius: 12rpx;
	}

	.debug-url {
		font-size: 20rpx;
		color: #999;
		margin-top: 12rpx;
		word-break: break-all;
		display: block;
	}

	.copy-link-section {
		background: #fff;
		margin: 20rpx 30rpx;
		border-radius: 20rpx;
		padding: 30rpx;
		box-shadow: 0 4rpx 20rpx rgba(0, 0, 0, 0.05);
	}

	.btn-copy-video {
		background: linear-gradient(135deg, #5cc261 0%, #5dce63 50%, #0be612 100%);
		color: #fff;
		padding: 24rpx;
		border-radius: 16rpx;
		text-align: center;
		font-size: 30rpx;
		font-weight: 600;
	}
</style>
