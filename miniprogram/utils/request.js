/**
 * utils/request.js
 * 统一网络请求封装 —— 自动携带 token、401 自动刷新、统一错误处理
 */

const app = getApp()

/** 基础请求方法（Promise 化） */
function request(options) {
  return new Promise((resolve, reject) => {
    const token = wx.getStorageSync('access_token') || ''

    wx.request({
      url: `${app.globalData.baseUrl}${options.url}`,
      method: options.method || 'GET',
      data: options.data || {},
      timeout: options.timeout || 15000,
      header: {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : '',
        ...options.header
      },
      success(res) {
        // HTTP 状态码处理
        if (res.statusCode === 401) {
          // token 过期，尝试刷新
          return refreshTokenAndRetry(options).then(resolve).catch(reject)
        }
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
        } else {
          const errMsg = (res.data && res.data.message) || '请求失败'
          wx.showToast({ title: errMsg, icon: 'none' })
          reject({ code: res.statusCode, message: errMsg, detail: res.data })
        }
      },
      fail(err) {
        wx.showToast({ title: '网络异常，请检查网络', icon: 'none' })
        reject({ code: -1, message: '网络异常', detail: err })
      }
    })
  })
}

/** 401 自动刷新 token 并重试 */
function refreshTokenAndRetry(options) {
  return new Promise((resolve, reject) => {
    const refreshToken = wx.getStorageSync('refresh_token')
    if (!refreshToken) {
      // 无 refresh token，跳转登录
      redirectToLogin()
      return reject({ code: 401, message: '登录已过期' })
    }

    wx.request({
      url: `${app.globalData.baseUrl}/auth/refresh`,
      method: 'POST',
      data: { refresh_token: refreshToken },
      success(res) {
        if (res.statusCode === 200 && res.data.access_token) {
          wx.setStorageSync('access_token', res.data.access_token)
          wx.setStorageSync('refresh_token', res.data.refresh_token)
          app.globalData.token = res.data.access_token
          // 重试原请求
          request(options).then(resolve).catch(reject)
        } else {
          redirectToLogin()
          reject({ code: 401, message: '刷新失败，请重新登录' })
        }
      },
      fail() {
        redirectToLogin()
        reject({ code: -1, message: '网络异常' })
      }
    })
  })
}

/** 跳转登录页 */
function redirectToLogin() {
  wx.removeStorageSync('access_token')
  wx.removeStorageSync('refresh_token')
  wx.navigateTo({ url: '/pages/login/index' })
}

/** 微信登录（wx.login → 换取 token） */
function wxLogin() {
  return new Promise((resolve, reject) => {
    wx.login({
      success(loginRes) {
        if (!loginRes.code) {
          return reject({ message: '微信登录失败' })
        }
        request({
          url: '/auth/wechat-login',
          method: 'POST',
          data: { code: loginRes.code }
        }).then(data => {
          wx.setStorageSync('access_token', data.access_token)
          wx.setStorageSync('refresh_token', data.refresh_token)
          app.globalData.token = data.access_token
          app.globalData.userInfo = data.user
          resolve(data.user)
        }).catch(reject)
      },
      fail(err) {
        reject({ message: '微信登录失败', detail: err })
      }
    })
  })
}

// 对外暴露便捷方法
module.exports = {
  request,
  get: (url, data) => request({ url, method: 'GET', data }),
  post: (url, data) => request({ url, method: 'POST', data }),
  put: (url, data) => request({ url, method: 'PUT', data }),
  del: (url, data) => request({ url, method: 'DELETE', data }),
  wxLogin
}
