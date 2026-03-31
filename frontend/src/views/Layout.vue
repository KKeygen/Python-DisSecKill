<template>
  <div class="layout">
    <!-- 顶部导航栏 -->
    <header class="navbar">
      <div class="navbar-inner container">
        <router-link to="/" class="brand">
          <span class="brand-icon">⚡</span>
          <span class="brand-text">DIS<span class="accent">SEC</span>KILL</span>
        </router-link>

        <nav class="nav-links">
          <router-link to="/" class="nav-link" exact-active-class="active">
            <span class="nav-icon">🏠</span>
            <span>首页</span>
          </router-link>
          <router-link to="/goods" class="nav-link" active-class="active">
            <span class="nav-icon">📦</span>
            <span>商品</span>
          </router-link>
          <router-link to="/seckill" class="nav-link seckill-link" active-class="active">
            <span class="nav-icon pulse">⚡</span>
            <span>秒杀</span>
            <span class="live-badge">LIVE</span>
          </router-link>
          <router-link to="/cart" class="nav-link" active-class="active">
            <span class="nav-icon">🛒</span>
            <span>购物车</span>
          </router-link>
          <router-link v-if="auth.isLoggedIn" to="/orders" class="nav-link" active-class="active">
            <span class="nav-icon">📋</span>
            <span>订单</span>
          </router-link>
        </nav>

        <div class="nav-right">
          <template v-if="auth.isLoggedIn">
            <router-link to="/profile" class="user-badge">
              <span class="avatar">{{ auth.user?.username?.charAt(0)?.toUpperCase() }}</span>
              <span class="username">{{ auth.user?.username }}</span>
            </router-link>
            <button class="btn-logout" @click="handleLogout">
              <span>退出</span>
            </button>
          </template>
          <template v-else>
            <router-link to="/login" class="btn btn-ghost btn-sm">登录</router-link>
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
      <div class="container footer-content">
        <div class="footer-brand">
          <span class="brand-icon">⚡</span>
          <span>DisSecKill</span>
        </div>
        <p class="footer-text">分布式秒杀系统 · Vue 3 + FastAPI + Redis + Kafka</p>
        <div class="footer-links">
          <a href="#" class="footer-link">GitHub</a>
          <span class="divider-dot">·</span>
          <a href="#" class="footer-link">文档</a>
          <span class="divider-dot">·</span>
          <a href="/admin" class="footer-link">商家后台</a>
        </div>
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
  position: sticky;
  top: 0;
  z-index: 100;
  background: rgba(13, 13, 20, 0.85);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--border-color);
}

.navbar-inner {
  display: flex;
  align-items: center;
  height: 70px;
  gap: 40px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 1.3rem;
  letter-spacing: 0.1em;
  color: var(--text-primary);
}

.brand-icon {
  font-size: 1.5rem;
  animation: pulse-glow 2s infinite;
}

.brand-text {
  color: var(--text-primary);
}

.brand-text .accent {
  color: var(--primary);
  text-shadow: 0 0 20px var(--primary-glow);
}

.nav-links {
  display: flex;
  gap: 4px;
  flex: 1;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 18px;
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  font-family: var(--font-body);
  font-weight: 500;
  font-size: 0.95rem;
  transition: all var(--transition);
  position: relative;
}

.nav-icon {
  font-size: 1.1rem;
}

.nav-icon.pulse {
  animation: pulse-glow 1.5s infinite;
}

.nav-link:hover {
  color: var(--text-primary);
  background: var(--bg-hover);
}

.nav-link.active {
  color: var(--primary);
  background: var(--primary-bg);
}

.nav-link.active::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 50%;
  transform: translateX(-50%);
  width: 30px;
  height: 2px;
  background: var(--primary);
  box-shadow: 0 0 10px var(--primary);
}

.seckill-link {
  position: relative;
}

.live-badge {
  position: absolute;
  top: 2px;
  right: 4px;
  font-family: var(--font-display);
  font-size: 0.5rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  color: #fff;
  background: var(--accent);
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  animation: pulse-glow 1.5s infinite;
}

.nav-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.user-badge {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 12px 6px 6px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-full);
  color: var(--text-primary);
  transition: all var(--transition);
}

.user-badge:hover {
  border-color: var(--primary);
  box-shadow: var(--glow-primary);
}

.avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--primary-dark), var(--primary));
  color: var(--bg-void);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 0.85rem;
}

.username {
  font-weight: 500;
  font-size: 0.9rem;
}

.btn-logout {
  background: transparent;
  border: 1px solid var(--border-color);
  color: var(--text-muted);
  cursor: pointer;
  font-family: var(--font-body);
  font-size: 0.85rem;
  padding: 8px 16px;
  border-radius: var(--radius-md);
  transition: all var(--transition);
}

.btn-logout:hover {
  color: var(--danger);
  border-color: var(--danger);
  background: rgba(255, 46, 99, 0.1);
}

/* ===== 主内容 ===== */
.main-content {
  flex: 1;
  padding: 40px 0;
}

/* ===== 页脚 ===== */
.footer {
  padding: 40px 0;
  background: var(--bg-void);
  border-top: 1px solid var(--border-color);
}

.footer-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  text-align: center;
}

.footer-brand {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-display);
  font-size: 1rem;
  letter-spacing: 0.1em;
  color: var(--text-primary);
}

.footer-text {
  color: var(--text-muted);
  font-size: 0.85rem;
}

.footer-links {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}

.footer-link {
  color: var(--text-secondary);
  font-size: 0.85rem;
  transition: color var(--transition);
}

.footer-link:hover {
  color: var(--primary);
}

.divider-dot {
  color: var(--text-muted);
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
  .live-badge {
    display: none;
  }
}
</style>
