// pages/capture/index.js
const app = getApp()

Page({
  data: {
    statusBarHeight: 0,
    navBarHeight: 0,
    animatingOut: false,
    isLoading: false,
    loadingText: '正在上传照片...',
    tips: [
      { id: 1, text: '选择光线充足的环境，避免逆光拍摄' },
      { id: 2, text: '拍摄病斑明显的叶片，对焦清晰' },
      { id: 3, text: '可多次拍摄提高识别准确率' }
    ]
  },

  onLoad() {
    const { statusBarHeight, navBarHeight } = app.globalData
    this.setData({
      statusBarHeight: statusBarHeight || 20,
      navBarHeight: navBarHeight || 44
    })
  },

  /** 返回上一页（带滑出动画） */
  goBack() {
    if (this.data.isLoading) return
    this.setData({ animatingOut: true })
    setTimeout(() => {
      wx.navigateBack({ delta: 1 })
    }, 250)
  },

  /** 拍照识别 */
  takePhoto() {
    if (this.data.isLoading) return
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      sourceType: ['camera'],
      camera: 'back',
      success: (res) => {
        this.identifyDisease(res.tempFiles[0].tempFilePath)
      },
      fail: (err) => {
        console.log('拍照取消或失败', err)
      }
    })
  },

  /** 从相册选择 */
  chooseFromAlbum() {
    if (this.data.isLoading) return
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      sourceType: ['album'],
      success: (res) => {
        this.identifyDisease(res.tempFiles[0].tempFilePath)
      },
      fail: (err) => {
        console.log('相册选择取消或失败', err)
      }
    })
  },

  /**
   * 调用后端 AI 识别接口
   * 流程: 持久化图片 → 显示 loading → 上传图片 → 接收结果 → 跳转结果页
   */
  identifyDisease(tempFilePath) {
    // 0. 检查登录状态
    const token = wx.getStorageSync('access_token')
    if (!token || token.split('.').length !== 3) {
      wx.showToast({ title: '请先登录', icon: 'none' })
      setTimeout(() => {
        wx.navigateTo({ url: '/pages/login/index' })
      }, 500)
      return
    }

    // 1. 先把临时图片持久化到本地存储
    const fs = wx.getFileSystemManager()
    const savedPath = wx.env.USER_DATA_PATH + '/disease_' + Date.now() + '.jpg'
    fs.saveFile({
      tempFilePath: tempFilePath,
      filePath: savedPath,
      success: () => {
        this.uploadAndIdentify(savedPath, tempFilePath)
      },
      fail: () => {
        // 持久化失败，退而用临时路径
        this.uploadAndIdentify(tempFilePath, tempFilePath)
      }
    })
  },

  /** 上传图片到后端并识别 */
  uploadAndIdentify(persistentPath, uploadPath) {
    // 1. 显示 loading 动画
    this.setData({ isLoading: true, loadingText: '正在上传照片...' })

    // 2. 上传图片到后端
    const baseUrl = app.globalData.baseUrl
    wx.uploadFile({
      url: `${baseUrl}/disease/identify`,
      filePath: uploadPath,
      name: 'file',
      header: {
        'Authorization': `Bearer ${wx.getStorageSync('access_token')}`
      },

      // 3. 上传进度更新 loading 文案
      progressUpdate: (res) => {
        if (res.progress < 100) {
          this.setData({ loadingText: `正在上传照片... ${res.progress}%` })
        } else {
          this.setData({ loadingText: 'AI 正在分析图片...' })
        }
      },

      // 4. 上传成功 → 解析响应
      success: (res) => {
        try {
          const data = JSON.parse(res.data)
          if (data.code === 0 && data.data) {
            this.setData({ loadingText: '识别完成！' })

            // 保存识别结果到全局
            app.globalData.lastDetectionResult = data.data

            // 同时保存到历史记录（用持久化路径，不用后端返回的 /uploads/ 路径）
            const history = app.globalData.diseaseHistory || []
            history.unshift({
              id: data.data.detection_id,
              name: data.data.diseaseName,
              severity: data.data.severity,
              plotName: '拍照识别',
              date: new Date().toISOString().split('T')[0],
              thumbnail: persistentPath
            })
            app.globalData.diseaseHistory = history

            setTimeout(() => {
              this.setData({ isLoading: false })
              wx.navigateTo({
                url: `/pages/result/index?filePath=${encodeURIComponent(persistentPath)}&fromApi=1`
              })
            }, 500)
          } else {
            this.setData({ isLoading: false })
            wx.showModal({
              title: '识别失败',
              content: data.message || '服务端返回错误，请重试',
              showCancel: false
            })
          }
        } catch (e) {
          this.setData({ isLoading: false })
          wx.showModal({
            title: '解析失败',
            content: '服务端返回数据格式异常',
            showCancel: false
          })
        }
      },

      // 5. 上传失败
      fail: (err) => {
        this.setData({ isLoading: false })
        wx.showModal({
          title: '网络异常',
          content: '无法连接到服务器，请确认后端服务已启动\n(http://localhost:8000)',
          showCancel: false
        })
      }
    })
  }
})
