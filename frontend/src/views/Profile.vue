<template>
  <div class="container profile-page">
    <div class="profile-card card">
      <div class="profile-header">
        <div class="avatar-lg">{{ auth.user?.username?.charAt(0)?.toUpperCase() }}</div>
        <div>
          <h1>{{ auth.user?.username }}</h1>
          <p class="text-muted">{{ auth.user?.email }}</p>
        </div>
      </div>

      <div class="profile-section">
        <h2>个人信息</h2>

        <div v-if="successMsg" class="alert alert-success">{{ successMsg }}</div>
        <div v-if="errorMsg" class="alert alert-error">{{ errorMsg }}</div>

        <form @submit.prevent="handleUpdate">
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">用户名</label>
              <input class="form-input" :value="auth.user?.username" disabled />
            </div>
            <div class="form-group">
              <label class="form-label">邮箱</label>
              <input v-model="form.email" class="form-input" type="email" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">手机号</label>
              <input v-model="form.phone" class="form-input" type="tel" placeholder="请输入手机号" />
            </div>
            <div class="form-group">
              <label class="form-label">注册时间</label>
              <input class="form-input" :value="formatDate(auth.user?.create_time)" disabled />
            </div>
          </div>
          <button type="submit" class="btn btn-primary" :disabled="loading">
            {{ loading ? '保存中...' : '保存修改' }}
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watchEffect } from 'vue'
import { useAuthStore } from '../stores/auth'
import { userApi } from '../api'

const auth = useAuthStore()
const form = reactive({ email: '', phone: '' })
const loading = ref(false)
const successMsg = ref('')
const errorMsg = ref('')

watchEffect(() => {
  if (auth.user) {
    form.email = auth.user.email
    form.phone = auth.user.phone || ''
  }
})

function formatDate(d: string | undefined) {
  if (!d) return '-'
  return new Date(d).toLocaleDateString('zh-CN')
}

async function handleUpdate() {
  loading.value = true
  successMsg.value = ''
  errorMsg.value = ''
  try {
    const data: any = {}
    if (form.email) data.email = form.email
    if (form.phone) data.phone = form.phone
    await userApi.updateProfile(data)
    await auth.fetchProfile()
    successMsg.value = '信息更新成功'
  } catch (e: any) {
    errorMsg.value = e.response?.data?.detail || '更新失败'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.profile-page {
  max-width: 800px;
}

.profile-card {
  padding: 0;
  overflow: hidden;
}

.profile-header {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 32px;
  background: linear-gradient(135deg, var(--primary), #8b5cf6);
  color: #fff;
}

.avatar-lg {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.6rem;
  font-weight: 700;
}

.profile-header h1 {
  font-size: 1.4rem;
  margin-bottom: 4px;
}

.profile-header .text-muted {
  opacity: 0.85;
  font-size: 0.9rem;
}

.profile-section {
  padding: 32px;
}

.profile-section h2 {
  font-size: 1.2rem;
  margin-bottom: 20px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

@media (max-width: 640px) {
  .form-row {
    grid-template-columns: 1fr;
  }
}
</style>
