<template>
  <div class="container detail-page">
    <div v-if="goods" class="detail-layout">
      <!-- 商品图片 -->
      <div class="detail-image">
        <div class="img-placeholder-lg">📦</div>
        <span v-if="goods.is_seckill" class="seckill-badge-lg">⚡ 秒杀中</span>
      </div>

      <!-- 商品信息 -->
      <div class="detail-info">
        <h1>{{ goods.name }}</h1>
        <p class="desc">{{ goods.desc || '暂无描述' }}</p>

        <div class="price-block">
          <span class="current-price">¥{{ goods.is_seckill ? goods.seckill_price : goods.price }}</span>
          <span v-if="goods.is_seckill" class="original-price">¥{{ goods.price }}</span>
        </div>

        <div class="meta-list">
          <div class="meta-item"><span class="meta-label">单位</span><span>{{ goods.unit }}</span></div>
          <div class="meta-item"><span class="meta-label">状态</span><span>{{ goods.status === 1 ? '在售' : '下架' }}</span></div>
        </div>

        <!-- 秒杀商品：显示限购信息和数量选择 -->
        <div v-if="goods.is_seckill" class="seckill-options">
          <div class="limit-info-detail">
            <span>限购 {{ limitPerUser }} 件</span>
            <span v-if="auth.isLoggedIn">已购 {{ userPurchased }} 件</span>
          </div>
          <div v-if="canBuyCount > 0" class="quantity-row">
            <span class="qty-label">购买数量：</span>
            <div class="quantity-selector">
              <button class="qty-btn" @click="seckillCount = Math.max(1, seckillCount - 1)" :disabled="seckillCount <= 1">−</button>
              <span class="qty-value">{{ seckillCount }}</span>
              <button class="qty-btn" @click="seckillCount = Math.min(canBuyCount, seckillCount + 1)" :disabled="seckillCount >= canBuyCount">+</button>
            </div>
          </div>
        </div>

        <div class="action-row">
          <button v-if="goods.is_seckill" class="btn btn-danger btn-lg" @click="handleSeckill" :disabled="seckilling || canBuyCount <= 0">
            {{ canBuyCount <= 0 ? '已达限购' : seckilling ? '抢购中...' : '立即秒杀' }}
          </button>
          <button v-else class="btn btn-primary btn-lg" @click="handleAddToCart">加入购物车</button>
        </div>

        <div v-if="seckillMsg" class="alert" :class="seckillSuccess ? 'alert-success' : 'alert-error'" style="margin-top:16px">
          {{ seckillMsg }}
        </div>
      </div>
    </div>

    <p v-else class="empty-text">商品加载中...</p>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { goodsApi, inventoryApi } from '../api'
import { useAuthStore } from '../stores/auth'
import { useCartStore } from '../stores/cart'

const route = useRoute()
const auth = useAuthStore()

const goods = ref<any>(null)
const cart = useCartStore()
const seckilling = ref(false)
const seckillMsg = ref('')
const seckillSuccess = ref(false)

// 秒杀限购相关状态
const limitPerUser = ref(2)
const userPurchased = ref(0)
const seckillCount = ref(1)

const canBuyCount = computed(() => Math.max(0, limitPerUser.value - userPurchased.value))

onMounted(async () => {
  const id = Number(route.params.id)
  try {
    const res = await goodsApi.detail(id)
    goods.value = res.data
    
    // 如果是秒杀商品且用户已登录，查询用户购买信息
    if (goods.value?.is_seckill && auth.isLoggedIn && auth.user) {
      try {
        const info = await inventoryApi.getUserSeckillInfo(id, auth.user.id)
        if (info.data) {
          userPurchased.value = info.data.purchased_count || 0
          limitPerUser.value = info.data.limit_per_user || 2
        }
      } catch { /* ignore */ }
    }
  } catch { /* ignore */ }
})

function handleAddToCart() {
  if (goods.value) {
    cart.addItem({ id: goods.value.id, name: goods.value.name, price: goods.value.price })
    seckillMsg.value = '已添加到购物车'
    seckillSuccess.value = true
  }
}

