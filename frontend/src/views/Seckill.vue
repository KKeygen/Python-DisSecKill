<template>
  <div class="container seckill-page">
    <div class="seckill-header">
      <h1 class="page-title">
        <span class="flash-icon">⚡</span> 限时秒杀
      </h1>
      <p class="seckill-subtitle">限量抢购，手慢无！</p>
    </div>

    <!-- 全局倒计时 -->
    <div class="countdown-banner">
      <div class="countdown-label">距离秒杀{{ countdownState }}还剩</div>
      <div class="countdown-timer">
        <div class="time-block">
          <span class="time-value">{{ timeDisplay.hours }}</span>
          <span class="time-unit">时</span>
        </div>
        <span class="time-sep">:</span>
        <div class="time-block">
          <span class="time-value">{{ timeDisplay.minutes }}</span>
          <span class="time-unit">分</span>
        </div>
        <span class="time-sep">:</span>
        <div class="time-block">
          <span class="time-value">{{ timeDisplay.seconds }}</span>
          <span class="time-unit">秒</span>
        </div>
      </div>
    </div>

    <!-- 秒杀商品列表 -->
    <div class="seckill-grid">
      <div v-for="item in seckillGoods" :key="item.id" class="seckill-card">
        <div class="seckill-card-img">
          <div class="img-placeholder">📦</div>
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: item.progressPercent + '%' }"></div>
          </div>
          <span class="progress-text">已抢{{ item.progressPercent }}%</span>
        </div>
        <div class="seckill-card-info">
          <h3>{{ item.name }}</h3>
          <div class="price-row">
            <span class="sk-price">¥{{ item.seckill_price }}</span>
            <span class="orig-price">¥{{ item.price }}</span>
          </div>
          <button
            class="btn btn-danger btn-block"
            :disabled="!isActive || item.grabbed"
            @click="handleGrab(item)"
          >
            {{ item.grabbed ? '已抢到' : item.grabbing ? '抢购中...' : isActive ? '立即抢购' : '未开始' }}
          </button>
        </div>

        <div v-if="item.message" class="seckill-msg" :class="item.success ? 'msg-success' : 'msg-fail'">
          {{ item.message }}
        </div>
      </div>
    </div>

    <p v-if="seckillGoods.length === 0" class="empty-text">暂无秒杀活动</p>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { goodsApi, inventoryApi } from '../api'
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
      }))
    } else {
      // 模拟数据
      seckillGoods.value = [
        { id: 1, name: '小米14 Ultra 手机', price: 5999, seckill_price: 4999, seckill_start: '', seckill_end: '', progressPercent: 75, grabbing: false, grabbed: false, success: false, message: '' },
        { id: 2, name: '索尼 WH-1000XM5 耳机', price: 2999, seckill_price: 1999, seckill_start: '', seckill_end: '', progressPercent: 42, grabbing: false, grabbed: false, success: false, message: '' },
        { id: 3, name: 'Apple iPad Air 2025', price: 4799, seckill_price: 3899, seckill_start: '', seckill_end: '', progressPercent: 88, grabbing: false, grabbed: false, success: false, message: '' },
        { id: 4, name: '戴森 V15 Detect 吸尘器', price: 4490, seckill_price: 3290, seckill_start: '', seckill_end: '', progressPercent: 31, grabbing: false, grabbed: false, success: false, message: '' },
      ]
    }
  } catch {
    // 出错也用模拟数据
    seckillGoods.value = [
      { id: 1, name: '秒杀商品A', price: 999, seckill_price: 499, seckill_start: '', seckill_end: '', progressPercent: 65, grabbing: false, grabbed: false, success: false, message: '' },
      { id: 2, name: '秒杀商品B', price: 1999, seckill_price: 999, seckill_start: '', seckill_end: '', progressPercent: 33, grabbing: false, grabbed: false, success: false, message: '' },
    ]
  }
}

