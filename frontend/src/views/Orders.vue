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
        <!-- 订单操作按钮 -->
        <div class="order-actions">
          <!-- 待支付：显示支付和取消按钮 -->
          <template v-if="order.order_status === 1">
            <button 
              class="btn btn-primary btn-sm" 
              :disabled="order.paying"
              @click="handlePay(order)"
            >
              {{ order.paying ? '支付中...' : '立即支付' }}
            </button>
            <button 
              class="btn btn-outline btn-sm" 
              :disabled="order.cancelling"
              @click="handleCancel(order)"
            >
              {{ order.cancelling ? '取消中...' : '取消订单' }}
            </button>
          </template>
          <!-- 待发货：仅显示取消按钮 -->
          <template v-else-if="order.order_status === 2">
            <button 
              class="btn btn-outline btn-sm" 
              :disabled="order.cancelling"
              @click="handleCancel(order)"
            >
              {{ order.cancelling ? '取消中...' : '申请退款' }}
            </button>
          </template>
          <!-- 已取消/已完成：无操作 -->
        </div>
        <!-- 操作结果消息 -->
        <div v-if="order.message" class="order-message" :class="order.success ? 'msg-success' : 'msg-error'">
          {{ order.message }}
        </div>
      </div>
    </div>

    <p v-else class="empty-text">暂无订单记录</p>

    <!-- 支付弹窗 -->
    <div v-if="showPayModal" class="modal-overlay" @click.self="showPayModal = false">
      <div class="modal-content">
        <h3>选择支付方式</h3>
        <div class="pay-methods">
          <label class="pay-option" :class="{ active: selectedPayMethod === 1 }">
            <input type="radio" v-model="selectedPayMethod" :value="1" />
            <span class="pay-icon">💳</span>
            <span>支付宝</span>
          </label>
          <label class="pay-option" :class="{ active: selectedPayMethod === 2 }">
            <input type="radio" v-model="selectedPayMethod" :value="2" />
            <span class="pay-icon">💚</span>
            <span>微信支付</span>
          </label>
          <label class="pay-option" :class="{ active: selectedPayMethod === 3 }">
            <input type="radio" v-model="selectedPayMethod" :value="3" />
            <span class="pay-icon">🏦</span>
            <span>银行卡</span>
          </label>
        </div>
        <div class="pay-amount">
          应付金额: <strong>¥{{ currentPayOrder?.total_price }}</strong>
        </div>
        <div class="modal-actions">
          <button class="btn btn-outline" @click="showPayModal = false">取消</button>
          <button class="btn btn-primary" @click="confirmPay">确认支付</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { orderApi } from '../api'

const statusMap: Record<number, string> = {
  1: '待支付', 2: '待发货', 3: '待收货', 4: '已取消', 5: '已完成',
}

interface OrderItem {
  id: string
  goods_id: number
  count: number
  total_price: number
  order_status: number
  create_time: string
  paying?: boolean
  cancelling?: boolean
  message?: string
  success?: boolean
}

const orders = ref<OrderItem[]>([])
const showPayModal = ref(false)
const selectedPayMethod = ref(1)
const currentPayOrder = ref<OrderItem | null>(null)

async function loadOrders() {
  try {
    const res = await orderApi.list()
    orders.value = (res.data.items || []).map((o: any) => ({
      ...o,
      paying: false,
      cancelling: false,
      message: '',
      success: false,
    }))
  } catch { /* ignore */ }
}

function handlePay(order: OrderItem) {
  currentPayOrder.value = order
  selectedPayMethod.value = 1
  showPayModal.value = true
}

async function confirmPay() {
  if (!currentPayOrder.value) return
  const order = currentPayOrder.value
  showPayModal.value = false
  order.paying = true
  order.message = ''
  
  try {
    const res = await orderApi.pay(order.id, { 
      pay_method: selectedPayMethod.value,
      pay_amount: order.total_price 
    })
    order.success = res.data.success !== false
    order.message = res.data.message || '支付成功'
    if (order.success) {
      order.order_status = 2 // 更新为待发货
    }
  } catch (e: any) {
    order.success = false
    order.message = e.response?.data?.detail || '支付失败，请稍后重试'
  } finally {
    order.paying = false
  }
}

async function handleCancel(order: OrderItem) {
  if (!confirm('确定要取消该订单吗？')) return
  
  order.cancelling = true
  order.message = ''
  
  try {
    const res = await orderApi.cancel(order.id, { reason: '用户主动取消' })
    order.success = res.data.success !== false
    order.message = res.data.message || '订单已取消'
    if (order.success) {
      order.order_status = 4 // 更新为已取消
    }
  } catch (e: any) {
    order.success = false
    order.message = e.response?.data?.detail || '取消失败，请稍后重试'
  } finally {
    order.cancelling = false
  }
}

onMounted(() => {
  loadOrders()
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
.status-4 { background: #f3f4f6; color: #6b7280; }
.status-5 { background: #d1fae5; color: #065f46; }

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

/* 订单操作按钮 */
.order-actions {
  display: flex;
  gap: 12px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--border-light);
}

.btn-sm {
  padding: 6px 16px;
  font-size: 0.85rem;
}

/* 操作结果消息 */
.order-message {
  margin-top: 12px;
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  font-size: 0.85rem;
}

.msg-success {
  background: #f0fdf4;
  color: #15803d;
}

.msg-error {
  background: #fef2f2;
  color: #b91c1c;
}

/* 支付弹窗 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  padding: 24px;
  width: 90%;
  max-width: 400px;
  box-shadow: var(--shadow-lg);
}

.modal-content h3 {
  margin-bottom: 20px;
  font-size: 1.2rem;
  font-weight: 600;
  text-align: center;
}

.pay-methods {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 20px;
}

.pay-option {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border: 2px solid var(--border-light);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.2s;
}

.pay-option:hover {
  border-color: var(--primary);
}

.pay-option.active {
  border-color: var(--primary);
  background: rgba(99, 102, 241, 0.05);
}

.pay-option input {
  display: none;
}

.pay-icon {
  font-size: 1.5rem;
}

.pay-amount {
  text-align: center;
  padding: 16px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  margin-bottom: 20px;
}

.pay-amount strong {
  color: var(--danger);
  font-size: 1.3rem;
}

.modal-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
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
  .order-actions {
    flex-wrap: wrap;
  }
}
</style>
