<template>
  <div class="orders-admin">
    <!-- 统计区 -->
    <div class="stats-row">
      <div class="stat-item">
        <span class="stat-num">{{ orderStats.total }}</span>
        <span class="stat-label">总订单</span>
      </div>
      <div class="stat-item pending">
        <span class="stat-num">{{ orderStats.pending }}</span>
        <span class="stat-label">待支付</span>
      </div>
      <div class="stat-item paid">
        <span class="stat-num">{{ orderStats.paid }}</span>
        <span class="stat-label">已支付</span>
      </div>
      <div class="stat-item shipped">
        <span class="stat-num">{{ orderStats.shipped }}</span>
        <span class="stat-label">已发货</span>
      </div>
      <div class="stat-item completed">
        <span class="stat-num">{{ orderStats.completed }}</span>
        <span class="stat-label">已完成</span>
      </div>
      <div class="stat-item cancelled">
        <span class="stat-num">{{ orderStats.cancelled }}</span>
        <span class="stat-label">已取消</span>
      </div>
    </div>

    <!-- 筛选工具栏 -->
    <div class="filter-bar">
      <div class="filter-group">
        <div class="search-box">
          <span class="search-icon">🔍</span>
          <input 
            v-model="searchQuery" 
            type="text" 
            placeholder="订单号/用户ID..." 
            class="search-input"
          />
        </div>
        
        <select v-model="filterStatus" class="filter-select">
          <option value="">全部状态</option>
          <option value="1">待支付</option>
          <option value="2">已支付</option>
          <option value="3">已发货</option>
          <option value="4">已取消</option>
          <option value="5">已完成</option>
        </select>

        <select v-model="filterType" class="filter-select">
          <option value="">全部类型</option>
          <option value="normal">普通订单</option>
          <option value="seckill">秒杀订单</option>
        </select>

        <input 
          v-model="filterDateStart" 
          type="date" 
          class="filter-input"
        />
        <span class="filter-sep">至</span>
        <input 
          v-model="filterDateEnd" 
          type="date" 
          class="filter-input"
        />
      </div>

      <div class="filter-actions">
        <button class="btn btn-ghost" @click="resetFilters">重置</button>
        <button class="btn btn-primary" @click="exportOrders">导出</button>
      </div>
    </div>

    <!-- 订单列表 -->
    <div class="orders-table">
      <div class="table-header">
        <span class="col-check"><input type="checkbox" @change="toggleSelectAll" /></span>
        <span class="col-order">订单信息</span>
        <span class="col-user">用户</span>
        <span class="col-amount">金额</span>
        <span class="col-status">状态</span>
        <span class="col-time">创建时间</span>
        <span class="col-actions">操作</span>
      </div>

      <div class="table-body">
        <div 
          v-for="order in filteredOrders" 
          :key="order.id" 
          class="table-row"
          :class="{ selected: selectedOrders.includes(order.id) }"
        >
          <span class="col-check">
            <input 
              type="checkbox" 
              :checked="selectedOrders.includes(order.id)"
              @change="toggleSelect(order.id)"
            />
          </span>
          
          <div class="col-order">
            <div class="order-id">
              <span class="id-text">{{ order.id }}</span>
              <button class="copy-btn" @click="copyOrderId(order.id)" title="复制">📋</button>
            </div>
            <div class="order-goods">
              <span v-for="(item, idx) in order.items.slice(0, 2)" :key="idx" class="goods-name">
                {{ item.name }} × {{ item.count }}
              </span>
              <span v-if="order.items.length > 2" class="more-goods">
                +{{ order.items.length - 2 }}件
              </span>
            </div>
            <span v-if="order.is_seckill" class="seckill-tag">⚡秒杀</span>
          </div>

          <div class="col-user">
            <span class="user-id">ID: {{ order.user_id }}</span>
          </div>

          <div class="col-amount">
            <span class="amount-value">¥{{ order.total_amount.toFixed(2) }}</span>
            <span v-if="order.pay_method" class="pay-method">{{ getPayMethodText(order.pay_method) }}</span>
          </div>

          <div class="col-status">
            <span class="status-badge" :class="getStatusClass(order.status)">
              {{ getStatusText(order.status) }}
            </span>
          </div>

          <div class="col-time">
            <span class="time-main">{{ formatDate(order.created_at) }}</span>
            <span class="time-sub">{{ formatTime(order.created_at) }}</span>
          </div>

          <div class="col-actions">
            <button class="action-btn" @click="viewOrder(order)">详情</button>
            <button 
              v-if="order.status === 2" 
              class="action-btn ship" 
              @click="shipOrder(order)"
            >发货</button>
            <button 
              v-if="order.status === 1" 
              class="action-btn cancel" 
              @click="cancelOrder(order)"
            >取消</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 分页 -->
    <div class="pagination">
      <span class="page-info">
        共 {{ orders.length }} 条，已选 {{ selectedOrders.length }} 条
      </span>
      <div class="page-controls">
        <button class="page-btn" :disabled="currentPage === 1" @click="currentPage--">←</button>
        <span class="page-numbers">
          <button 
            v-for="page in visiblePages" 
            :key="page"
            class="page-num" 
            :class="{ active: currentPage === page }"
            @click="currentPage = page"
          >{{ page }}</button>
        </span>
        <button class="page-btn" :disabled="currentPage === totalPages" @click="currentPage++">→</button>
      </div>
      <select v-model="pageSize" class="page-size">
        <option :value="10">10条/页</option>
        <option :value="20">20条/页</option>
        <option :value="50">50条/页</option>
      </select>
    </div>

    <!-- 批量操作栏 -->
    <div v-if="selectedOrders.length > 0" class="bulk-actions">
      <span class="bulk-info">已选择 {{ selectedOrders.length }} 个订单</span>
      <button class="bulk-btn" @click="bulkShip">批量发货</button>
      <button class="bulk-btn cancel" @click="bulkCancel">批量取消</button>
      <button class="bulk-btn" @click="selectedOrders = []">取消选择</button>
    </div>

    <!-- 订单详情弹窗 -->
    <div v-if="showDetail" class="modal-overlay" @click.self="showDetail = false">
      <div class="modal-content detail-modal">
        <div class="modal-header">
          <h3>订单详情</h3>
          <button class="close-btn" @click="showDetail = false">×</button>
        </div>

        <div v-if="currentOrder" class="detail-content">
          <!-- 订单基本信息 -->
          <div class="detail-section">
            <h4>基本信息</h4>
            <div class="info-grid">
              <div class="info-item">
                <span class="info-label">订单号</span>
                <span class="info-value mono">{{ currentOrder.id }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">订单状态</span>
                <span class="status-badge" :class="getStatusClass(currentOrder.status)">
                  {{ getStatusText(currentOrder.status) }}
                </span>
              </div>
              <div class="info-item">
                <span class="info-label">订单类型</span>
                <span class="info-value">{{ currentOrder.is_seckill ? '秒杀订单' : '普通订单' }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">创建时间</span>
                <span class="info-value">{{ currentOrder.created_at }}</span>
              </div>
            </div>
          </div>

          <!-- 用户信息 -->
          <div class="detail-section">
            <h4>用户信息</h4>
            <div class="info-grid">
              <div class="info-item">
                <span class="info-label">用户ID</span>
                <span class="info-value mono">{{ currentOrder.user_id }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">收货地址</span>
                <span class="info-value">{{ currentOrder.address || '未填写' }}</span>
              </div>
            </div>
          </div>

          <!-- 商品列表 -->
          <div class="detail-section">
            <h4>商品明细</h4>
            <div class="goods-list">
              <div v-for="(item, idx) in currentOrder.items" :key="idx" class="goods-item">
                <div class="goods-avatar">{{ item.name.charAt(0) }}</div>
                <div class="goods-info">
                  <span class="goods-name">{{ item.name }}</span>
                  <span class="goods-spec">{{ item.spec || '标准规格' }}</span>
                </div>
                <span class="goods-price">¥{{ item.price }}</span>
                <span class="goods-count">× {{ item.count }}</span>
                <span class="goods-subtotal">¥{{ (item.price * item.count).toFixed(2) }}</span>
              </div>
            </div>
          </div>

          <!-- 金额信息 -->
          <div class="detail-section">
            <h4>金额信息</h4>
            <div class="amount-summary">
              <div class="amount-row">
                <span>商品总额</span>
                <span>¥{{ currentOrder.goods_amount?.toFixed(2) || currentOrder.total_amount.toFixed(2) }}</span>
              </div>
              <div class="amount-row">
                <span>运费</span>
                <span>¥{{ currentOrder.shipping_fee?.toFixed(2) || '0.00' }}</span>
              </div>
              <div class="amount-row">
                <span>优惠</span>
                <span class="discount">-¥{{ currentOrder.discount?.toFixed(2) || '0.00' }}</span>
              </div>
              <div class="amount-row total">
                <span>实付金额</span>
                <span>¥{{ currentOrder.total_amount.toFixed(2) }}</span>
              </div>
            </div>
          </div>

          <!-- 支付信息 -->
          <div v-if="currentOrder.status >= 2" class="detail-section">
            <h4>支付信息</h4>
            <div class="info-grid">
              <div class="info-item">
                <span class="info-label">支付方式</span>
                <span class="info-value">{{ getPayMethodText(currentOrder.pay_method) }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">支付时间</span>
                <span class="info-value">{{ currentOrder.paid_at || '-' }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">交易流水</span>
                <span class="info-value mono">{{ currentOrder.transaction_id || '-' }}</span>
              </div>
            </div>
          </div>

          <!-- 物流信息 -->
          <div v-if="currentOrder.status >= 3" class="detail-section">
            <h4>物流信息</h4>
            <div class="info-grid">
              <div class="info-item">
                <span class="info-label">快递公司</span>
                <span class="info-value">{{ currentOrder.express_company || '-' }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">快递单号</span>
                <span class="info-value mono">{{ currentOrder.express_no || '-' }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">发货时间</span>
                <span class="info-value">{{ currentOrder.shipped_at || '-' }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="modal-actions">
          <button class="btn btn-ghost" @click="showDetail = false">关闭</button>
          <button 
            v-if="currentOrder?.status === 2" 
            class="btn btn-primary" 
            @click="shipOrder(currentOrder)"
          >发货</button>
        </div>
      </div>
    </div>

    <!-- 发货弹窗 -->
    <div v-if="showShipModal" class="modal-overlay" @click.self="showShipModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h3>订单发货</h3>
          <button class="close-btn" @click="showShipModal = false">×</button>
        </div>

        <div class="modal-form">
          <div class="form-group">
            <label class="form-label">快递公司</label>
            <select v-model="shipForm.company" class="form-input">
              <option value="">请选择</option>
              <option value="sf">顺丰速运</option>
              <option value="jd">京东物流</option>
              <option value="sto">申通快递</option>
              <option value="yto">圆通速递</option>
              <option value="zto">中通快递</option>
              <option value="yunda">韵达快递</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">快递单号</label>
            <input v-model="shipForm.trackingNo" type="text" class="form-input" placeholder="输入快递单号" />
          </div>
        </div>

        <div class="modal-actions">
          <button class="btn btn-ghost" @click="showShipModal = false">取消</button>
          <button class="btn btn-primary" @click="confirmShip">确认发货</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { orderApi } from '../../api'

interface OrderItem {
  name: string
  price: number
  count: number
  spec?: string
}

interface Order {
  id: string
  user_id: number
  status: number
  total_amount: number
  goods_amount?: number
  shipping_fee?: number
  discount?: number
  is_seckill: boolean
  pay_method?: string
  created_at: string
  paid_at?: string
  shipped_at?: string
  transaction_id?: string
  express_company?: string
  express_no?: string
  address?: string
  items: OrderItem[]
}

const orders = ref<Order[]>([])
const selectedOrders = ref<string[]>([])
const searchQuery = ref('')
const filterStatus = ref('')
const filterType = ref('')
const filterDateStart = ref('')
const filterDateEnd = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const showDetail = ref(false)
const showShipModal = ref(false)
const currentOrder = ref<Order | null>(null)
const shipForm = ref({ company: '', trackingNo: '' })

const orderStats = computed(() => {
  const stats = { total: 0, pending: 0, paid: 0, shipped: 0, completed: 0, cancelled: 0 }
  orders.value.forEach(o => {
    stats.total++
    if (o.status === 1) stats.pending++
    else if (o.status === 2) stats.paid++
    else if (o.status === 3) stats.shipped++
    else if (o.status === 5) stats.completed++
    else if (o.status === 4) stats.cancelled++
  })
  return stats
})

const filteredOrders = computed(() => {
  let result = orders.value

  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    result = result.filter(o => 
      o.id.toLowerCase().includes(q) || String(o.user_id).includes(q)
    )
  }

  if (filterStatus.value) {
    result = result.filter(o => o.status === Number(filterStatus.value))
  }

  if (filterType.value === 'seckill') {
    result = result.filter(o => o.is_seckill)
  } else if (filterType.value === 'normal') {
    result = result.filter(o => !o.is_seckill)
  }

  return result
})

const totalPages = computed(() => Math.ceil(filteredOrders.value.length / pageSize.value))

const visiblePages = computed(() => {
  const pages = []
  const start = Math.max(1, currentPage.value - 2)
  const end = Math.min(totalPages.value, start + 4)
  for (let i = start; i <= end; i++) pages.push(i)
  return pages
})

function getStatusText(status: number) {
  const map: Record<number, string> = {
    1: '待支付',
    2: '已支付',
    3: '已发货',
    4: '已取消',
    5: '已完成',
  }
  return map[status] || '未知'
}

function getStatusClass(status: number) {
  const map: Record<number, string> = {
    1: 'pending',
    2: 'paid',
    3: 'shipped',
    4: 'cancelled',
    5: 'completed',
  }
  return map[status] || ''
}

function getPayMethodText(method?: string) {
  const map: Record<string, string> = {
    alipay: '支付宝',
    wechat: '微信支付',
    bank: '银行卡',
  }
  return method ? map[method] || method : '-'
}

function formatDate(datetime: string) {
  return datetime.split(' ')[0]
}

function formatTime(datetime: string) {
  return datetime.split(' ')[1] || ''
}

function toggleSelectAll(e: Event) {
  const checked = (e.target as HTMLInputElement).checked
  if (checked) {
    selectedOrders.value = filteredOrders.value.map(o => o.id)
  } else {
    selectedOrders.value = []
  }
}

function toggleSelect(id: string) {
  const idx = selectedOrders.value.indexOf(id)
  if (idx >= 0) {
    selectedOrders.value.splice(idx, 1)
  } else {
    selectedOrders.value.push(id)
  }
}

function copyOrderId(id: string) {
  navigator.clipboard.writeText(id).catch(() => {
    // Fallback for older browsers or insecure contexts
    const textarea = document.createElement('textarea')
    textarea.value = id
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand('copy')
    document.body.removeChild(textarea)
  })
}

function viewOrder(order: Order) {
  currentOrder.value = order
  showDetail.value = true
}

function shipOrder(order: Order) {
  currentOrder.value = order
  shipForm.value = { company: '', trackingNo: '' }
  showShipModal.value = true
}

async function confirmShip() {
  if (!currentOrder.value) return
  if (!shipForm.value.company || !shipForm.value.trackingNo.trim()) {
    alert('请填写快递公司和快递单号')
    return
  }
  try {
    await orderApi.ship(currentOrder.value.id, {
      express_company: shipForm.value.company,
      express_no: shipForm.value.trackingNo,
    })
    currentOrder.value.status = 3
    currentOrder.value.express_company = shipForm.value.company
    currentOrder.value.express_no = shipForm.value.trackingNo
    currentOrder.value.shipped_at = new Date().toISOString().slice(0, 19).replace('T', ' ')
    showShipModal.value = false
    showDetail.value = false
  } catch (err) {
    console.error('Failed to ship order:', err)
    alert('发货失败，请重试')
  }
}

async function cancelOrder(order: Order) {
  if (confirm('确定取消此订单吗？')) {
    try {
      await orderApi.cancel(order.id, { reason: '管理员取消' })
      order.status = 4
    } catch (err) {
      console.error('Failed to cancel order:', err)
      alert('取消失败，请重试')
    }
  }
}

function bulkShip() {
  const paidOrders = orders.value.filter(o => 
    selectedOrders.value.includes(o.id) && o.status === 2
  )
  if (paidOrders.length === 0) {
    alert('所选订单中没有可发货的订单')
    return
  }
  // 简化处理，实际应弹窗输入快递信息
  paidOrders.forEach(o => {
    o.status = 3
    o.shipped_at = new Date().toISOString().slice(0, 19).replace('T', ' ')
  })
  selectedOrders.value = []
}

function bulkCancel() {
  const pendingOrders = orders.value.filter(o => 
    selectedOrders.value.includes(o.id) && o.status === 1
  )
  if (pendingOrders.length === 0) {
    alert('所选订单中没有可取消的订单')
    return
  }
  if (confirm(`确定取消 ${pendingOrders.length} 个订单吗？`)) {
    pendingOrders.forEach(o => o.status = 4)
    selectedOrders.value = []
  }
}

function resetFilters() {
  searchQuery.value = ''
  filterStatus.value = ''
  filterType.value = ''
  filterDateStart.value = ''
  filterDateEnd.value = ''
}

function exportOrders() {
  alert('导出功能开发中...')
}

async function loadOrders() {
  try {
    const params: any = {
      page: currentPage.value,
      size: pageSize.value,
    }
    if (filterStatus.value) {
      params.order_status = Number(filterStatus.value)
    }
    const res = await orderApi.list(params)
    const data = res.data.items || res.data || []
    // Transform backend data to frontend format
    orders.value = data.map((o: any) => ({
      id: o.order_id || o.id,
      user_id: o.user_id,
      status: o.order_status || o.status,
      total_amount: o.total_price || o.total_amount || 0,
      goods_amount: o.total_price || o.goods_amount,
      is_seckill: o.is_seckill || false,
      pay_method: o.pay_method,
      created_at: o.created_at || o.create_time,
      paid_at: o.paid_at,
      shipped_at: o.shipped_at,
      transaction_id: o.transaction_id,
      express_company: o.express_company,
      express_no: o.express_no,
      address: o.address,
      items: o.items || [{ name: o.goods_name || '商品', price: o.total_price, count: o.count || 1 }],
    }))
  } catch (err) {
    console.error('Failed to load orders:', err)
    // Keep mock data as fallback for demo
  }
}

watch([currentPage, pageSize, filterStatus], () => {
  loadOrders()
})

onMounted(() => {
  loadOrders()
})
</script>

<style scoped>
.orders-admin {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* ===== 统计区 ===== */
.stats-row {
  display: flex;
  gap: 16px;
  padding: 20px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
}

.stat-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 12px;
  border-radius: var(--radius-md);
}

.stat-num {
  font-family: var(--font-display);
  font-size: 1.8rem;
  font-weight: 700;
}

.stat-label {
  font-size: 0.8rem;
  color: var(--text-muted);
}

.stat-item.pending .stat-num { color: var(--warning); }
.stat-item.paid .stat-num { color: var(--info); }
.stat-item.shipped .stat-num { color: var(--primary); }
.stat-item.completed .stat-num { color: var(--success); }
.stat-item.cancelled .stat-num { color: var(--text-muted); }

/* ===== 筛选工具栏 ===== */
.filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.search-box {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  width: 200px;
}

.search-icon {
  font-size: 0.9rem;
  opacity: 0.5;
}

.search-input {
  flex: 1;
  background: transparent;
  border: none;
  color: var(--text-primary);
  font-size: 0.85rem;
  outline: none;
}

.filter-select,
.filter-input {
  padding: 10px 14px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-size: 0.85rem;
}

.filter-sep {
  color: var(--text-muted);
  font-size: 0.85rem;
}

.filter-actions {
  display: flex;
  gap: 10px;
}

/* ===== 表格 ===== */
.orders-table {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.table-header,
.table-row {
  display: grid;
  grid-template-columns: 40px 2.5fr 1fr 1fr 1fr 1.2fr 1.2fr;
  gap: 12px;
  padding: 14px 20px;
  align-items: center;
}

.table-header {
  background: var(--bg-elevated);
  font-family: var(--font-display);
  font-size: 0.7rem;
  letter-spacing: 0.08em;
  color: var(--text-muted);
  text-transform: uppercase;
  border-bottom: 1px solid var(--border-color);
}

.table-row {
  border-bottom: 1px solid var(--border-light);
  transition: background var(--transition);
}

.table-row:hover {
  background: var(--bg-hover);
}

.table-row.selected {
  background: rgba(0, 245, 212, 0.05);
}

.table-row:last-child {
  border-bottom: none;
}

/* 订单列 */
.col-order {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.order-id {
  display: flex;
  align-items: center;
  gap: 6px;
}

.id-text {
  font-family: var(--font-mono);
  font-size: 0.8rem;
}

.copy-btn {
  background: none;
  border: none;
  font-size: 0.7rem;
  cursor: pointer;
  opacity: 0.4;
  transition: opacity var(--transition);
}

.copy-btn:hover {
  opacity: 1;
}

.order-goods {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.goods-name {
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.more-goods {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.seckill-tag {
  display: inline-block;
  padding: 2px 8px;
  background: rgba(255, 46, 99, 0.15);
  color: var(--accent);
  border-radius: var(--radius-sm);
  font-size: 0.7rem;
  width: fit-content;
}

/* 用户列 */
.col-user {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.user-id {
  font-size: 0.8rem;
  font-family: var(--font-mono);
}

/* 金额列 */
.col-amount {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.amount-value {
  font-family: var(--font-display);
  font-weight: 600;
}

.pay-method {
  font-size: 0.75rem;
  color: var(--text-muted);
}

/* 状态列 */
.status-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: var(--radius-full);
  font-size: 0.75rem;
  font-weight: 500;
}

.status-badge.pending {
  background: rgba(255, 181, 71, 0.15);
  color: var(--warning);
}

.status-badge.paid {
  background: rgba(0, 183, 235, 0.15);
  color: var(--info);
}

.status-badge.shipped {
  background: rgba(0, 245, 212, 0.15);
  color: var(--primary);
}

.status-badge.completed {
  background: rgba(0, 245, 160, 0.15);
  color: var(--success);
}

.status-badge.cancelled {
  background: var(--bg-elevated);
  color: var(--text-muted);
}

/* 时间列 */
.col-time {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.time-main {
  font-size: 0.85rem;
}

.time-sub {
  font-size: 0.75rem;
  color: var(--text-muted);
}

/* 操作列 */
.col-actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  padding: 5px 12px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  font-size: 0.75rem;
  cursor: pointer;
  transition: all var(--transition);
}

.action-btn:hover {
  border-color: var(--primary);
  color: var(--primary);
}

.action-btn.ship {
  background: var(--primary);
  border-color: var(--primary);
  color: var(--bg-void);
}

.action-btn.cancel:hover {
  border-color: var(--accent);
  color: var(--accent);
}

/* ===== 分页 ===== */
.pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.page-info {
  font-size: 0.85rem;
  color: var(--text-muted);
}

.page-controls {
  display: flex;
  align-items: center;
  gap: 4px;
}

.page-btn {
  width: 32px;
  height: 32px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition);
}

.page-btn:hover:not(:disabled) {
  border-color: var(--primary);
  color: var(--primary);
}

.page-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.page-numbers {
  display: flex;
  gap: 4px;
}

.page-num {
  width: 32px;
  height: 32px;
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  cursor: pointer;
  transition: all var(--transition);
}

.page-num:hover {
  background: var(--bg-hover);
}

.page-num.active {
  background: var(--primary);
  color: var(--bg-void);
}

.page-size {
  padding: 6px 10px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  font-size: 0.8rem;
}

/* ===== 批量操作栏 ===== */
.bulk-actions {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 24px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4);
  z-index: 100;
}

.bulk-info {
  font-size: 0.9rem;
  color: var(--text-muted);
}

.bulk-btn {
  padding: 8px 18px;
  background: var(--primary);
  border: none;
  border-radius: var(--radius-sm);
  color: var(--bg-void);
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition);
}

.bulk-btn:hover {
  opacity: 0.9;
}

.bulk-btn.cancel {
  background: transparent;
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
}

.bulk-btn.cancel:hover {
  border-color: var(--accent);
  color: var(--accent);
}

/* ===== 弹窗 ===== */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.modal-content {
  width: 90%;
  max-width: 500px;
  max-height: 90vh;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-content.detail-modal {
  max-width: 700px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
}

.modal-header h3 {
  font-family: var(--font-display);
  font-size: 1.1rem;
  font-weight: 600;
}

.close-btn {
  width: 32px;
  height: 32px;
  background: var(--bg-elevated);
  border: none;
  border-radius: 50%;
  color: var(--text-muted);
  font-size: 1.2rem;
  cursor: pointer;
  transition: all var(--transition);
}

.close-btn:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.modal-form {
  padding: 24px;
  flex: 1;
  overflow-y: auto;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid var(--border-color);
  flex-shrink: 0;
}

/* 详情弹窗 */
.detail-content {
  padding: 24px;
  max-height: 60vh;
  overflow-y: auto;
}

.detail-section {
  margin-bottom: 24px;
}

.detail-section:last-child {
  margin-bottom: 0;
}

.detail-section h4 {
  font-family: var(--font-display);
  font-size: 0.85rem;
  letter-spacing: 0.05em;
  color: var(--text-muted);
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-light);
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-label {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.info-value {
  font-size: 0.9rem;
}

.info-value.mono {
  font-family: var(--font-mono);
}

/* 商品列表 */
.goods-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.goods-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: var(--bg-elevated);
  border-radius: var(--radius-md);
}

.goods-avatar {
  width: 40px;
  height: 40px;
  background: linear-gradient(135deg, var(--primary-dark), var(--primary));
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-display);
  font-weight: 700;
  color: var(--bg-void);
  flex-shrink: 0;
}

.goods-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.goods-name {
  font-size: 0.9rem;
}

.goods-spec {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.goods-price {
  font-family: var(--font-mono);
  font-size: 0.85rem;
}

.goods-count {
  color: var(--text-muted);
  font-size: 0.85rem;
}

.goods-subtotal {
  font-family: var(--font-display);
  font-weight: 600;
  min-width: 80px;
  text-align: right;
}

/* 金额汇总 */
.amount-summary {
  background: var(--bg-elevated);
  border-radius: var(--radius-md);
  padding: 16px;
}

.amount-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  font-size: 0.9rem;
}

.amount-row:not(:last-child) {
  border-bottom: 1px solid var(--border-light);
}

.amount-row .discount {
  color: var(--accent);
}

.amount-row.total {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 1rem;
  color: var(--primary);
}

/* ===== 响应式 ===== */
@media (max-width: 1200px) {
  .table-header,
  .table-row {
    grid-template-columns: 40px 2fr 1fr 1fr 1fr;
  }
  
  .col-time,
  .col-actions {
    display: none;
  }
}

@media (max-width: 768px) {
  .stats-row {
    flex-wrap: wrap;
  }
  
  .stat-item {
    flex: 1 1 30%;
  }
  
  .filter-bar {
    flex-direction: column;
    align-items: stretch;
  }
  
  .filter-group {
    flex-direction: column;
    align-items: stretch;
  }
  
  .search-box {
    width: 100%;
  }
  
  .filter-actions {
    justify-content: flex-end;
  }
  
  .info-grid {
    grid-template-columns: 1fr;
  }
  
  .bulk-actions {
    left: 16px;
    right: 16px;
    transform: none;
    flex-wrap: wrap;
    justify-content: center;
  }
}
</style>
