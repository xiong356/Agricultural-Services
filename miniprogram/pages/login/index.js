// pages/login/index.js
const app = getApp()
const { post } = require('../../utils/request')

Page({
  data: {
    phone: '',
    password: '',
    loading: false,
    showPassword: false
  },

  onLoad() {
    // 已登录则直接进入首页
    const token = wx.getStorageSync('access_token')
    const isValidJWT = token && token.split('.').length === 3
    if (isValidJWT) {
      wx.switchTab({ url: '/pages/home/index' })
    }
  },

  onPhoneInput(e) {
    this.setData({ phone: e.detail.value })
  },

  onPasswordInput(e) {
    this.setData({ password: e.detail.value })
  },

  /** 手机号 + 密码登录（主流程） */
  async onLogin() {
    const { phone, password } = this.data

    if (!phone) {
      wx.showToast({ title: '请输入手机号', icon: 'none' }); return
    }
    if (!password) {
      wx.showToast({ title: '请输入密码', icon: 'none' }); return
    }

    this.setData({ loading: true })

    try {
      const res = await post('/auth/login', { phone, password })
      if (res.code === 0 && res.data && res.data.access_token) {
        // 保存 token（必须是 JWT 格式 xxx.yyy.zzz）
        wx.setStorageSync('access_token', res.data.access_token)
        wx.setStorageSync('refresh_token', res.data.refresh_token)
        app.globalData.token = res.data.access_token
        app.globalData.userInfo = res.data.user

        wx.showToast({ title: '登录成功', icon: 'success' })

        setTimeout(() => {
          wx.switchTab({ url: '/pages/home/index' })
        }, 500)
      } else {
        wx.showToast({ title: res.message || '登录失败', icon: 'none' })
        this.setData({ loading: false })
      }
    } catch (err) {
      wx.showToast({ title: '网络异常', icon: 'none' })
      this.setData({ loading: false })
    }
  },

  /** 跳转注册 */
  goRegister() {
    wx.navigateTo({ url: '/pages/register/index' })
  },

  /** 填充测试账号（仅开发用） */
  fillTestAccount() {
    this.setData({ phone: '13800138000', password: '123456' })
  }
})
