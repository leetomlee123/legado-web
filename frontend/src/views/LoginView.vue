<template>
  <div class="login-wrapper">
    <div class="login-bg-decor" aria-hidden="true">
      <div class="glow-orb orb-1"></div>
      <div class="glow-orb orb-2"></div>
    </div>

    <div class="login-container">
      <!-- 品牌头部 -->
      <div class="brand-header">
        <div class="brand-logo" aria-hidden="true">
          <svg width="44" height="44" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="3" y="3" width="10" height="22" rx="2" fill="#c8983a" opacity="0.95"/>
            <rect x="15" y="5" width="10" height="20" rx="2" fill="#fdf5e0" opacity="0.85"/>
            <rect x="5" y="8" width="6" height="1.5" rx="0.75" fill="#1c1208" opacity="0.4"/>
            <rect x="5" y="11" width="6" height="1.5" rx="0.75" fill="#1c1208" opacity="0.3"/>
            <rect x="5" y="14" width="4" height="1.5" rx="0.75" fill="#1c1208" opacity="0.2"/>
          </svg>
        </div>
        <h1 class="brand-title">阅&thinsp;读</h1>
        <p class="brand-subtitle">Legado Web · 专注纯粹沉浸的小说阅读器</p>
      </div>

      <!-- 系统初始化提示（无任何用户时） -->
      <div v-if="!loadingStatus && isFirstTimeInit" class="first-time-tip">
        <div class="tip-icon">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
          </svg>
        </div>
        <div class="tip-text">
          <strong>初始化系统</strong>：系统尚未创建账号，首个注册的用户将自动获得<strong>超级管理员 (Admin)</strong> 权限。
        </div>
      </div>

      <!-- 登录/注册 卡片主体 -->
      <div class="auth-card">
        <!-- 选项卡切换 -->
        <div v-if="!isFirstTimeInit" class="tab-header">
          <button
            class="tab-btn"
            :class="{ active: currentTab === 'login' }"
            @click="currentTab = 'login'"
          >
            账号登录
          </button>
          <button
            class="tab-btn"
            :class="{ active: currentTab === 'register' }"
            @click="currentTab = 'register'"
          >
            新用户注册
            <span v-if="!allowRegistration" class="tab-tag">已关闭</span>
          </button>
        </div>

        <div v-else class="tab-header first-init-header">
          <div class="first-init-title">注册管理员账号</div>
        </div>

        <!-- 登录表单 -->
        <div v-if="currentTab === 'login' && !isFirstTimeInit" class="form-body">
          <el-form :model="loginForm" label-position="top" @submit.prevent="handleLogin">
            <el-form-item label="用户名">
              <el-input
                v-model="loginForm.username"
                placeholder="请输入用户名"
                size="large"
                clearable
                :prefix-icon="UserIcon"
                @keyup.enter="handleLogin"
              />
            </el-form-item>

            <el-form-item label="登录密码">
              <el-input
                v-model="loginForm.password"
                type="password"
                placeholder="请输入登录密码"
                size="large"
                show-password
                :prefix-icon="LockIcon"
                @keyup.enter="handleLogin"
              />
            </el-form-item>

            <div class="form-submit-row">
              <button
                type="button"
                class="submit-btn"
                :disabled="submitting || !loginForm.username || !loginForm.password"
                @click="handleLogin"
              >
                <span v-if="submitting" class="btn-spinner"></span>
                <span>{{ submitting ? '正在登录...' : '立即登录' }}</span>
              </button>
            </div>
          </el-form>
        </div>

        <!-- 注册表单 -->
        <div v-else class="form-body">
          <div v-if="!isFirstTimeInit && !allowRegistration" class="reg-closed-notice">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/>
            </svg>
            <span>系统管理员已暂停新用户开放注册，如需账号请联系管理员。</span>
          </div>

          <el-form
            v-else
            :model="registerForm"
            label-position="top"
            @submit.prevent="handleRegister"
          >
            <el-form-item label="用户名">
              <el-input
                v-model="registerForm.username"
                placeholder="2~30 位字符（支持中英文、数字）"
                size="large"
                clearable
                :prefix-icon="UserIcon"
              />
            </el-form-item>

            <el-form-item label="个性昵称 (可选)">
              <el-input
                v-model="registerForm.nickname"
                placeholder="书架上展示的称呼"
                size="large"
                clearable
                :prefix-icon="EditPenIcon"
              />
            </el-form-item>

            <el-form-item label="密码">
              <el-input
                v-model="registerForm.password"
                type="password"
                placeholder="不少于 6 位密码"
                size="large"
                show-password
                :prefix-icon="LockIcon"
              />
            </el-form-item>

            <el-form-item label="确认密码">
              <el-input
                v-model="registerForm.confirmPassword"
                type="password"
                placeholder="请再次输入密码"
                size="large"
                show-password
                :prefix-icon="LockIcon"
                @keyup.enter="handleRegister"
              />
            </el-form-item>

            <div class="form-submit-row">
              <button
                type="button"
                class="submit-btn"
                :disabled="submitting || !registerForm.username || !registerForm.password"
                @click="handleRegister"
              >
                <span v-if="submitting" class="btn-spinner"></span>
                <span>{{ submitting ? '正在注册...' : (isFirstTimeInit ? '创建管理员账号' : '立即注册并进入') }}</span>
              </button>
            </div>
          </el-form>
        </div>
      </div>

      <!-- 底部版权信息 -->
      <footer class="login-footer">
        <p>Legado Web · 阅读 3.0 Web 移植版</p>
      </footer>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User as UserIcon, Lock as LockIcon, EditPen as EditPenIcon } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const currentTab = ref<'login' | 'register'>('login')
