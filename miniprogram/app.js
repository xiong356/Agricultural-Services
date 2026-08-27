App({
  globalData: {
    // 用户信息
    userInfo: null,
    // 接口基础地址（开发环境）
    baseUrl: 'http://localhost:8000/miniapp/v1',
    // token（从缓存读取）
    token: wx.getStorageSync('access_token') || '',
    // 当前选中的地块
    currentPlotId: null,
    // 临时新增地块（接口对接后替换为云数据库）
    newPlots: [],
    // 临时识别记录（接口对接后替换为云数据库）
    diseaseHistory: []
  },

  onLaunch() {
    // 检查小程序更新
    this.checkUpdate()
    // 获取系统信息（状态栏高度等）
    this.getSystemInfo()
    // 检查登录状态
    this.checkAuth()
  },

  /** 检查登录状态 — 无 token 或 token 非法则跳转登录页 */
  checkAuth() {
    const token = wx.getStorageSync('access_token')
    // JWT 格式校验: 合法 JWT 必须有 3 段 (header.payload.signature)
    const isValidJWT = token && token.split('.').length === 3
    if (!isValidJWT) {
      // 清除旧的无效 token（包括 mock_access_token_xxx）
      wx.removeStorageSync('access_token')
      wx.removeStorageSync('refresh_token')
      this.globalData.token = ''
      setTimeout(() => {
        wx.reLaunch({ url: '/pages/login/index' })
      }, 100)
    }
  },

  /** 检查小程序版本更新 */
  checkUpdate() {
    if (wx.canIUse('getUpdateManager')) {
      const updateManager = wx.getUpdateManager()
      updateManager.onCheckForUpdate((res) => {
        if (res.hasUpdate) {
          updateManager.onUpdateReady(() => {
            wx.showModal({
              title: '更新提示',
              content: '新版本已就绪，是否重启应用？',
              success: (res) => {
                if (res.confirm) updateManager.applyUpdate()
              }
            })
          })
        }
      })
    }
  },

  /** 获取系统信息，计算状态栏和导航栏高度 */
  getSystemInfo() {
    try {
      const systemInfo = wx.getSystemInfoSync()
      const menuButton = wx.getMenuButtonBoundingClientRect()
      this.globalData.statusBarHeight = systemInfo.statusBarHeight
      this.globalData.navBarHeight = menuButton.bottom + menuButton.top - systemInfo.statusBarHeight * 2
      this.globalData.screenWidth = systemInfo.screenWidth
      this.globalData.screenHeight = systemInfo.screenHeight
    } catch (e) {
      console.error('获取系统信息失败', e)
    }
  }
})
