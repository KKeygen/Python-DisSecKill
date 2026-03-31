<template>
  <div class="home">
    <!-- 霓虹 Hero 区域 -->
    <section class="hero">
      <!-- 背景装饰 -->
      <div class="hero-bg">
        <div class="grid-lines"></div>
        <div class="glow-orb glow-1"></div>
        <div class="glow-orb glow-2"></div>
        <div class="scan-line"></div>
      </div>

      <div class="container hero-container">
        <div class="hero-content">
          <div class="hero-badge" data-aos="fade-down">
            <span class="badge-dot"></span>
            <span>SYSTEM ONLINE</span>
          </div>
          
          <h1 class="hero-title" data-aos="fade-up">
            <span class="title-line">分布式</span>
            <span class="title-highlight">
              <span class="neon-text">秒杀</span>
              <span class="glitch" data-text="秒杀">秒杀</span>
            </span>
            <span class="title-line">系统</span>
          </h1>
          
          <p class="hero-desc" data-aos="fade-up" data-aos-delay="100">
            <span class="typing-text">
              基于 Python 微服务架构 · Redis 原子扣减 · Kafka 异步下单<br/>
              高并发 · 零超卖 · 最终一致性
            </span>
          </p>
          
          <div class="hero-actions" data-aos="fade-up" data-aos-delay="200">
            <router-link to="/seckill" class="btn btn-danger btn-lg pulse-btn">
              <span class="btn-icon">⚡</span>
              <span>立即抢购</span>
            </router-link>
            <router-link to="/goods" class="btn btn-outline btn-lg">
              <span>浏览商品</span>
              <span class="btn-arrow">→</span>
            </router-link>
          </div>
        </div>

        <!-- 右侧数据面板 -->
        <div class="hero-panel" data-aos="fade-left" data-aos-delay="300">
          <div class="panel-header">
            <span class="panel-title">SYSTEM STATUS</span>
            <span class="panel-indicator online"></span>
          </div>
          
          <div class="stats-grid">
            <div class="stat-card" v-for="(stat, idx) in stats" :key="stat.label" :style="{ animationDelay: idx * 0.1 + 's' }">
              <div class="stat-icon">{{ stat.icon }}</div>
              <div class="stat-value">
                <span class="counter">{{ stat.value }}</span>
                <span class="stat-unit">{{ stat.unit }}</span>
              </div>
              <div class="stat-label">{{ stat.label }}</div>
              <div class="stat-bar">
                <div class="stat-bar-fill" :style="{ width: stat.percent + '%' }"></div>
              </div>
            </div>
          </div>
          
          <div class="panel-footer">
            <span class="status-text">All systems operational</span>
          </div>
        </div>
      </div>
    </section>

    <!-- 特性介绍 -->
    <section class="features container">
      <div class="section-header" data-aos="fade-up">
        <span class="section-tag">FEATURES</span>
        <h2 class="section-title">核心<span class="text-primary">技术栈</span></h2>
        <p class="section-desc">高性能 · 高可用 · 可扩展的分布式架构设计</p>
      </div>

      <div class="features-grid">
        <div 
          class="feature-card" 
          v-for="(f, idx) in features" 
          :key="f.title"
          data-aos="fade-up"
          :data-aos-delay="idx * 50"
        >
          <div class="feature-glow"></div>
          <div class="feature-icon">{{ f.icon }}</div>
          <h3 class="feature-title">{{ f.title }}</h3>
          <p class="feature-desc">{{ f.desc }}</p>
          <div class="feature-tag">{{ f.tag }}</div>
        </div>
      </div>
    </section>

    <!-- 架构展示 -->
    <section class="architecture container">
      <div class="section-header" data-aos="fade-up">
        <span class="section-tag">ARCHITECTURE</span>
        <h2 class="section-title">系统<span class="text-accent">架构</span></h2>
      </div>

      <div class="arch-diagram" data-aos="zoom-in">
        <div class="arch-layer">
          <div class="arch-node client">
            <span class="node-icon">👤</span>
            <span class="node-label">用户终端</span>
          </div>
        </div>
        
        <div class="arch-arrow">
          <div class="arrow-line"></div>
          <div class="arrow-pulse"></div>
        </div>
        
        <div class="arch-layer gateway">
          <div class="arch-node">
            <span class="node-icon">🌐</span>
            <span class="node-label">API Gateway</span>
          </div>
        </div>
        
        <div class="arch-arrow">
          <div class="arrow-line"></div>
          <div class="arrow-pulse"></div>
        </div>
        
        <div class="arch-layer services">
          <div class="arch-node" v-for="svc in services" :key="svc.name">
            <span class="node-icon">{{ svc.icon }}</span>
            <span class="node-label">{{ svc.name }}</span>
          </div>
        </div>
        
        <div class="arch-arrow">
          <div class="arrow-line"></div>
          <div class="arrow-pulse"></div>
        </div>
        
        <div class="arch-layer infra">
          <div class="arch-node redis">
            <span class="node-icon">🔴</span>
            <span class="node-label">Redis</span>
          </div>
          <div class="arch-node kafka">
            <span class="node-icon">📨</span>
            <span class="node-label">Kafka</span>
          </div>
          <div class="arch-node mysql">
            <span class="node-icon">🗄️</span>
            <span class="node-label">MySQL</span>
          </div>
        </div>
      </div>
    </section>

    <!-- CTA -->
    <section class="cta" data-aos="fade-up">
      <div class="container cta-content">
        <h2 class="cta-title">准备好开始抢购了吗？</h2>
        <p class="cta-desc">体验高性能分布式秒杀系统</p>
        <div class="cta-actions">
          <router-link v-if="!auth.isLoggedIn" to="/register" class="btn btn-primary btn-lg">
            <span>立即注册</span>
          </router-link>
          <router-link to="/seckill" class="btn btn-danger btn-lg">
            <span>⚡ 参与秒杀</span>
          </router-link>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { useAuthStore } from '../stores/auth'
