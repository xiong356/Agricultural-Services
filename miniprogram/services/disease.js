/**
 * services/disease.js
 * 病虫害识别相关 API
 */
const { get, post, upload } = require('../utils/request')

/** 拍照识病 —— 上传图片并识别 */
function identifyDisease(filePath) {
  return upload('/disease/identify', filePath, { type: 'ground' })
}

/** 获取识别历史记录 */
function getHistory(params = {}) {
  return get('/disease/history', params)
}

/** 获取识别结果详情 */
function getResult(detectionId) {
  return get(`/disease/result/${detectionId}`)
}

/** 获取常见病虫害知识列表 */
function getPestLibrary() {
  return get('/disease/pest-library')
}

module.exports = { identifyDisease, getHistory, getResult, getPestLibrary }
