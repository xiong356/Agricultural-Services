// pages/plot-detail/index.js
const app = getApp()

Page({
  data: {
    statusBarHeight: 0,
    navBarHeight: 0,
    plot: null,
    animatingOut: false
  },

  onLoad(options) {
    const { statusBarHeight, navBarHeight } = app.globalData
    const id = options.id

    // 从用户添加的地块中查找
    const newPlots = app.globalData.newPlots || []
    const plot = newPlots.find(p => p.id === id)

    if (!plot) {
      wx.showToast({ title: '未找到地块信息', icon: 'none' })
      setTimeout(() => wx.navigateBack(), 1000)
      return
    }

    this.setData({
      statusBarHeight: statusBarHeight || 20,
      navBarHeight: navBarHeight || 44,
      plot
    })
  },

  /** 返回上一页（带滑出动画） */
  goBack() {
    this.setData({ animatingOut: true })
    setTimeout(() => {
      wx.navigateBack({ delta: 1 })
    }, 250)
  },

  /** 巡田报告 */
  viewPatrolReport() {
    wx.showToast({ title: '巡田报告功能开发中', icon: 'none' })
  },

  /** 飞防下单 */
  orderSpray() {
    wx.showToast({ title: '飞防下单功能开发中', icon: 'none' })
  },

  /** 删除地块 */
  onDeletePlot() {
    wx.showModal({
      title: '确认删除',
      content: `确定删除地块「${this.data.plot.name}」吗？删除后不可恢复。`,
      confirmColor: '#B85042',
      success: (res) => {
        if (res.confirm) {
          const app = getApp()
          const id = this.data.plot.id
          const plots = app.globalData.newPlots || []
          const target = plots.find(p => p.id === id)
          // 删除关联的本地图片
          if (target && target.image) {
            try { wx.getFileSystemManager().unlinkSync(target.image) } catch (e) { }
          }
          app.globalData.newPlots = plots.filter(p => p.id !== id)
          wx.showToast({ title: '已删除', icon: 'success' })
          setTimeout(() => wx.navigateBack(), 500)
        }
      }
    })
  }
})
