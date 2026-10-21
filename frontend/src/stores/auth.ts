import { defineStore } from 'pinia'
import type { User, AuthStatus } from '@/types'
import http from '@/utils/http'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('auth_token') || '',
    user: ((): User | null => {
      try {
        const raw = localStorage.getItem('auth_user')
        return raw ? JSON.parse(raw) : null
      } catch {
        return null
      }
    })(),
    status: null as AuthStatus | null,
    ready: false,
  }),
  getters: {
    isLoggedIn: (state) => Boolean(state.token && state.user),
    isAdmin: (state) => state.user?.role === 'admin',
    displayName: (state) => state.user?.nickname || state.user?.username || '用户',
  },
  actions: {
    async init() {
      if (this.token && !this.user) {
        await this.fetchMe()
      }
      this.ready = true
    },
    setAuth(token: string, user: User) {
      this.token = token
      this.user = user
      localStorage.setItem('auth_token', token)
      localStorage.setItem('auth_user', JSON.stringify(user))
    },
    clearAuth() {
      this.token = ''
      this.user = null
      localStorage.removeItem('auth_token')
      localStorage.removeItem('auth_user')
    },
    async fetchStatus(): Promise<AuthStatus> {
      try {
        const res = (await http.get('/auth/status')) as unknown as AuthStatus
        this.status = res
        if (res.user) {
          this.user = res.user
          localStorage.setItem('auth_user', JSON.stringify(res.user))
        }
        return res
      } catch (e) {
        return {
          hasUsers: true,
          allowRegistration: true,
          loggedIn: false,
          user: null,
        }
      }
    },
    async login(params: { username: string; password: string }) {
      const res = (await http.post('/auth/login', params)) as unknown as {
        token: string
        user: User
        message?: string
      }
      this.setAuth(res.token, res.user)
      return res
    },
    async register(params: { username: string; password: string; nickname?: string }) {
      const res = (await http.post('/auth/register', params)) as unknown as {
        token: string
        user: User
        message?: string
      }
      this.setAuth(res.token, res.user)
      return res
    },
    async logout() {
      try {
        await http.post('/auth/logout')
      } catch {
        // ignore logout errors
      } finally {
        this.clearAuth()
      }
    },
    async fetchMe() {
      if (!this.token) return null
      try {
        const user = (await http.get('/auth/me')) as unknown as User
        this.user = user
        localStorage.setItem('auth_user', JSON.stringify(user))
        return user
      } catch {
        this.clearAuth()
        return null
      }
    },
    async changePassword(params: { oldPassword: string; newPassword: string }) {
      return await http.post('/auth/change-password', params)
    },
  },
})