const loadingStatus = ref(true)
const submitting = ref(false)

const isFirstTimeInit = computed(() => {
  return authStore.status !== null && !authStore.status.hasUsers
})

const allowRegistration = computed(() => {
  if (authStore.status === null) return true
  return authStore.status.allowRegistration
})

const loginForm = reactive({
  username: '',
  password: '',
})

const registerForm = reactive({
  username: '',
  nickname: '',
  password: '',
  confirmPassword: '',
})

async function checkInitStatus() {
  loadingStatus.value = true
  try {
    const status = await authStore.fetchStatus()
    if (!status.hasUsers) {
      currentTab.value = 'register'
    } else if (authStore.isLoggedIn) {
      const redirect = (route.query.redirect as string) || '/'
      router.replace(redirect)
    }
  } finally {
    loadingStatus.value = false
  }
}

async function handleLogin() {
  const username = loginForm.username.trim()
  const password = loginForm.password.trim()
  if (!username || !password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }

  submitting.value = true
  try {
    await authStore.login({ username, password })
    ElMessage.success(`欢迎回来，${authStore.displayName}！`)
    const redirect = (route.query.redirect as string) || '/'
    router.replace(redirect)
  } catch (e: any) {
    ElMessage.error(e.message || '登录失败，请检查账号或密码')
  } finally {
    submitting.value = false
  }
}

async function handleRegister() {
  const username = registerForm.username.trim()
  const password = registerForm.password.trim()
  const confirmPassword = registerForm.confirmPassword.trim()
  const nickname = registerForm.nickname.trim()

  if (!username) {
    ElMessage.warning('请输入用户名')
    return
  }
  if (password.length < 6) {
    ElMessage.warning('密码长度不能少于 6 位')
    return
  }
  if (password !== confirmPassword) {
    ElMessage.warning('两次输入的密码不一致')
    return
  }

  submitting.value = true
  try {
    await authStore.register({
      username,
      password,
      nickname: nickname || undefined,
    })
    ElMessage.success(isFirstTimeInit.value ? '超级管理员创建成功！' : '注册成功！')
    const redirect = (route.query.redirect as string) || '/'
    router.replace(redirect)
  } catch (e: any) {
    ElMessage.error(e.message || '注册失败')
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  checkInitStatus()
})
</script>

<style scoped>
.login-wrapper {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #17120e;
  background-image:
    radial-gradient(ellipse at 50% 20%, rgba(200, 152, 58, 0.12) 0%, transparent 60%),
    radial-gradient(ellipse at 80% 80%, rgba(180, 130, 40, 0.08) 0%, transparent 50%),
    radial-gradient(circle at 15% 70%, rgba(30, 20, 10, 0.9) 0%, transparent 50%);
  overflow: hidden;
  padding: 24px;
}

.login-bg-decor {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
}

.glow-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.25;
}

.orb-1 {
  width: 380px;
  height: 380px;
  background: #c8983a;
  top: -100px;
  right: -50px;
}

.orb-2 {
  width: 420px;
  height: 420px;
  background: #7a501e;
  bottom: -150px;
  left: -100px;
}

