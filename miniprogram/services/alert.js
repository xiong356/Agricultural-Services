/**
 * services/alert.js
 * 预警相关 API
 */
const { get } = require('../utils/request')

/** 获取预警列表 */
function getAlerts(params = {}) {
  return get('/alerts', params)
}

/** 获取预警详情 */
function getAlertDetail(alertId) {
  return get(`/alerts/${alertId}`)
}

/** 获取未处理预警数量 */
function getUnreadCount() {
  return get('/alerts/unread-count')
}

module.exports = { getAlerts, getAlertDetail, getUnreadCount }