import { onMounted } from 'vue'

const auth = useAuthStore()

const stats = [
  { icon: '🏗️', value: '4', unit: '', label: '微服务', percent: 100 },
  { icon: '⚡', value: '10K', unit: '+', label: 'QPS 并发', percent: 85 },
  { icon: '🎯', value: '0', unit: '', label: '超卖事故', percent: 100 },
  { icon: '⏱️', value: '<50', unit: 'ms', label: '响应延迟', percent: 95 },
]

const features = [
  { icon: '🏗️', title: '微服务架构', desc: '用户、商品、订单、库存四大独立服务，独立部署、弹性扩容', tag: 'FastAPI' },
  { icon: '⚡', title: 'Redis 扣减', desc: 'Lua脚本原子操作，限购N件校验，毫秒级库存扣减', tag: 'Atomic' },
  { icon: '📨', title: 'Kafka 异步', desc: '消息队列削峰填谷，TCC/Saga模式保障最终一致性', tag: 'Eventually Consistent' },
  { icon: '🔒', title: '乐观锁兜底', desc: '数据库version字段二次校验，多重保障数据安全', tag: 'Optimistic Lock' },
  { icon: '🚀', title: '高性能框架', desc: 'FastAPI + Uvicorn异步运行，轻松支撑万级并发', tag: 'Async I/O' },
  { icon: '🐳', title: '容器化部署', desc: 'Docker Compose一键启动，环境标准化零依赖', tag: 'Containerized' },
]

const services = [
  { icon: '👤', name: '用户服务' },
  { icon: '📦', name: '商品服务' },
  { icon: '📋', name: '订单服务' },
  { icon: '📊', name: '库存服务' },
]

onMounted(() => {
  // 简单的入场动画
  const elements = document.querySelectorAll('[data-aos]')
  elements.forEach((el, idx) => {
    setTimeout(() => {
      el.classList.add('aos-animate')
    }, idx * 100)
  })
})
</script>

<style scoped>
/* ===== Hero Section ===== */
.hero {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  overflow: hidden;
  padding: 80px 0;
}

.hero-bg {
  position: absolute;
  inset: 0;
  overflow: hidden;
}

.grid-lines {
  position: absolute;
  inset: 0;
  background-image: 
    linear-gradient(rgba(0, 245, 212, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 245, 212, 0.05) 1px, transparent 1px);
  background-size: 80px 80px;
  transform: perspective(500px) rotateX(60deg);
  transform-origin: center top;
  opacity: 0.5;
}

.glow-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  animation: float 8s ease-in-out infinite;
}

.glow-1 {
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, var(--primary-glow), transparent 70%);
  top: -100px;
  right: 10%;
}

.glow-2 {
  width: 300px;
  height: 300px;
  background: radial-gradient(circle, var(--accent-glow), transparent 70%);
  bottom: 0;
  left: 10%;
  animation-delay: -4s;
}

