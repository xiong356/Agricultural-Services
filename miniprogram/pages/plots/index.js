// pages/plots/index.js
const { formatDate } = require('../../utils/format')

Page({
  data: {
    plotList: [],
    totalCount: 0
  },

  onLoad() {
    this.loadData()
  },

  onShow() {
    this.loadData()
  },

  /** 加载地块列表（仅显示用户添加的地块） */
  loadData() {
    const app = getApp()
    const newPlots = app.globalData.newPlots || []

    const plotList = newPlots.map(item => ({
      ...item,
      lastPatrolText: formatDate(item.lastPatrol)
    }))
    this.setData({
      plotList,
      totalCount: plotList.length
    })
  },

  /** 跳转地块详情 */
  goPlotDetail(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: `/pages/plot-detail/index?id=${id}` })
  },

  /** 添加新地块 */
  goAddPlot() {
    wx.navigateTo({ url: '/pages/plot-add/index' })
  }
})
