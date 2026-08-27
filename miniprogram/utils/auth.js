/**
 * utils/auth.js
 * 登录态管理
 */
const { wxLogin } = require('./request')

/** 检查是否已登录 */
function isLoggedIn() {
  return !!wx.getStorageSync('access_token')
}

/** 获取用户信息（带缓存） */
function getUserInfo() {
  return wx.getStorageSync('user_info')
}

/** 确保已登录，未登录则自动静默登录 */
async function ensureLogin() {
  if (isLoggedIn()) return getUserInfo()
  try {
    return await wxLogin()
  } catch (e) {
    console.error('静默登录失败', e)
    return null
  }
}

/** 退出登录 */
function logout() {
  wx.removeStorageSync('access_token')
  wx.removeStorageSync('refresh_token')
  wx.removeStorageSync('user_info')
  const app = getApp()
  app.globalData.token = ''
  app.globalData.userInfo = null
  wx.reLaunch({ url: '/pages/home/index' })
}

module.exports = { isLoggedIn, getUserInfo, ensureLogin, logout }
