// pages/plot-add/index.js
Page({
  data: {
    form: {
      name: '',
      village: '',
      crop: '',
      area: '',
      image: ''
    },
    animatingOut: false
  },

  /** 文本输入 */
  onFieldInput(e) {
    const { field } = e.currentTarget.dataset
    this.setData({
      [`form.${field}`]: e.detail.value
    })
  },

  /** 选择/上传地块航拍图片 */
  chooseImage() {
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      sourceType: ['album'],
      success: (res) => {
        const tempPath = res.tempFiles[0].tempFilePath
        // 持久化保存
        const fs = wx.getFileSystemManager()
        const savedPath = wx.env.USER_DATA_PATH + '/plot_' + Date.now() + '.jpg'
        fs.saveFile({
          tempFilePath: tempPath,
          filePath: savedPath,
          success: () => {
            this.setData({ 'form.image': savedPath })
          },
          fail: () => {
            this.setData({ 'form.image': tempPath })
          }
        })
      }
    })
  },

  /** 提交表单 */
  onSubmit() {
    const { name, area, village, crop } = this.data.form
    if (!name.trim()) {
      wx.showToast({ title: '请输入地块名称', icon: 'none' })
      return
    }
    if (!village.trim()) {
      wx.showToast({ title: '请输入所在村组', icon: 'none' })
      return
    }
    if (!crop.trim()) {
      wx.showToast({ title: '请输入作物类型', icon: 'none' })
      return
    }
    if (!area || parseFloat(area) <= 0) {
      wx.showToast({ title: '请输入有效面积', icon: 'none' })
      return
    }

    // 构建新地块数据并存入全局
    const app = getApp()
    if (!app.globalData.newPlots) {
      app.globalData.newPlots = []
    }
    const newPlot = {
      id: 'plot-new-' + Date.now(),
      name: name.trim(),
      crop: crop.trim(),
      area: parseFloat(area),
      lastPatrol: new Date().toISOString().split('T')[0],
      image: this.data.form.image || ''
    }
    app.globalData.newPlots.unshift(newPlot)

    this.setData({ animatingOut: true })
    wx.showToast({ title: '添加成功', icon: 'success' })
    setTimeout(() => {
      wx.navigateBack({ delta: 1 })
    }, 250)
  },

  /** 返回上一页（带滑出动画） */
  goBack() {
    this.setData({ animatingOut: true })
    setTimeout(() => {
      wx.navigateBack({ delta: 1 })
    }, 250)
  }
})
