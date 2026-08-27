/**
 * services/plot.js
 * 地块管理相关 API
 */
const { get } = require('../utils/request')

/** 获取当前用户的地块列表 */
function getMyPlots() {
  return get('/plots/mine')
}

/** 获取地块详情 */
function getPlotDetail(plotId) {
  return get(`/plots/${plotId}`)
}

/** 获取地块巡田报告列表 */
function getPatrolReports(plotId) {
  return get(`/plots/${plotId}/reports`)
}

module.exports = { getMyPlots, getPlotDetail, getPatrolReports }
