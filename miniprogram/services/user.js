/**
 * services/user.js
 * 用户相关 API
 */
const { get, post } = require('../utils/request')

/** 获取用户信息 */
function getProfile() {
  return get('/user/profile')
}

/** 更新用户信息 */
function updateProfile(data) {
  return post('/user/profile/update', data)
}

/** 获取用户统计（种植面积/地块数/巡田次数） */
function getStats() {
  return get('/user/stats')
}

module.exports = { getProfile, updateProfile, getStats }
