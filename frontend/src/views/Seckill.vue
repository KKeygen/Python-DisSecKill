<template>
  <div class="seckill-page">
    <!-- 霓虹背景 -->
    <div class="page-bg">
      <div class="bg-grid"></div>
      <div class="bg-glow glow-1"></div>
      <div class="bg-glow glow-2"></div>
    </div>

    <div class="container">
      <!-- 标题区域 -->
      <header class="seckill-header">
        <div class="header-badge">
          <span class="badge-dot"></span>
          <span>FLASH SALE</span>
        </div>
        <h1 class="page-title">
          <span class="title-icon">⚡</span>
          <span class="title-text">限时<span class="neon-accent">秒杀</span></span>
        </h1>
        <p class="seckill-subtitle">限量抢购 · 手慢无 · 先到先得</p>
      </header>

      <!-- 倒计时面板 -->
      <div class="countdown-panel">
        <div class="countdown-left">
          <div class="countdown-status" :class="{ active: isActive }">
            <span class="status-dot"></span>
            <span class="status-text">{{ isActive ? '抢购进行中' : '即将开始' }}</span>
          </div>
          <div class="countdown-label">距离{{ countdownState }}还剩</div>
        </div>
        
        <div class="countdown-timer">
          <div class="time-block">
            <div class="time-value">
              <span class="digit">{{ timeDisplay.hours[0] }}</span>
              <span class="digit">{{ timeDisplay.hours[1] }}</span>
            </div>
            <span class="time-unit">HOURS</span>
          </div>
          <span class="time-sep">:</span>
          <div class="time-block">
            <div class="time-value">
              <span class="digit">{{ timeDisplay.minutes[0] }}</span>
              <span class="digit">{{ timeDisplay.minutes[1] }}</span>
            </div>
            <span class="time-unit">MINS</span>
          </div>
          <span class="time-sep">:</span>
          <div class="time-block">
            <div class="time-value">
              <span class="digit">{{ timeDisplay.seconds[0] }}</span>
              <span class="digit">{{ timeDisplay.seconds[1] }}</span>
            </div>
            <span class="time-unit">SECS</span>
          </div>
        </div>
      </div>

      <!-- 秒杀商品列表 -->
      <div class="seckill-grid">
        <div 
          v-for="(item, idx) in seckillGoods" 
          :key="item.id" 
          class="seckill-card"
          :style="{ animationDelay: idx * 0.1 + 's' }"
        >
          <!-- 热度标签 -->
          <div class="hot-badge" v-if="item.progressPercent > 70">
            <span>🔥 HOT</span>
          </div>
          
          <div class="card-image">
            <div class="image-placeholder">{{ item.name.charAt(0) }}</div>
            <!-- 进度条 -->
            <div class="progress-wrapper">
              <div class="progress-track">
                <div 
                  class="progress-fill" 
                  :style="{ width: item.progressPercent + '%' }"
                  :class="{ danger: item.progressPercent > 80 }"
                ></div>
              </div>
              <span class="progress-label">已抢 {{ item.progressPercent }}%</span>
            </div>
          </div>
          
          <div class="card-content">
            <h3 class="card-title">{{ item.name }}</h3>
            
            <div class="price-section">
              <div class="price-current">
                <span class="currency">¥</span>
                <span class="amount">{{ item.seckill_price }}</span>
              </div>
              <div class="price-original">
                <span>原价 ¥{{ item.price }}</span>
                <span class="discount-tag">{{ Math.round((1 - item.seckill_price / item.price) * 100) }}% OFF</span>
              </div>
            </div>

            <!-- 限购信息 -->
            <div class="limit-section">
              <div class="limit-item">
                <span class="limit-icon">🎯</span>
                <span>限购 {{ item.limit_per_user }} 件</span>
              </div>
              <div class="limit-item" v-if="auth.isLoggedIn">
                <span class="limit-icon">✓</span>
                <span>已购 {{ item.user_purchased }} 件</span>
              </div>
            </div>
            
            <!-- 数量选择器 -->
            <div v-if="!item.grabbed && getMaxBuyCount(item) > 0" class="quantity-section">
              <span class="qty-label">购买数量</span>
              <div class="quantity-control">
                <button class="qty-btn" @click="decreaseCount(item)" :disabled="item.selected_count <= 1">−</button>
                <span class="qty-value">{{ item.selected_count }}</span>
                <button class="qty-btn" @click="increaseCount(item)" :disabled="item.selected_count >= getMaxBuyCount(item)">+</button>
              </div>
            </div>

            <!-- 抢购按钮 -->
            <button
              class="grab-btn"
              :class="{ 
                disabled: !isActive || item.grabbed || getMaxBuyCount(item) <= 0,
                grabbing: item.grabbing 
              }"
              :disabled="!isActive || item.grabbed || getMaxBuyCount(item) <= 0"
              @click="handleGrab(item)"
            >
              <span class="btn-content">
                <span v-if="item.grabbed || getMaxBuyCount(item) <= 0">已达限购</span>
                <span v-else-if="item.grabbing" class="grabbing-text">
                  <span class="spinner"></span>
                  抢购中
                </span>
                <span v-else-if="!isActive">未开始</span>
                <span v-else>
                  <span class="btn-icon">⚡</span>
                  立即抢购
                </span>
              </span>
            </button>
          </div>

          <!-- 结果消息 -->
          <div v-if="item.message" class="result-toast" :class="item.success ? 'success' : 'error'">
            <span class="toast-icon">{{ item.success ? '✓' : '✕' }}</span>
            <span>{{ item.message }}</span>
          </div>
        </div>
      </div>

      <div v-if="seckillGoods.length === 0" class="empty-state">
        <div class="empty-icon">📦</div>
        <p class="empty-text">暂无秒杀活动</p>
        <p class="empty-hint">敬请期待更多精彩活动</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { goodsApi, inventoryApi, orderApi } from '../api'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()

