// pages/profile/index.js
const { get } = require('../../utils/request')

Page({
  data: {
    user: null,
    avatarChar: '',
    services: [],
    settings: [
      { key: 'profile', name: '个人信息修改', icon: '👤', color: '#E8F0E4' },
      { key: 'notify', name: '通知设置', icon: '🔔', color: '#FCF0D9' },
      { key: 'about', name: '关于溪山农服', icon: 'ℹ️', color: '#F2EFE8' },
      { key: 'logout', name: '退出登录', icon: '↩️', color: '#FBE8E5', danger: true }
    ]
  },

  onLoad() {
    this.loadData()
  },

  onShow() {
    this.loadData()
  },

  /** 加载数据：从后端 API 获取用户信息 + 服务记录 */
  loadData() {
    const app = getApp()
    const newPlots = app.globalData.newPlots || []

    // 获取用户信息
    get('/user/profile')
      .then(res => {
        if (res.code === 0 && res.data) {
          this.setData({
            user: {
              ...res.data,
              stats: { area: 0, plots: newPlots.length, patrols: 0 }
            },
            avatarChar: res.data.name ? res.data.name.charAt(0) : '农'
          })
        }
      })
      .catch(() => {
        this.setData({
          user: { name: '未登录', stats: { area: 0, plots: 0, patrols: 0 } },
          avatarChar: '农'
        })
      })

    // 获取服务记录
    get('/user/service-records')
      .then(res => {
        if (res.code === 0 && res.data) {
          this.setData({ services: res.data })
        }
      })
      .catch(() => {})
  },

  /** 点击服务记录 */
  onServiceTap(e) {
    const name = e.currentTarget.dataset.name
    if (name === '识病记录') {
      wx.navigateTo({ url: '/pages/disease-history/index' })
    } else if (name === '巡田报告') {
      wx.showToast({ title: '巡田报告功能开发中', icon: 'none' })
    } else if (name === '飞防订单') {
      wx.showToast({ title: '飞防订单功能开发中', icon: 'none' })
    }
  },

  /** 点击设置项 */
  onSettingTap(e) {
    const key = e.currentTarget.dataset.key
    if (key === 'logout') {
      wx.showModal({
        title: '提示',
        content: '确定退出登录吗？',
        success: (res) => {
          if (res.confirm) {
            // 清理登录态
            wx.removeStorageSync('access_token')
            wx.removeStorageSync('refresh_token')
            // 清空全局数据
            const app = getApp()
            app.globalData.newPlots = []
            app.globalData.diseaseHistory = []
            app.globalData.lastDetectionResult = null
            // 回到登录页
            wx.reLaunch({ url: '/pages/login/index' })
          }
        }
      })
      return
    }
    wx.showToast({ title: '功能开发中', icon: 'none' })
  }
})
