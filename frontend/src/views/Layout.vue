<template>
  <div class="layout">
    <!-- 顶部导航栏 -->
    <header class="navbar">
      <div class="navbar-inner container">
        <router-link to="/" class="brand">
          <span class="brand-icon">⚡</span>
          <span class="brand-text">DisSecKill</span>
        </router-link>

        <nav class="nav-links">
          <router-link to="/" class="nav-link" exact-active-class="active">首页</router-link>
          <router-link to="/goods" class="nav-link" active-class="active">商品</router-link>
          <router-link to="/seckill" class="nav-link" active-class="active">秒杀</router-link>
          <router-link to="/cart" class="nav-link" active-class="active">🛒 购物车</router-link>
          <router-link v-if="auth.isLoggedIn" to="/orders" class="nav-link" active-class="active">我的订单</router-link>
        </nav>

        <div class="nav-right">
          <template v-if="auth.isLoggedIn">
            <router-link to="/profile" class="user-badge">
              <span class="avatar">{{ auth.user?.username?.charAt(0)?.toUpperCase() }}</span>
              <span class="username">{{ auth.user?.username }}</span>
            </router-link>
            <button class="btn-text" @click="handleLogout">退出</button>
          </template>
          <template v-else>
            <router-link to="/login" class="btn btn-outline btn-sm">登录</router-link>
            <router-link to="/register" class="btn btn-primary btn-sm">注册</router-link>
          </template>
        </div>
      </div>
    </header>

    <!-- 主内容区 -->
    <main class="main-content">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <!-- 页脚 -->
    <footer class="footer">
      <div class="container">
        <p>DisSecKill · 分布式秒杀系统 · Built with Vue 3 + FastAPI</p>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { useAuthStore } from '../stores/auth'
import { useRouter } from 'vue-router'

const auth = useAuthStore()
const router = useRouter()

function handleLogout() {
  auth.logout()
  router.push('/')
}
</script>

<style scoped>
.layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

/* ===== 导航栏 ===== */
.navbar {
  background: var(--bg-card);
  border-bottom: 1px solid var(--border-light);
  position: sticky;
  top: 0;
  z-index: 100;
  backdrop-filter: blur(12px);
  background: rgba(255, 255, 255, 0.88);
}

.navbar-inner {
  display: flex;
  align-items: center;
  height: 64px;
  gap: 32px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  font-size: 1.2rem;
  color: var(--text-primary);
}

.brand-icon {
  font-size: 1.4rem;
}

.brand-text {
  background: linear-gradient(135deg, var(--primary), #8b5cf6);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.nav-links {
  display: flex;
  gap: 4px;
  flex: 1;
}

.nav-link {
  padding: 8px 16px;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  font-weight: 500;
  font-size: 0.95rem;
  transition: all var(--transition);
}

.nav-link:hover {
  color: var(--text-primary);
  background: var(--bg-input);
}

.nav-link.active {
  color: var(--primary);
  background: var(--primary-bg);
}

.nav-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.btn-sm {
  padding: 6px 16px;
  font-size: 0.875rem;
}

.user-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-primary);
}

.avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--primary), #8b5cf6);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 0.85rem;
}

.username {
  font-weight: 500;
  font-size: 0.9rem;
}

.btn-text {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 0.875rem;
  padding: 4px 8px;
  transition: color var(--transition);
}

.btn-text:hover {
  color: var(--danger);
}

/* ===== 主内容 ===== */
.main-content {
  flex: 1;
  padding: 32px 0;
}

/* ===== 页脚 ===== */
.footer {
  padding: 24px 0;
  text-align: center;
  color: var(--text-muted);
  font-size: 0.85rem;
  border-top: 1px solid var(--border-light);
}

/* ===== 响应式 ===== */
@media (max-width: 768px) {
  .navbar-inner {
    gap: 16px;
  }
  .nav-links {
    display: none;
  }
  .username {
    display: none;
  }
}
</style>