.login-container {
  position: relative;
  z-index: 2;
  width: 100%;
  max-width: 440px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.brand-header {
  text-align: center;
}

.brand-logo {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
  filter: drop-shadow(0 6px 16px rgba(200, 152, 58, 0.3));
}

.brand-title {
  font-size: 28px;
  font-weight: 700;
  color: #f5eedb;
  letter-spacing: 4px;
  margin: 0 0 6px;
  font-family: 'Songti SC', 'Source Han Serif SC', serif;
}

.brand-subtitle {
  font-size: 13px;
  color: rgba(245, 238, 219, 0.6);
  margin: 0;
  letter-spacing: 0.5px;
}

.first-time-tip {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  background: rgba(200, 152, 58, 0.15);
  border: 1px solid rgba(200, 152, 58, 0.35);
  border-radius: 10px;
  padding: 12px 16px;
  color: #f7dfa5;
  font-size: 13px;
  line-height: 1.5;
}

.tip-icon {
  flex-shrink: 0;
  margin-top: 2px;
  color: #c8983a;
}

.tip-text strong {
  color: #fff;
}

.auth-card {
  background: #231b14;
  border: 1px solid rgba(200, 152, 58, 0.22);
  border-radius: 16px;
  box-shadow:
    0 16px 36px rgba(0, 0, 0, 0.45),
    0 0 0 1px rgba(255, 255, 255, 0.04);
  padding: 28px;
  backdrop-filter: blur(12px);
}

.tab-header {
  display: flex;
  background: rgba(0, 0, 0, 0.25);
  border-radius: 10px;
  padding: 4px;
  margin-bottom: 24px;
}

.tab-btn {
  flex: 1;
  border: none;
  background: transparent;
  color: rgba(245, 238, 219, 0.6);
  font-size: 14px;
  font-weight: 500;
  padding: 8px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.tab-btn.active {
  background: rgba(200, 152, 58, 0.2);
  color: #f5eedb;
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.tab-tag {
  font-size: 10px;
  background: rgba(255, 77, 79, 0.2);
  color: #ff7875;
  padding: 2px 6px;
  border-radius: 4px;
}

.first-init-header {
  background: transparent;
  padding: 0;
  margin-bottom: 20px;
  text-align: center;
}

.first-init-title {
  font-size: 16px;
  font-weight: 600;
  color: #e0be75;
}

:deep(.el-form-item__label) {
  color: rgba(245, 238, 219, 0.8) !important;
  font-size: 13px !important;
  font-weight: 500 !important;
  margin-bottom: 6px !important;
}

:deep(.el-input__wrapper) {
  background-color: rgba(18, 13, 9, 0.7) !important;
  box-shadow: 0 0 0 1px rgba(200, 152, 58, 0.2) inset !important;
  border-radius: 8px !important;
  transition: all 0.2s ease;
}

:deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1.5px #c8983a inset !important;
  background-color: rgba(18, 13, 9, 0.9) !important;
}

:deep(.el-input__inner) {
  color: #f5eedb !important;
}

:deep(.el-input__inner::placeholder) {
  color: rgba(245, 238, 219, 0.35) !important;
}

:deep(.el-input__prefix) {
  color: rgba(200, 152, 58, 0.7);
}

.form-submit-row {
  margin-top: 26px;
}

.submit-btn {
  width: 100%;
  height: 44px;
  border-radius: 8px;
  border: none;
  background: linear-gradient(135deg, #d4a34b 0%, #b88226 100%);
  color: #17120e;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  box-shadow: 0 4px 14px rgba(184, 130, 38, 0.35);
}

.submit-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #e0b057 0%, #c58f33 100%);
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(184, 130, 38, 0.45);
}

.submit-btn:active:not(:disabled) {
  transform: translateY(0);
}

.submit-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  box-shadow: none;
}

.btn-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(23, 18, 14, 0.2);
  border-top-color: #17120e;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.reg-closed-notice {
  display: flex;
  align-items: center;
  gap: 10px;
  background: rgba(255, 77, 79, 0.1);
  border: 1px solid rgba(255, 77, 79, 0.3);
  border-radius: 8px;
  padding: 16px;
  color: #ff9c9e;
  font-size: 13px;
  line-height: 1.5;
}

.login-footer {
  text-align: center;
  font-size: 12px;
  color: rgba(245, 238, 219, 0.35);
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