async function handleSeckill() {
  if (!auth.isLoggedIn || !auth.user) {
    seckillMsg.value = '请先登录'
    seckillSuccess.value = false
    return
  }
  if (canBuyCount.value <= 0) {
    seckillMsg.value = '您已达到限购数量'
    seckillSuccess.value = false
    return
  }
  if (seckillCount.value > canBuyCount.value) {
    seckillMsg.value = `您最多还可购买 ${canBuyCount.value} 件`
    seckillSuccess.value = false
    return
  }
  seckilling.value = true
  seckillMsg.value = ''
  try {
    const res = await inventoryApi.seckill({ 
      goods_id: goods.value.id, 
      user_id: auth.user.id,
      count: seckillCount.value
    })
    seckillSuccess.value = res.data.success
    seckillMsg.value = res.data.message
    if (res.data.success) {
      userPurchased.value += seckillCount.value
    }
  } catch (e: any) {
    seckillSuccess.value = false
    seckillMsg.value = e.response?.data?.detail || '秒杀请求失败'
  } finally {
    seckilling.value = false
  }
}
</script>

<style scoped>
.detail-layout {
  display: flex;
  gap: 48px;
  padding: 16px 0;
}

.detail-image {
  flex: 0 0 420px;
  height: 400px;
  border-radius: var(--radius-lg);
  background: linear-gradient(135deg, #f0f4ff, #faf5ff);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}

.img-placeholder-lg {
  font-size: 6rem;
  opacity: 0.3;
}

.seckill-badge-lg {
  position: absolute;
  top: 16px;
  left: 16px;
  background: linear-gradient(135deg, #ef4444, #ec4899);
  color: #fff;
  padding: 6px 16px;
  border-radius: var(--radius-md);
  font-weight: 600;
  font-size: 0.9rem;
}

.detail-info h1 {
  font-size: 1.8rem;
  font-weight: 700;
  margin-bottom: 12px;
}

.desc {
  color: var(--text-secondary);
  margin-bottom: 24px;
  line-height: 1.7;
}

.price-block {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 24px;
}

.current-price {
  font-size: 2rem;
  font-weight: 700;
  color: var(--danger);
}

.original-price {
  font-size: 1rem;
  color: var(--text-muted);
  text-decoration: line-through;
}

.meta-list {
  display: flex;
  gap: 32px;
  margin-bottom: 24px;
}

.meta-item {
  display: flex;
  gap: 8px;
  font-size: 0.9rem;
}

.meta-label {
  color: var(--text-muted);
}

/* 秒杀选项区域 */
.seckill-options {
  margin-bottom: 24px;
  padding: 16px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
}

.limit-info-detail {
  display: flex;
  justify-content: space-between;
  font-size: 0.9rem;
  color: var(--text-secondary);
  margin-bottom: 12px;
}

.quantity-row {
  display: flex;
  align-items: center;
  gap: 16px;
}

.qty-label {
  font-size: 0.9rem;
  color: var(--text-secondary);
}

.quantity-selector {
  display: flex;
  align-items: center;
  gap: 12px;
}

.qty-btn {
  width: 32px;
  height: 32px;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  background: var(--bg-card);
  cursor: pointer;
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text-primary);
  transition: all 0.2s;
}

.qty-btn:hover:not(:disabled) {
  border-color: var(--primary);
  color: var(--primary);
}

.qty-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.qty-value {
  font-size: 1.2rem;
  font-weight: 600;
  min-width: 32px;
  text-align: center;
}

.action-row {
  display: flex;
  gap: 16px;
}

.empty-text {
  text-align: center;
  padding: 80px 0;
  color: var(--text-muted);
}

@media (max-width: 768px) {
  .detail-layout {
    flex-direction: column;
    gap: 24px;
  }
  .detail-image {
    flex: none;
    width: 100%;
    height: 280px;
  }
}
</style>