interface SeckillItem {
  id: number
  name: string
  price: number
  seckill_price: number
  seckill_start: string
  seckill_end: string
  progressPercent: number
  grabbing: boolean
  grabbed: boolean
  success: boolean
  message: string
  limit_per_user: number  // 限购数量
  user_purchased: number  // 用户已购数量
  selected_count: number  // 选择购买数量
}

const seckillGoods = ref<SeckillItem[]>([])
const now = ref(Date.now())
let timer: number | null = null

// 秒杀时间（模拟：默认使用第一个秒杀商品的时间或未来2小时）
const seckillStart = ref(Date.now() - 600_000) // 模拟已开始10分钟
const seckillEnd = ref(Date.now() + 7200_000) // 2小时后结束

const isActive = computed(() => now.value >= seckillStart.value && now.value < seckillEnd.value)
const countdownState = computed(() => {
  if (now.value < seckillStart.value) return '开始'
  if (now.value < seckillEnd.value) return '结束'
  return '已结束'
})

const timeDisplay = computed(() => {
  let target = seckillEnd.value
  if (now.value < seckillStart.value) target = seckillStart.value
  const diff = Math.max(0, target - now.value)
  const totalSec = Math.floor(diff / 1000)
  return {
    hours: String(Math.floor(totalSec / 3600)).padStart(2, '0'),
    minutes: String(Math.floor((totalSec % 3600) / 60)).padStart(2, '0'),
    seconds: String(totalSec % 60).padStart(2, '0'),
  }
})