.scan-line {
  position: absolute;
  width: 100%;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--primary), transparent);
  animation: scan 4s linear infinite;
  opacity: 0.3;
}

@keyframes scan {
  0% { top: -10%; }
  100% { top: 110%; }
}

.hero-container {
  display: flex;
  align-items: center;
  gap: 60px;
  position: relative;
  z-index: 1;
}

.hero-content {
  flex: 1;
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-full);
  font-family: var(--font-display);
  font-size: 0.7rem;
  letter-spacing: 0.2em;
  color: var(--primary);
  margin-bottom: 24px;
}

.badge-dot {
  width: 8px;
  height: 8px;
  background: var(--success);
  border-radius: 50%;
  animation: pulse-glow 2s infinite;
  box-shadow: 0 0 10px var(--success);
}

.hero-title {
  font-size: 4.5rem;
  font-weight: 700;
  line-height: 1.1;
  margin-bottom: 24px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.title-line {
  display: block;
}

.title-highlight {
  position: relative;
  display: inline-block;
}

.title-highlight .neon-text {
  color: var(--primary);
  text-shadow: 
    0 0 10px var(--primary),
    0 0 20px var(--primary),
    0 0 40px var(--primary),
    0 0 80px var(--primary);
  animation: neon-flicker 3s infinite;
}

.glitch {
  position: absolute;
  top: 0;
  left: 0;
  opacity: 0;
  color: var(--accent);
  animation: glitch 3s infinite;
}

@keyframes glitch {
  0%, 90%, 100% { opacity: 0; transform: translate(0); }
  92% { opacity: 0.8; transform: translate(-2px, 2px); }
  94% { opacity: 0.8; transform: translate(2px, -2px); }
  96% { opacity: 0; }
}

.hero-desc {
  font-size: 1.15rem;
  color: var(--text-secondary);
  line-height: 1.8;
  margin-bottom: 40px;
  max-width: 500px;
}

.hero-actions {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.pulse-btn {
  animation: pulse-glow 2s infinite;
}

.btn-icon {
  font-size: 1.2em;
}

.btn-arrow {
  transition: transform 0.3s;
}

.btn:hover .btn-arrow {
  transform: translateX(4px);
}

/* ===== Hero Panel ===== */
.hero-panel {
  flex: 0 0 380px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  overflow: hidden;
  box-shadow: var(--shadow-xl), var(--glow-primary);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-elevated);
}

.panel-title {
  font-family: var(--font-display);
  font-size: 0.75rem;
  letter-spacing: 0.15em;
  color: var(--text-muted);
}

.panel-indicator {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.panel-indicator.online {
  background: var(--success);
  box-shadow: 0 0 10px var(--success);
  animation: pulse-glow 2s infinite;
}

.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1px;
  background: var(--border-color);
}

.stat-card {
  background: var(--bg-card);
  padding: 20px;
  animation: fade-in 0.5s ease forwards;
  opacity: 0;
}

@keyframes fade-in {
  to { opacity: 1; }
}

.stat-icon {
  font-size: 1.5rem;
  margin-bottom: 8px;
}

.stat-value {
  font-family: var(--font-display);
  font-size: 2rem;
  font-weight: 700;
  color: var(--primary);
  text-shadow: 0 0 20px var(--primary-glow);
}

.stat-unit {
  font-size: 0.9rem;
  color: var(--text-muted);
}

.stat-label {
  font-size: 0.8rem;
  color: var(--text-muted);
  margin: 4px 0 12px;
}

.stat-bar {
  height: 3px;
  background: var(--bg-elevated);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.stat-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--primary-dark), var(--primary));
  border-radius: var(--radius-full);
  transition: width 1s ease;
}

.panel-footer {
  padding: 12px 20px;
  border-top: 1px solid var(--border-color);
  background: var(--bg-elevated);
}

.status-text {
  font-size: 0.75rem;
  color: var(--success);
  display: flex;
  align-items: center;
  gap: 6px;
}

.status-text::before {
  content: '●';
  animation: pulse-glow 2s infinite;
}

/* ===== Features Section ===== */
.features {
  padding: 100px 0;
}

.section-header {
  text-align: center;
  margin-bottom: 60px;
}