async function handleGrab(item: SeckillItem) {
  if (!auth.isLoggedIn || !auth.user) {
    item.message = '请先登录后再抢购'
    item.success = false
    return
  }
  item.grabbing = true
  item.message = ''
  try {
    const res = await inventoryApi.seckill({ goods_id: item.id, user_id: auth.user.id })
    item.success = res.data.success
    item.message = res.data.message
    if (res.data.success) {
      item.grabbed = true
      item.progressPercent = Math.min(100, item.progressPercent + 1)
    }
  } catch (e: any) {
    item.success = false
    item.message = e.response?.data?.detail || '请求失败，请稍后重试'
  } finally {
    item.grabbing = false
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
.seckill-header {
  text-align: center;
  padding: 16px 0 8px;
}

.page-title {
  font-size: 2rem;
  font-weight: 700;
}

.flash-icon {
  animation: flash 1.2s infinite;
}

@keyframes flash {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.seckill-subtitle {
  color: var(--text-secondary);
  margin-top: 8px;
}

/* ===== 倒计时 ===== */
.countdown-banner {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 24px;
  margin: 24px 0 32px;
  padding: 20px;
  background: linear-gradient(135deg, #1e293b, #334155);
  border-radius: var(--radius-lg);
  color: #fff;
}

.countdown-label {
  font-size: 1rem;
  opacity: 0.85;
}

.countdown-timer {
  display: flex;
  align-items: center;
  gap: 4px;
}

.time-block {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.time-value {
  background: rgba(255, 255, 255, 0.15);
  padding: 8px 14px;
  border-radius: var(--radius-sm);
  font-size: 1.6rem;
  font-weight: 700;
  font-family: 'Courier New', monospace;
  min-width: 56px;
  text-align: center;
}

.time-unit {
  font-size: 0.7rem;
  opacity: 0.6;
  margin-top: 4px;
}

.time-sep {
  font-size: 1.4rem;
  font-weight: 700;
  opacity: 0.5;
  padding: 0 2px;
  align-self: flex-start;
  margin-top: 8px;
}

/* ===== 秒杀卡片 ===== */
.seckill-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 20px;
}

.seckill-card {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-light);
  position: relative;
  transition: all 0.3s ease;
}

.seckill-card:hover {
  box-shadow: var(--shadow-lg);
  transform: translateY(-4px);
}

.seckill-card-img {
  height: 180px;
  background: linear-gradient(135deg, #fff1f2, #fef3c7);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.img-placeholder {
  font-size: 4rem;
  opacity: 0.3;
}

.progress-bar {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 6px;
  background: rgba(0, 0, 0, 0.1);
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #ef4444, #ec4899);
  border-radius: 0 3px 3px 0;
  transition: width 0.5s ease;
}

.progress-text {
  position: absolute;
  bottom: 10px;
  right: 12px;
  font-size: 0.75rem;
  color: #ef4444;
  font-weight: 600;
  background: rgba(255, 255, 255, 0.9);
  padding: 2px 8px;
  border-radius: 10px;
}

.seckill-card-info {
  padding: 16px;
}

.seckill-card-info h3 {
  font-size: 1rem;
  font-weight: 600;
  margin-bottom: 10px;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.price-row {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 12px;
}

.sk-price {
  font-size: 1.3rem;
  font-weight: 700;
  color: var(--danger);
}

.orig-price {
  font-size: 0.85rem;
  color: var(--text-muted);
  text-decoration: line-through;
}

.seckill-msg {
  padding: 8px 16px;
  font-size: 0.85rem;
  text-align: center;
}

.msg-success {
  background: #f0fdf4;
  color: #15803d;
}

.msg-fail {
  background: #fef2f2;
  color: #b91c1c;
}

.empty-text {
  text-align: center;
  padding: 80px 0;
  color: var(--text-muted);
}

@media (max-width: 640px) {
  .countdown-banner {
    flex-direction: column;
    gap: 12px;
  }
}
</style>
