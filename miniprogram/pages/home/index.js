// pages/home/index.js
Page({
  data: {
    userName: '',
    alert: null,
    report: null
  },

  onLoad() {
    this.loadData()
  },

  onShow() {
    this.loadData()
  },

  /** 加载数据 */
  loadData() {
    // 数据来自后端 API，当前无 mock
    this.setData({
      alert: null,
      report: null
    })
  },

  /** 跳转拍照识病 */
  goCapture() {
    wx.navigateTo({ url: '/pages/capture/index' })
  },

  /** 跳转地块列表 */
  goPlots() {
    wx.switchTab({ url: '/pages/plots/index' })
  },

  /** 跳转飞防下单（P1 功能，暂跳预警） */
  goSpray() {
    wx.showToast({ title: '飞防下单功能开发中', icon: 'none' })
  },

  /** 跳转巡田报告 */
  goReports() {
    wx.switchTab({ url: '/pages/profile/index' })
  },

  /** 查看预警详情 */
  viewAlert() {
    wx.switchTab({ url: '/pages/alerts/index' })
  }
})
