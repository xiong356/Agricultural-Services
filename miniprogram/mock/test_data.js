/**
 * mock/test_data.js
 * 模拟后端动态数据 —— 后端 API 就绪后删除此文件
 * 数据应来自：wx.cloud.callFunction() 或 wx.request() → 后端返回
 */
module.exports = {
  userInfo: null,
  homeAlert: null,
  homeReport: null,
  diseaseHistory: [],
  alertList: [],
  detectionResult: {
    diseaseName: '',
    severity: '',
    confidence: 0,
    time: '',
    treatments: [
      { label: '药剂推荐', value: '' },
      { label: '防治窗口', value: '' },
      { label: '飞防参数', value: '' }
    ]
  },
  serviceRecords: [
    { name: '识病记录', count: '0条', icon: '🔬', color: '#E8F0E4' },
    { name: '巡田报告', count: '0次', icon: '📋', color: '#FCF0D9' },
    { name: '飞防订单', count: '0单', icon: '🛩️', color: '#FBE8E5' }
  ]
}
