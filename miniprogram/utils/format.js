/**
 * utils/format.js
 * 通用格式化工具
 */

/** 格式化日期：2026-07-15 → 7月15日 */
function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return `${d.getMonth() + 1}月${d.getDate()}日`
}

/** 格式化日期时间：2026-07-15T14:32:00 → 7月15日 14:32 */
function formatDateTime(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const h = String(d.getHours()).padStart(2, '0')
  const m = String(d.getMinutes()).padStart(2, '0')
  return `${d.getMonth() + 1}月${d.getDate()}日 ${h}:${m}`
}

/** 严重度 → 标签 class */
function severityToClass(severity) {
  const map = {
    critical: 'tag-severity-critical',
    high: 'tag-severity-critical',
    medium: 'tag-severity-medium',
    low: 'tag-severity-low'
  }
  return map[severity] || 'tag-severity-low'
}

/** 严重度 → 中文 */
function severityToText(severity) {
  const map = {
    critical: '严重',
    high: '严重',
    medium: '中等',
    low: '轻度'
  }
  return map[severity] || '未知'
}

module.exports = {
  formatDate,
  formatDateTime,
  severityToClass,
  severityToText
}
