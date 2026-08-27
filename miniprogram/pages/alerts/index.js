// pages/alerts/index.js

Page({
  data: {
    hasAlerts: false,
    activeFilter: 'all',
    filters: [
      { key: 'all', label: '全部' },
      { key: 'disease', label: '病害' },
      { key: 'pest', label: '虫害' }
    ],
    alertList: [],
    filteredList: []
  },

  onLoad() {
    this.loadData()
  },

  onShow() {
    this.loadData()
  },

  /** 加载数据 */
  loadData() {
    // 数据来自后端 API，当前无预警
    this.setData({
      alertList: [],
      hasAlerts: false,
      filteredList: []
    })
  },

  /** 切换筛选 tab */
  onFilter(e) {
    const key = e.currentTarget.dataset.key
    const filteredList = key === 'all'
      ? this.data.alertList
      : this.data.alertList.filter(item => item.type === key)
    this.setData({
      activeFilter: key,
      filteredList
    })
  }
})