async function loadSeckillGoods() {
  try {
    const res = await goodsApi.list({ page: 1, size: 50 })
    // 筛选秒杀商品（如果后端没有秒杀商品，用模拟数据）
    const items = res.data.items.filter((g: any) => g.is_seckill)
    if (items.length > 0) {
      seckillGoods.value = items.map((g: any) => ({
        ...g,
        progressPercent: Math.floor(Math.random() * 60 + 20),
        grabbing: false,
        grabbed: false,
        success: false,
        message: '',
        limit_per_user: g.limit_per_user || 2,  // 默认限购2件
        user_purchased: 0,
        selected_count: 1,
      }))
      // 如果用户已登录，查询每个商品的用户购买信息
      if (auth.isLoggedIn && auth.user) {
        for (const item of seckillGoods.value) {
          try {
            const info = await inventoryApi.getUserSeckillInfo(item.id, auth.user.id)
            if (info.data) {
              item.user_purchased = info.data.purchased_count || 0
              item.limit_per_user = info.data.limit_per_user || 2
              if (item.user_purchased >= item.limit_per_user) {
                item.grabbed = true
              }
            }
          } catch { /* ignore */ }
        }
      }
    } else {
      // 模拟数据
      seckillGoods.value = [
        { id: 1, name: '小米14 Ultra 手机', price: 5999, seckill_price: 4999, seckill_start: '', seckill_end: '', progressPercent: 75, grabbing: false, grabbed: false, success: false, message: '', limit_per_user: 2, user_purchased: 0, selected_count: 1 },
        { id: 2, name: '索尼 WH-1000XM5 耳机', price: 2999, seckill_price: 1999, seckill_start: '', seckill_end: '', progressPercent: 42, grabbing: false, grabbed: false, success: false, message: '', limit_per_user: 3, user_purchased: 0, selected_count: 1 },
        { id: 3, name: 'Apple iPad Air 2025', price: 4799, seckill_price: 3899, seckill_start: '', seckill_end: '', progressPercent: 88, grabbing: false, grabbed: false, success: false, message: '', limit_per_user: 1, user_purchased: 0, selected_count: 1 },
        { id: 4, name: '戴森 V15 Detect 吸尘器', price: 4490, seckill_price: 3290, seckill_start: '', seckill_end: '', progressPercent: 31, grabbing: false, grabbed: false, success: false, message: '', limit_per_user: 2, user_purchased: 0, selected_count: 1 },
      ]
    }
  } catch {
    // 出错也用模拟数据
    seckillGoods.value = [
      { id: 1, name: '秒杀商品A', price: 999, seckill_price: 499, seckill_start: '', seckill_end: '', progressPercent: 65, grabbing: false, grabbed: false, success: false, message: '', limit_per_user: 2, user_purchased: 0, selected_count: 1 },
      { id: 2, name: '秒杀商品B', price: 1999, seckill_price: 999, seckill_start: '', seckill_end: '', progressPercent: 33, grabbing: false, grabbed: false, success: false, message: '', limit_per_user: 3, user_purchased: 0, selected_count: 1 },
    ]
  }
}

async function handleGrab(item: SeckillItem) {
  if (!auth.isLoggedIn || !auth.user) {
    item.message = '请先登录后再抢购'
    item.success = false
    return
  }
  // 检查是否还能购买
  const canBuy = item.limit_per_user - item.user_purchased
  if (canBuy <= 0) {
    item.message = '您已达到限购数量'
    item.success = false
    item.grabbed = true
    return
  }
  if (item.selected_count > canBuy) {
    item.message = `您最多还可购买 ${canBuy} 件`
    item.success = false
    return
  }
  item.grabbing = true
  item.message = ''
  try {
    const res = await inventoryApi.seckill({ 
      goods_id: item.id, 
      user_id: auth.user.id,
      count: item.selected_count 
    })
    item.success = res.data.success
    item.message = res.data.message
    if (res.data.success) {
      item.user_purchased += item.selected_count
      item.progressPercent = Math.min(100, item.progressPercent + item.selected_count)
      if (item.user_purchased >= item.limit_per_user) {
        item.grabbed = true
      }
      // 秒杀请求成功后，开始轮询订单结果
      pollResult(item.id)
    }
  } catch (e: any) {
    item.success = false
    item.message = e.response?.data?.detail || '请求失败，请稍后重试'
  } finally {
    item.grabbing = false
  }
}

