import { defineStore } from 'pinia'

/**
 * 最小化 auth store：目前仅维护一个轻量会话标记。
 * 后续可扩展真实登录/令牌逻辑。
 */
export const useAuthStore = defineStore('auth', {
  state: () => ({
    ready: false,
  }),
  actions: {
    init() {
      // 预留：读取本地 token / user 信息
      this.ready = true
    },
  },
})