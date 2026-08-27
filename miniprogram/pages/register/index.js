// pages/register/index.js
const app = getApp()
const { post } = require('../../utils/request')

Page({
  data: {
    name: '',
    phone: '',
    password: '',
    confirmPassword: '',
    village: '',
    loading: false
  },

  onInput(e) {
    const field = e.currentTarget.dataset.field
    this.setData({ [field]: e.detail.value })
  },

  /** 注册 */
  async onRegister() {
    const { name, phone, password, confirmPassword, village } = this.data

    if (!name) {
      wx.showToast({ title: '请输入姓名', icon: 'none' }); return
    }
    if (!phone || phone.length !== 11) {
      wx.showToast({ title: '请输入正确的手机号', icon: 'none' }); return
    }
    if (!password || password.length < 6) {
      wx.showToast({ title: '密码至少 6 位', icon: 'none' }); return
    }
    if (password !== confirmPassword) {
      wx.showToast({ title: '两次密码不一致', icon: 'none' }); return
    }

    this.setData({ loading: true })

    try {
      const res = await post('/auth/register', {
        phone, password, name, village
      })
      if (res.code === 0 && res.data) {
        // 注册成功 → 自动登录
        wx.setStorageSync('access_token', res.data.access_token)
        wx.setStorageSync('refresh_token', res.data.refresh_token)
        app.globalData.token = res.data.access_token
        app.globalData.userInfo = res.data.user

        wx.showToast({ title: '注册成功', icon: 'success' })

        setTimeout(() => {
          wx.switchTab({ url: '/pages/home/index' })
        }, 500)
      } else {
        wx.showToast({ title: res.message || '注册失败', icon: 'none' })
      }
    } catch (err) {
      wx.showToast({ title: '网络异常', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  }
})