// 轮询获取秒杀结果
async function pollResult(goodsId: number, maxAttempts = 10) {
  for (let i = 0; i < maxAttempts; i++) {
    await new Promise(resolve => setTimeout(resolve, 1000)) // 等待1秒
    try {
      const res = await orderApi.getSeckillResult(goodsId)
      if (res.data && res.data.order_id) {
        alert(`秒杀成功！订单号: ${res.data.order_id}`)
        return true
      } else if (res.data && res.data.status === 'failed') {
        alert('秒杀失败: ' + (res.data.message || '库存不足'))
        return false
      }
    } catch (err) {
      // 继续轮询
    }
  }
  alert('订单处理中，请稍后在订单页面查看')
  return false
}

// 计算用户还可购买的数量
function getMaxBuyCount(item: SeckillItem): number {
  return Math.max(0, item.limit_per_user - item.user_purchased)
}

// 增减购买数量
function decreaseCount(item: SeckillItem) {
  if (item.selected_count > 1) {
    item.selected_count--
  }
}

function increaseCount(item: SeckillItem) {
  const max = getMaxBuyCount(item)
  if (item.selected_count < max) {
    item.selected_count++
  }
}

onMounted(() => {
  loadSeckillGoods()
  timer = window.setInterval(() => { now.value = Date.now() }, 1000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
/* ===== 页面背景 ===== */
.seckill-page {
  position: relative;
  min-height: 100vh;
  padding-bottom: 80px;
}

.page-bg {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: -1;
}

.bg-grid {
  position: absolute;
  inset: 0;
  background-image: 
    linear-gradient(rgba(255, 46, 99, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 46, 99, 0.03) 1px, transparent 1px);
  background-size: 60px 60px;
}

.bg-glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(100px);
  opacity: 0.4;
}

.glow-1 {
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, var(--accent-glow), transparent 70%);
  top: -200px;
  right: -100px;
}

.glow-2 {
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, var(--primary-glow), transparent 70%);
  bottom: 0;
  left: -100px;
}

/* ===== 头部 ===== */
.seckill-header {
  text-align: center;
  padding: 20px 0 40px;
}

.header-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 20px;
  background: rgba(255, 46, 99, 0.15);
  border: 1px solid rgba(255, 46, 99, 0.3);
  border-radius: var(--radius-full);
  font-family: var(--font-display);
  font-size: 0.7rem;
  letter-spacing: 0.2em;
  color: var(--accent);
  margin-bottom: 20px;
}

.badge-dot {
  width: 8px;
  height: 8px;
  background: var(--accent);
  border-radius: 50%;
  animation: pulse-glow 1.5s infinite;
  box-shadow: 0 0 10px var(--accent);
}

.page-title {
  font-size: 3.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-bottom: 12px;
}

.title-icon {
  font-size: 3rem;
  animation: neon-flicker 3s infinite;
  filter: drop-shadow(0 0 20px var(--accent));
}

.title-text {
  font-family: var(--font-display);
  font-weight: 700;
}

.neon-accent {
  color: var(--accent);
  text-shadow: 
    0 0 10px var(--accent),
    0 0 20px var(--accent),
    0 0 40px var(--accent);
}

.seckill-subtitle {
  color: var(--text-muted);
  font-size: 1.1rem;
  letter-spacing: 0.1em;
}

/* ===== 倒计时面板 ===== */
.countdown-panel {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24px 40px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  margin-bottom: 48px;
  position: relative;
  overflow: hidden;
}

.countdown-panel::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--accent), transparent);
}

.countdown-left {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.countdown-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-display);
  font-size: 0.8rem;
  letter-spacing: 0.1em;
  color: var(--text-muted);
}

.countdown-status.active {
  color: var(--success);
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--text-muted);
}