.section-tag {
  display: inline-block;
  font-family: var(--font-display);
  font-size: 0.7rem;
  letter-spacing: 0.3em;
  color: var(--primary);
  padding: 6px 16px;
  border: 1px solid var(--primary);
  border-radius: var(--radius-full);
  margin-bottom: 16px;
}

.section-title {
  font-size: 2.5rem;
  margin-bottom: 12px;
}

.section-desc {
  color: var(--text-muted);
  font-size: 1rem;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
}

.feature-card {
  position: relative;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 32px;
  overflow: hidden;
  transition: all 0.4s ease;
}

.feature-card:hover {
  border-color: var(--primary);
  transform: translateY(-8px);
  box-shadow: var(--glow-primary);
}

.feature-glow {
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(circle at center, var(--primary-bg), transparent 70%);
  opacity: 0;
  transition: opacity 0.4s;
}

.feature-card:hover .feature-glow {
  opacity: 1;
}

.feature-icon {
  font-size: 2.5rem;
  margin-bottom: 16px;
  position: relative;
  z-index: 1;
}

.feature-title {
  font-size: 1.2rem;
  margin-bottom: 12px;
  position: relative;
  z-index: 1;
}

.feature-desc {
  color: var(--text-secondary);
  font-size: 0.9rem;
  line-height: 1.7;
  margin-bottom: 16px;
  position: relative;
  z-index: 1;
}

.feature-tag {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: var(--primary);
  padding: 4px 10px;
  background: var(--primary-bg);
  border-radius: var(--radius-sm);
  position: relative;
  z-index: 1;
}

/* ===== Architecture Section ===== */
.architecture {
  padding: 80px 0 120px;
}

.arch-diagram {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
  padding: 40px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
}

.arch-layer {
  display: flex;
  gap: 16px;
  justify-content: center;
  flex-wrap: wrap;
}

.arch-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 16px 24px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  transition: all 0.3s;
}

.arch-node:hover {
  border-color: var(--primary);
  box-shadow: var(--glow-primary);
}

.node-icon {
  font-size: 1.8rem;
}

.node-label {
  font-family: var(--font-display);
  font-size: 0.75rem;
  letter-spacing: 0.05em;
  color: var(--text-secondary);
}

.arch-arrow {
  position: relative;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.arrow-line {
  width: 2px;
  height: 100%;
  background: linear-gradient(to bottom, var(--primary), transparent);
}

.arrow-pulse {
  position: absolute;
  width: 8px;
  height: 8px;
  background: var(--primary);
  border-radius: 50%;
  animation: arrow-flow 1.5s infinite;
  box-shadow: 0 0 10px var(--primary);
}

@keyframes arrow-flow {
  0% { top: 0; opacity: 1; }
  100% { top: 100%; opacity: 0; }
}

/* ===== CTA Section ===== */
.cta {
  padding: 80px 0;
  background: linear-gradient(135deg, var(--bg-elevated), var(--bg-card));
  border-top: 1px solid var(--border-color);
  border-bottom: 1px solid var(--border-color);
}

.cta-content {
  text-align: center;
}

.cta-title {
  font-size: 2.5rem;
  margin-bottom: 12px;
}

.cta-desc {
  color: var(--text-muted);
  margin-bottom: 32px;
}

.cta-actions {
  display: flex;
  gap: 16px;
  justify-content: center;
}

/* ===== AOS Animation ===== */
[data-aos] {
  opacity: 0;
  transform: translateY(20px);
  transition: all 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}

[data-aos="fade-down"] {
  transform: translateY(-20px);
}

[data-aos="fade-left"] {
  transform: translateX(40px);
}

[data-aos="zoom-in"] {
  transform: scale(0.95);
}

[data-aos].aos-animate {
  opacity: 1;
  transform: translate(0) scale(1);
}

/* ===== Responsive ===== */
@media (max-width: 1024px) {
  .hero-container {
    flex-direction: column;
    text-align: center;
  }
  
  .hero-panel {
    flex: none;
    width: 100%;
    max-width: 400px;
  }
  
  .hero-desc {
    max-width: 100%;
  }
  
  .hero-actions {
    justify-content: center;
  }
  
  .features-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .hero {
    padding: 60px 0;
    min-height: auto;
  }
  
  .hero-title {
    font-size: 2.5rem;
  }
  
  .features-grid {
    grid-template-columns: 1fr;
  }
  
  .arch-layer.services {
    flex-direction: column;
  }
  
  .cta-actions {
    flex-direction: column;
    align-items: center;
  }
}
</style>
