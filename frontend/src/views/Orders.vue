<template>
  <div class="container orders-page">
    <h1 class="page-title">我的订单</h1>

    <div v-if="orders.length > 0" class="orders-list">
      <div v-for="order in orders" :key="order.id" class="order-card card">
        <div class="order-header">
          <span class="order-id">订单号: {{ order.id }}</span>
          <span class="order-status" :class="'status-' + order.order_status">
            {{ statusMap[order.order_status] || '未知' }}
          </span>
        </div>
        <div class="order-body">
          <div class="order-meta">
            <span>商品ID: {{ order.goods_id }}</span>
            <span>数量: {{ order.count }}</span>
            <span>总价: <strong class="price">¥{{ order.total_price }}</strong></span>
          </div>
          <div class="order-time">
            {{ new Date(order.create_time).toLocaleString('zh-CN') }}
          </div>
        </div>
      </div>
    </div>

    <p v-else class="empty-text">暂无订单记录</p>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { orderApi } from '../api'

const statusMap: Record<number, string> = {
  1: '待支付', 2: '待发货', 3: '待收货', 4: '待评价', 5: '已完成', 6: '已取消',
}

const orders = ref<any[]>([])

onMounted(async () => {
  try {
    const res = await orderApi.list()
    orders.value = res.data.items
  } catch { /* ignore */ }
})
</script>

<style scoped>
.orders-page {
  max-width: 800px;
}

.page-title {
  font-size: 1.8rem;
  font-weight: 700;
  margin-bottom: 24px;
}

.orders-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.order-card {
  padding: 20px 24px;
}

.order-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.order-id {
  font-size: 0.85rem;
  color: var(--text-muted);
  font-family: monospace;
}

.order-status {
  padding: 3px 12px;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 500;
}

.status-1 { background: #fef3c7; color: #92400e; }
.status-2 { background: #dbeafe; color: #1e40af; }
.status-3 { background: #e0e7ff; color: #3730a3; }
.status-4 { background: #fce7f3; color: #9d174d; }
.status-5 { background: #d1fae5; color: #065f46; }
.status-6 { background: #f3f4f6; color: #6b7280; }

.order-body {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.order-meta {
  display: flex;
  gap: 20px;
  font-size: 0.9rem;
  color: var(--text-secondary);
}

.price {
  color: var(--danger);
}

.order-time {
  font-size: 0.85rem;
  color: var(--text-muted);
}

.empty-text {
  text-align: center;
  padding: 80px 0;
  color: var(--text-muted);
}

@media (max-width: 640px) {
  .order-body {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
  .order-meta {
    flex-wrap: wrap;
    gap: 12px;
  }
}
</style>