.countdown-status.active .status-dot {
  background: var(--success);
  box-shadow: 0 0 10px var(--success);
  animation: pulse-glow 1.5s infinite;
}

.countdown-label {
  font-size: 1rem;
  color: var(--text-secondary);
}

.countdown-timer {
  display: flex;
  align-items: center;
  gap: 8px;
}

.time-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.time-value {
  display: flex;
  gap: 4px;
}

.digit {
  width: 48px;
  height: 60px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-display);
  font-size: 2rem;
  font-weight: 700;
  color: var(--accent);
  text-shadow: 0 0 20px var(--accent-glow);
}

.time-unit {
  font-family: var(--font-display);
  font-size: 0.65rem;
  letter-spacing: 0.15em;
  color: var(--text-muted);
}

.time-sep {
  font-family: var(--font-display);
  font-size: 2rem;
  font-weight: 700;
  color: var(--accent);
  margin: 0 4px;
  animation: pulse-glow 1s infinite;
}

/* ===== 秒杀网格 ===== */
.seckill-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 24px;
}

.seckill-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  overflow: hidden;
  position: relative;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  animation: card-in 0.5s ease forwards;
  opacity: 0;
  transform: translateY(20px);
}

@keyframes card-in {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.seckill-card:hover {
  transform: translateY(-8px);
  border-color: var(--accent);
  box-shadow: 0 20px 40px rgba(255, 46, 99, 0.2), var(--glow-accent);
}

.hot-badge {
  position: absolute;
  top: 16px;
  right: 16px;
  z-index: 10;
  padding: 6px 12px;
  background: linear-gradient(135deg, #ff6b35, #ff2e63);
  border-radius: var(--radius-full);
  font-family: var(--font-display);
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  color: #fff;
  animation: pulse-glow 2s infinite;
}

/* ===== 卡片图片区域 ===== */
.card-image {
  height: 180px;
  background: linear-gradient(135deg, var(--bg-elevated), var(--bg-hover));
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.image-placeholder {
  width: 80px;
  height: 80px;
  background: linear-gradient(135deg, var(--accent-dark), var(--accent));
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-display);
  font-size: 2rem;
  font-weight: 700;
  color: #fff;
  box-shadow: var(--glow-accent);
}

.progress-wrapper {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 12px 16px;
  background: linear-gradient(transparent, rgba(0,0,0,0.6));
}

.progress-track {
  height: 6px;
  background: rgba(255,255,255,0.2);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--primary), var(--accent));
  border-radius: var(--radius-full);
  transition: width 0.5s ease;
  position: relative;
}

