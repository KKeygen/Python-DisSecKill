<template>
  <div class="home container">
    <!-- Hero区域 -->
    <section class="hero">
      <div class="hero-content">
        <h1 class="hero-title">
          分布式<span class="gradient-text">秒杀</span>系统
        </h1>
        <p class="hero-desc">
          基于 Python 微服务架构，Redis 原子扣减 + RabbitMQ 异步下单，<br />
          支撑高并发秒杀场景。
        </p>
        <div class="hero-actions">
          <router-link to="/goods" class="btn btn-primary btn-lg">浏览商品</router-link>
          <router-link v-if="!auth.isLoggedIn" to="/register" class="btn btn-outline btn-lg">立即注册</router-link>
        </div>
      </div>
      <div class="hero-visual">
        <div class="visual-card">
          <div class="stats-row">
            <div class="stat">
              <span class="stat-value">4</span>
              <span class="stat-label">微服务</span>
            </div>
            <div class="stat">
              <span class="stat-value">10K+</span>
              <span class="stat-label">QPS</span>
            </div>
            <div class="stat">
              <span class="stat-value">0</span>
              <span class="stat-label">超卖</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 特性介绍 -->
    <section class="features">
      <h2 class="section-title">系统特性</h2>
      <div class="features-grid">
        <div class="feature-card" v-for="f in features" :key="f.title">
          <span class="feature-icon">{{ f.icon }}</span>
          <h3>{{ f.title }}</h3>
          <p>{{ f.desc }}</p>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()

const features = [
  { icon: '🏗️', title: '微服务架构', desc: '用户、商品、订单、库存四大独立服务，各自部署扩容' },
  { icon: '⚡', title: 'Redis扣减', desc: 'Lua脚本原子操作，毫秒级库存扣减，杜绝超卖' },
  { icon: '📨', title: '异步下单', desc: 'RabbitMQ消息队列，流量削峰填谷，订单最终一致' },
  { icon: '🔒', title: '乐观锁兜底', desc: '数据库version字段二次校验，多重保障数据安全' },
  { icon: '🚀', title: '高性能框架', desc: 'FastAPI + Uvicorn异步运行，轻松支撑万级并发' },
  { icon: '🐳', title: '容器化部署', desc: 'Docker Compose一键启动，环境标准化零依赖' },
]
</script>

<style scoped>
/* ===== Hero ===== */
.hero {
  display: flex;
  align-items: center;
  gap: 48px;
  padding: 48px 0 64px;
}

.hero-content {
  flex: 1;
}

.hero-title {
  font-size: 3rem;
  font-weight: 700;
  line-height: 1.2;
  margin-bottom: 16px;
}

.gradient-text {
  background: linear-gradient(135deg, var(--primary), #8b5cf6, #ec4899);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.hero-desc {
  font-size: 1.1rem;
  color: var(--text-secondary);
  margin-bottom: 32px;
  line-height: 1.8;
}

.hero-actions {
  display: flex;
  gap: 16px;
}

.hero-visual {
  flex: 0 0 320px;
}

.visual-card {
  background: linear-gradient(135deg, var(--primary), #8b5cf6);
  border-radius: var(--radius-xl);
  padding: 40px 32px;
  color: #fff;
  box-shadow: 0 20px 40px rgba(79, 109, 245, 0.25);
}

.stats-row {
  display: flex;
  gap: 24px;
  text-align: center;
}

.stat {
  flex: 1;
}

.stat-value {
  display: block;
  font-size: 2rem;
  font-weight: 700;
}

.stat-label {
  font-size: 0.85rem;
  opacity: 0.85;
}

/* ===== Features ===== */
.features {
  padding: 48px 0 64px;
}

.section-title {
  font-size: 1.8rem;
  font-weight: 700;
  text-align: center;
  margin-bottom: 40px;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
}

.feature-card {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  padding: 28px;
  box-shadow: var(--shadow-sm);
  transition: all 0.3s ease;
  border: 1px solid var(--border-light);
}

.feature-card:hover {
  box-shadow: var(--shadow-lg);
  transform: translateY(-4px);
}

.feature-icon {
  font-size: 2rem;
  margin-bottom: 12px;
  display: block;
}

.feature-card h3 {
  font-size: 1.1rem;
  font-weight: 600;
  margin-bottom: 8px;
}

.feature-card p {
  color: var(--text-secondary);
  font-size: 0.9rem;
  line-height: 1.6;
}

/* ===== 响应式 ===== */
@media (max-width: 768px) {
  .hero {
    flex-direction: column;
    text-align: center;
    padding: 32px 0 48px;
  }
  .hero-title {
    font-size: 2rem;
  }
  .hero-actions {
    justify-content: center;
  }
  .hero-visual {
    flex: none;
    width: 100%;
    max-width: 320px;
  }
  .features-grid {
    grid-template-columns: 1fr;
  }
}
</style>
