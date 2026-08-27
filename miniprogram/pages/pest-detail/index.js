// pages/pest-detail/index.js
const { get } = require('../../utils/request')
const { severityToText } = require('../../utils/format')

Page({
  data: {
    pest: {},
    severityText: '',
    animatingOut: false
  },

  onLoad(options) {
    const { id } = options
    if (!id) {
      wx.showToast({ title: '未找到病虫害信息', icon: 'none' })
      setTimeout(() => wx.navigateBack(), 1000)
      return
    }

    // 从后端 API 获取病虫害详情
    get(`/disease/pest-library/${id}`)
      .then(res => {
        if (res.code === 0 && res.data) {
          this.setData({
            pest: res.data,
            severityText: severityToText(res.data.severity || 'low')
          })
        } else {
          wx.showToast({ title: '未找到病虫害信息', icon: 'none' })
          setTimeout(() => wx.navigateBack(), 1000)
        }
      })
      .catch(() => {
        wx.showToast({ title: '加载失败，请稍后重试', icon: 'none' })
        setTimeout(() => wx.navigateBack(), 1000)
      })
  },

  /** 返回上一页（带滑出动画） */
  goBack() {
    this.setData({ animatingOut: true })
    setTimeout(() => {
      wx.navigateBack({ delta: 1 })
    }, 250)
  }
})