.progress-fill.danger {
  background: linear-gradient(90deg, #ff6b35, #ff2e63);
  animation: progress-pulse 1s infinite;
}

@keyframes progress-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.progress-label {
  display: block;
  margin-top: 6px;
  font-family: var(--font-display);
  font-size: 0.7rem;
  letter-spacing: 0.1em;
  color: rgba(255,255,255,0.9);
  text-align: right;
}

/* ===== 卡片内容 ===== */
.card-content {
  padding: 20px;
}

.card-title {
  font-family: var(--font-body);
  font-size: 1.1rem;
  font-weight: 600;
  margin-bottom: 16px;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.price-section {
  margin-bottom: 16px;
}

.price-current {
  display: flex;
  align-items: baseline;
  gap: 2px;
  margin-bottom: 4px;
}

.currency {
  font-size: 1rem;
  color: var(--accent);
}

.amount {
  font-family: var(--font-display);
  font-size: 2rem;
  font-weight: 700;
  color: var(--accent);
  text-shadow: 0 0 20px var(--accent-glow);
}

.price-original {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.85rem;
  color: var(--text-muted);
  text-decoration: line-through;
}

.discount-tag {
  padding: 2px 8px;
  background: rgba(255, 46, 99, 0.15);
  border-radius: var(--radius-sm);
  font-family: var(--font-display);
  font-size: 0.65rem;
  font-weight: 600;
  color: var(--accent);
  text-decoration: none;
}

/* ===== 限购区域 ===== */
.limit-section {
  display: flex;
  gap: 16px;
  padding: 12px;
  background: var(--bg-elevated);
  border-radius: var(--radius-md);
  margin-bottom: 16px;
}

.limit-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.limit-icon {
  font-size: 1rem;
}

/* ===== 数量选择 ===== */
.quantity-section {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.qty-label {
  font-size: 0.9rem;
  color: var(--text-secondary);
}

.quantity-control {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px;
  background: var(--bg-elevated);
  border-radius: var(--radius-md);
}

.qty-btn {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: var(--radius-sm);
  background: var(--bg-hover);
  color: var(--text-primary);
  font-size: 1.2rem;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.qty-btn:hover:not(:disabled) {
  background: var(--primary);
  color: var(--bg-void);
}

.qty-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.qty-value {
  min-width: 32px;
  text-align: center;
  font-family: var(--font-display);
  font-size: 1.1rem;
  font-weight: 600;
}

/* ===== 抢购按钮 ===== */
.grab-btn {
  width: 100%;
  padding: 16px 24px;
  background: linear-gradient(135deg, var(--accent-dark), var(--accent));
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  position: relative;
  overflow: hidden;
  transition: all 0.3s;
}

.grab-btn::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
  transform: translateX(-100%);
  transition: transform 0.5s;
}

.grab-btn:hover:not(.disabled)::before {
  transform: translateX(100%);
}

.grab-btn:hover:not(.disabled) {
  transform: scale(1.02);
  box-shadow: 0 10px 30px var(--accent-glow);
}

.grab-btn.disabled {
  background: var(--bg-elevated);
  cursor: not-allowed;
}

.btn-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-family: var(--font-display);
  font-size: 1rem;
  font-weight: 600;
  letter-spacing: 0.1em;
  color: #fff;
}

.grab-btn.disabled .btn-content {
  color: var(--text-muted);
}

.btn-icon {
  font-size: 1.2em;
}

.grabbing-text {
  display: flex;
  align-items: center;
  gap: 8px;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ===== 结果消息 ===== */
.result-toast {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 12px 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 0.9rem;
  animation: toast-in 0.3s ease;
}

@keyframes toast-in {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
}

.result-toast.success {
  background: rgba(0, 245, 160, 0.15);
  color: var(--success);
  border-top: 1px solid rgba(0, 245, 160, 0.3);
}

.result-toast.error {
  background: rgba(255, 46, 99, 0.15);
  color: var(--accent);
  border-top: 1px solid rgba(255, 46, 99, 0.3);
}

.toast-icon {
  font-size: 1.1rem;
}

/* ===== 空状态 ===== */
.empty-state {
  text-align: center;
  padding: 80px 20px;
}

.empty-icon {
  font-size: 4rem;
  opacity: 0.3;
  margin-bottom: 16px;
}

.empty-text {
  font-family: var(--font-display);
  font-size: 1.2rem;
  color: var(--text-muted);
  margin-bottom: 8px;
}

.empty-hint {
  font-size: 0.9rem;
  color: var(--text-muted);
  opacity: 0.7;
}

/* ===== 响应式 ===== */
@media (max-width: 768px) {
  .page-title {
    font-size: 2.5rem;
    flex-direction: column;
    gap: 8px;
  }
  
  .title-icon {
    font-size: 2rem;
  }
  
  .countdown-panel {
    flex-direction: column;
    gap: 24px;
    padding: 24px;
    text-align: center;
  }
  
  .countdown-left {
    align-items: center;
  }
  
  .digit {
    width: 40px;
    height: 50px;
    font-size: 1.5rem;
  }
  
  .seckill-grid {
    grid-template-columns: 1fr;
  }
}
</style>
