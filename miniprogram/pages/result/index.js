// pages/result/index.js
const app = getApp()
const { severityToText } = require('../../utils/format')

Page({
  data: {
    statusBarHeight: 0,
    navBarHeight: 0,
    animatingOut: false,
    filePath: '',
    result: null,
    severityText: '',
    confidencePercent: 0
  },

  onLoad(options) {
    const { statusBarHeight, navBarHeight } = app.globalData
    const filePath = options.filePath ? decodeURIComponent(options.filePath) : ''
    const fromHistory = options.fromHistory === '1'
    const fromApi = options.fromApi === '1'

    // 从 API 返回（拍照识病真实结果）
    if (fromApi && app.globalData.lastDetectionResult) {
      const apiResult = app.globalData.lastDetectionResult
      this.setData({
        statusBarHeight: statusBarHeight || 20,
        navBarHeight: navBarHeight || 44,
        filePath,
        fromHistory: false,
        result: apiResult,
        severityText: severityToText(apiResult.severity),
        confidencePercent: Math.round((apiResult.confidence || 0) * 100)
      })
      return
    }

    // 从历史记录进入
    if (fromHistory) {
      const historyResult = {
        diseaseName: decodeURIComponent(options.diseaseName || ''),
        severity: options.severity || 'low',
        confidence: 0.93,
        time: options.date || '',
        treatments: []
      }
      this.setData({
        statusBarHeight: statusBarHeight || 20,
        navBarHeight: navBarHeight || 44,
        filePath: decodeURIComponent(options.thumbnail || ''),
        fromHistory: true,
        historyId: decodeURIComponent(options.historyId || ''),
        result: historyResult,
        severityText: severityToText(historyResult.severity),
        confidencePercent: Math.round(historyResult.confidence * 100),
        historyDate: options.date || '',
        historyPlotName: decodeURIComponent(options.plotName || '')
      })
      return
    }

    // 从拍照进入
    if (!app.globalData.diseaseHistory) {
      app.globalData.diseaseHistory = []
    }
    this.setData({
      statusBarHeight: statusBarHeight || 20,
      navBarHeight: navBarHeight || 44,
      filePath,
      fromHistory: false
    })
  },

  /** 返回上一页（带滑出动画） */
  goBack() {
    this.setData({ animatingOut: true })
    setTimeout(() => {
      wx.navigateBack({ delta: 1 })
    }, 250)
  },

  /** 分享 */
  onShare() {
    wx.showToast({ title: '分享功能开发中', icon: 'none' })
  },

  /** 预约飞防 */
  bookSpray() {
    wx.showToast({ title: '飞防下单功能开发中', icon: 'none' })
  },

  /** 查看历史记录 */
  viewHistory() {
    wx.navigateTo({ url: '/pages/disease-history/index' })
  },

  /** 删除此记录 */
  onDeleteRecord() {
    wx.showModal({
      title: '确认删除',
      content: '确定删除此条识别记录吗？',
      confirmColor: '#B85042',
      success: (res) => {
        if (res.confirm) {
          const { del } = require('../../utils/request')
          const id = this.data.historyId
          del(`/disease/history/${id}`)
            .then(res => {
              if (res.code === 0) {
                wx.showToast({ title: '已删除', icon: 'success' })
                setTimeout(() => wx.navigateBack(), 500)
              } else {
                wx.showToast({ title: res.message || '删除失败', icon: 'none' })
              }
            })
            .catch(() => {
              wx.showToast({ title: '删除失败', icon: 'none' })
            })
        }
      }
    })
  }
})
