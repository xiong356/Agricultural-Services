// pages/disease-history/index.js
const app = getApp()
const { get } = require('../../utils/request')
const { formatDate, severityToClass, severityToText } = require('../../utils/format')

Page({
  data: {
    list: [],
    animatingOut: false
  },

  onLoad() {
    this.loadData()
  },

  onShow() {
    this.loadData()
  },

  /** 从后端 API 加载识别历史 */
  loadData() {
    get('/disease/history')
      .then(res => {
        if (res.code === 0 && res.data && res.data.items) {
          const baseUrl = app.globalData.baseUrl.replace('/miniapp/v1', '')
          const list = res.data.items.map(item => {
            let thumbnail = item.thumbnail || ''
            if (thumbnail && thumbnail.startsWith('/')) {
              thumbnail = `${baseUrl}${thumbnail}`
            }
            return {
              ...item,
              thumbnail,
              dateText: formatDate(item.date),
              severityClass: severityToClass(item.severity),
              severityText: severityToText(item.severity)
            }
          })
          this.setData({ list })
        }
      })
      .catch(() => {
        wx.showToast({ title: '加载失败', icon: 'none' })
      })
  },

  /** 图片加载失败时回退为 emoji */
  onThumbError(e) {
    const index = e.currentTarget.dataset.index
    this.setData({ [`list[${index}].thumbnail`]: '' })
  },

  goBack() {
    this.setData({ animatingOut: true })
    setTimeout(() => wx.navigateBack({ delta: 1 }), 250)
  },

  goDetail(e) {
    const id = e.currentTarget.dataset.id
    const record = this.data.list.find(item => item.id === id)
    if (record) {
      const params = `diseaseName=${encodeURIComponent(record.name)}&severity=${record.severity}&plotName=${encodeURIComponent(record.plotName)}&date=${record.date}&fromHistory=1&thumbnail=${encodeURIComponent(record.thumbnail || '')}&historyId=${encodeURIComponent(record.id || '')}`
      wx.navigateTo({ url: `/pages/result/index?${params}` })
    }
  }
})
