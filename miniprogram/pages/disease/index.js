// pages/disease/index.js
const { get } = require('../../utils/request')
const { formatDate, severityToClass, severityToText } = require('../../utils/format')

Page({
  data: {
    historyList: [],
    pestList: []
  },

  onLoad() {
    this.loadData()
  },

  onShow() {
    this.loadData()
  },

  /** 加载数据：从后端 API 获取识别历史 + 病虫害知识库 */
  loadData() {
    // 从后端 API 获取识别历史（持久化在数据库，重启不丢）
    get('/disease/history')
      .then(res => {
        if (res.code === 0 && res.data && res.data.items) {
          const historyList = res.data.items.slice(0, 2).map(item => ({
            ...item,
            dateText: formatDate(item.date),
            severityClass: severityToClass(item.severity),
            severityText: severityToText(item.severity)
          }))
          this.setData({ historyList })
        }
      })
      .catch(() => {})

    // 从后端 API 获取病虫害知识库
    get('/disease/pest-library')
      .then(res => {
        if (res.code === 0 && res.data) {
          this.setData({ pestList: res.data.slice(0, 3) })
        }
      })
      .catch(() => {})
  },

  /** 跳转拍照识病 */
  goCapture() {
    wx.navigateTo({ url: '/pages/capture/index' })
  },

  /** 查看全部历史 */
  viewAll() {
    wx.navigateTo({ url: '/pages/disease-history/index' })
  },

  /** 跳转病虫害详情 */
  goPestDetail(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: `/pages/pest-detail/index?id=${id}` })
  }
})
