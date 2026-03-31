<template>
  <div class="admin-layout">
    <!-- 侧边栏 -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <router-link to="/admin" class="brand">
          <span class="brand-icon">⚡</span>
          <span class="brand-text">ADMIN</span>
        </router-link>
      </div>
      
      <nav class="sidebar-nav">
        <router-link 
          v-for="item in navItems" 
          :key="item.path" 
          :to="item.path" 
          class="nav-item"
          :class="{ active: isActive(item.path) }"
        >
          <span class="nav-icon">{{ item.icon }}</span>
          <span class="nav-label">{{ item.label }}</span>
        </router-link>
      </nav>
      
      <div class="sidebar-footer">
        <router-link to="/" class="back-link">
          <span>← 返回前台</span>
        </router-link>
        <div class="user-info" v-if="auth.user">
          <span class="avatar">{{ auth.user.username?.charAt(0)?.toUpperCase() }}</span>
          <span class="username">{{ auth.user.username }}</span>
        </div>
      </div>
    </aside>

    <!-- 主内容区 -->
    <main class="main-area">
      <header class="topbar">
        <div class="topbar-left">
          <h1 class="page-title">{{ currentPageTitle }}</h1>
        </div>
        <div class="topbar-right">
          <div class="status-indicator">
            <span class="status-dot online"></span>
            <span>系统运行中</span>
          </div>
        </div>
      </header>
      
      <div class="content-area">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../../stores/auth'

const route = useRoute()
const auth = useAuthStore()

const navItems = [
  { path: '/admin/dashboard', label: '数据概览', icon: '📊' },
  { path: '/admin/products', label: '商品管理', icon: '📦' },
  { path: '/admin/seckill', label: '秒杀管理', icon: '⚡' },
  { path: '/admin/orders', label: '订单管理', icon: '📋' },
]

const isActive = (path: string) => route.path === path

const currentPageTitle = computed(() => {
  const item = navItems.find(i => route.path.startsWith(i.path))
  return item?.label || '管理后台'
})
</script>

<style scoped>
.admin-layout {
  display: flex;
  min-height: 100vh;
  background: var(--bg-void);
}

/* ===== 侧边栏 ===== */
.sidebar {
  width: 260px;
  background: var(--bg-card);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  z-index: 100;
}

.sidebar-header {
  padding: 24px;
  border-bottom: 1px solid var(--border-color);
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  font-family: var(--font-display);
  font-size: 1.2rem;
  font-weight: 700;
  letter-spacing: 0.15em;
  color: var(--primary);
}

.brand-icon {
  font-size: 1.5rem;
  animation: pulse-glow 2s infinite;
}

.sidebar-nav {
  flex: 1;
  padding: 16px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  font-size: 0.95rem;
  font-weight: 500;
  transition: all var(--transition);
  position: relative;
}

.nav-item:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.nav-item.active {
  background: var(--primary-bg);
  color: var(--primary);
}

.nav-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 24px;
  background: var(--primary);
  border-radius: 0 2px 2px 0;
  box-shadow: 0 0 10px var(--primary);
}

.nav-icon {
  font-size: 1.2rem;
}

.sidebar-footer {
  padding: 16px;
  border-top: 1px solid var(--border-color);
}

.back-link {
  display: block;
  padding: 12px 16px;
  border-radius: var(--radius-md);
  color: var(--text-muted);
  font-size: 0.9rem;
  text-align: center;
  transition: all var(--transition);
  margin-bottom: 12px;
}

.back-link:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  background: var(--bg-elevated);
  border-radius: var(--radius-md);
}

.avatar {
  width: 36px;
  height: 36px;
  background: linear-gradient(135deg, var(--primary-dark), var(--primary));
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 0.9rem;
  color: var(--bg-void);
}

.username {
  font-size: 0.9rem;
  color: var(--text-primary);
}

/* ===== 主内容区 ===== */
.main-area {
  flex: 1;
  margin-left: 260px;
  display: flex;
  flex-direction: column;
}

.topbar {
  height: 70px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 32px;
  position: sticky;
  top: 0;
  z-index: 50;
}

.page-title {
  font-family: var(--font-display);
  font-size: 1.3rem;
  font-weight: 600;
  letter-spacing: 0.05em;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.85rem;
  color: var(--text-muted);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-dot.online {
  background: var(--success);
  box-shadow: 0 0 10px var(--success);
  animation: pulse-glow 2s infinite;
}

.content-area {
  flex: 1;
  padding: 32px;
  overflow-y: auto;
}

/* ===== 动画 ===== */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* ===== 响应式 ===== */
@media (max-width: 1024px) {
  .sidebar {
    width: 80px;
  }
  
  .brand-text,
  .nav-label,
  .username,
  .back-link span {
    display: none;
  }
  
  .sidebar-header {
    padding: 20px;
    text-align: center;
  }
  
  .nav-item {
    justify-content: center;
    padding: 14px;
  }
  
  .nav-icon {
    font-size: 1.4rem;
  }
  
  .main-area {
    margin-left: 80px;
  }
  
  .user-info {
    justify-content: center;
  }
}
</style>
