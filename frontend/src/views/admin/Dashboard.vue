<template>
  <div class="dashboard">
    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div class="stat-card" style="animation-delay: 0s">
        <div class="stat-header">
          <span class="stat-icon" style="background: linear-gradient(135deg, #00f5d4, #00c4aa)">📦</span>
          <span class="stat-trend up">+12.5%</span>
        </div>
        <div class="stat-value">{{ stats.todayOrders }}</div>
        <div class="stat-label">今日订单</div>
        <div class="stat-bar">
          <div class="stat-bar-fill" style="width: 75%; background: linear-gradient(135deg, #00f5d4, #00c4aa)"></div>
        </div>
      </div>
      
      <div class="stat-card" style="animation-delay: 0.1s">
        <div class="stat-header">
          <span class="stat-icon" style="background: linear-gradient(135deg, #ff2e63, #d41e4f)">💰</span>
          <span class="stat-trend up">+8.2%</span>
        </div>
        <div class="stat-value">¥{{ (stats.todaySales || 0).toLocaleString() }}</div>
        <div class="stat-label">今日收入</div>
        <div class="stat-bar">
          <div class="stat-bar-fill" style="width: 68%; background: linear-gradient(135deg, #ff2e63, #d41e4f)"></div>
        </div>
      </div>
      
      <div class="stat-card" style="animation-delay: 0.2s">
        <div class="stat-header">
          <span class="stat-icon" style="background: linear-gradient(135deg, #ffd93d, #f59e0b)">👥</span>
          <span class="stat-trend up">+5.7%</span>
        </div>
        <div class="stat-value">{{ stats.activeUsers }}</div>
        <div class="stat-label">活跃用户</div>
        <div class="stat-bar">
          <div class="stat-bar-fill" style="width: 82%; background: linear-gradient(135deg, #ffd93d, #f59e0b)"></div>
        </div>
      </div>
      
      <div class="stat-card" style="animation-delay: 0.3s">
        <div class="stat-header">
          <span class="stat-icon" style="background: linear-gradient(135deg, #00d9ff, #0099cc)">⚡</span>
          <span class="stat-trend down">-2.3%</span>
        </div>
        <div class="stat-value">{{ stats.seckillItems }}</div>
        <div class="stat-label">秒杀参与</div>
        <div class="stat-bar">
          <div class="stat-bar-fill" style="width: 91%; background: linear-gradient(135deg, #00d9ff, #0099cc)"></div>
        </div>
      </div>
    </div>

    <!-- 图表区域 -->
    <div class="charts-row">
      <div class="chart-card">
        <div class="card-header">
          <h3>订单趋势</h3>
          <div class="time-filter">
            <button class="filter-btn active">今日</button>
            <button class="filter-btn">本周</button>
            <button class="filter-btn">本月</button>
          </div>
        </div>
        <div class="chart-placeholder">
          <div class="chart-bars">
            <div class="bar" v-for="(h, i) in chartData" :key="i" :style="{ height: h + '%' }">
              <span class="bar-value">{{ Math.round(h * 1.5) }}</span>
            </div>
          </div>
          <div class="chart-labels">
            <span v-for="i in 12" :key="i">{{ i * 2 }}:00</span>
          </div>
        </div>
      </div>

      <div class="chart-card">
        <div class="card-header">
          <h3>秒杀热度</h3>
        </div>
        <div class="hot-list">
          <div class="hot-item" v-for="(item, idx) in hotItems" :key="item.name">
            <span class="hot-rank" :class="{ top: idx < 3 }">{{ idx + 1 }}</span>
            <span class="hot-name">{{ item.name }}</span>
            <div class="hot-bar-wrapper">
              <div class="hot-bar" :style="{ width: item.percent + '%' }"></div>
            </div>
            <span class="hot-value">{{ item.sold }}件</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 最近订单 -->
    <div class="recent-section">
      <div class="card-header">
        <h3>最近订单</h3>
        <router-link to="/admin/orders" class="view-all">查看全部 →</router-link>
      </div>
      <div class="orders-table">
        <div class="table-header">
          <span>订单号</span>
          <span>用户</span>
          <span>商品</span>
          <span>金额</span>
          <span>状态</span>
          <span>时间</span>
        </div>
        <div class="table-row" v-for="order in recentOrders" :key="order.id">
          <span class="order-id">{{ order.id }}</span>
          <span>{{ order.user }}</span>
          <span>{{ order.product }}</span>
          <span class="amount">¥{{ order.amount }}</span>
          <span class="status" :class="order.statusClass">{{ order.status }}</span>
          <span class="time">{{ order.time }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { orderApi, goodsApi } from '../../api'

const stats = ref({
  todayOrders: 0,
  todaySales: 0,
  activeUsers: 0,
  seckillItems: 0,
})

const chartData = ref([45, 62, 78, 55, 89, 72, 94, 68, 85, 76, 92, 88])

const hotItems = ref<any[]>([])

const recentOrders = ref<any[]>([])

async function loadData() {
  // Load recent orders
  try {
    const ordersRes = await orderApi.list({ page: 1, size: 10 })
    const ordersData = ordersRes.data.items || ordersRes.data || []
    recentOrders.value = ordersData.map((o: any) => ({
      id: o.order_id || o.id,
      user: `用户${o.user_id}`,
      product: o.goods_name || '商品',
      amount: o.total_price || o.total_amount || 0,
      status: o.order_status || o.status,
      statusClass: getStatusClass(o.order_status || o.status),
      time: o.created_at || o.create_time || '-',
    }))
    
    // Calculate stats from orders
    const allOrders = ordersRes.data.items || ordersRes.data || []
    stats.value.todayOrders = allOrders.length
    stats.value.todaySales = allOrders.reduce((sum: number, o: any) => sum + (o.total_price || 0), 0)
  } catch (err) {
    console.error('Failed to load orders:', err)
  }

  // Load products for hot items
  try {
    const goodsRes = await goodsApi.list({ page: 1, size: 5 })
    const goodsData = goodsRes.data.items || goodsRes.data || []
    hotItems.value = goodsData.map((g: any, idx: number) => {
      const sold = g.sales || Math.floor(Math.random() * 500)
      return {
        id: g.id,
        name: g.name,
        sold: sold,
        percent: Math.round((sold / 1000) * 100),
      }
    })
  } catch (err) {
    console.error('Failed to load goods:', err)
  }
}

function getStatusClass(status: string): string {
  const statusMap: { [key: string]: string } = {
    'paid': 'paid',
    'pending': 'pending',
    'shipped': 'shipped',
    'cancelled': 'cancelled',
    'completed': 'paid',
  }
  return statusMap[status] || 'pending'
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

/* ===== 统计卡片 ===== */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}

.stat-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 24px;
  animation: fade-in 0.5s ease forwards;
  opacity: 0;
}

@keyframes fade-in {
  to { opacity: 1; }
}

.stat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
}

.stat-trend {
  font-family: var(--font-display);
  font-size: 0.8rem;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: var(--radius-full);
}

.stat-trend.up {
  background: rgba(0, 245, 160, 0.15);
  color: var(--success);
}

.stat-trend.down {
  background: rgba(255, 46, 99, 0.15);
  color: var(--accent);
}

.stat-value {
  font-family: var(--font-display);
  font-size: 2rem;
  font-weight: 700;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 0.9rem;
  color: var(--text-muted);
  margin-bottom: 16px;
}

.stat-bar {
  height: 4px;
  background: var(--bg-elevated);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.stat-bar-fill {
  height: 100%;
  border-radius: var(--radius-full);
  transition: width 1s ease;
}

/* ===== 图表区域 ===== */
.charts-row {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 20px;
}

.chart-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 24px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.card-header h3 {
  font-family: var(--font-display);
  font-size: 1rem;
  font-weight: 600;
  letter-spacing: 0.05em;
}

.time-filter {
  display: flex;
  gap: 4px;
}

.filter-btn {
  padding: 6px 14px;
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  font-size: 0.8rem;
  cursor: pointer;
  transition: all var(--transition);
}

.filter-btn:hover {
  border-color: var(--primary);
  color: var(--primary);
}

.filter-btn.active {
  background: var(--primary-bg);
  border-color: var(--primary);
  color: var(--primary);
}

.chart-placeholder {
  height: 200px;
  display: flex;
  flex-direction: column;
}

.chart-bars {
  flex: 1;
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding-bottom: 8px;
}

.bar {
  flex: 1;
  background: linear-gradient(to top, var(--primary-dark), var(--primary));
  border-radius: var(--radius-sm) var(--radius-sm) 0 0;
  position: relative;
  min-height: 10px;
  transition: height 0.5s ease;
}

.bar:hover {
  background: linear-gradient(to top, var(--accent-dark), var(--accent));
}

.bar-value {
  position: absolute;
  top: -20px;
  left: 50%;
  transform: translateX(-50%);
  font-family: var(--font-display);
  font-size: 0.7rem;
  color: var(--text-muted);
  opacity: 0;
  transition: opacity 0.2s;
}

.bar:hover .bar-value {
  opacity: 1;
}

.chart-labels {
  display: flex;
  justify-content: space-between;
  padding-top: 8px;
  border-top: 1px solid var(--border-color);
  font-size: 0.7rem;
  color: var(--text-muted);
}

/* ===== 热度列表 ===== */
.hot-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.hot-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.hot-rank {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--bg-elevated);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-display);
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--text-muted);
}

.hot-rank.top {
  background: linear-gradient(135deg, var(--accent-dark), var(--accent));
  color: #fff;
}

.hot-name {
  flex: 1;
  font-size: 0.9rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.hot-bar-wrapper {
  width: 100px;
  height: 6px;
  background: var(--bg-elevated);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.hot-bar {
  height: 100%;
  background: linear-gradient(90deg, var(--primary), var(--accent));
  border-radius: var(--radius-full);
}

.hot-value {
  font-family: var(--font-display);
  font-size: 0.8rem;
  color: var(--text-muted);
  min-width: 50px;
  text-align: right;
}

/* ===== 最近订单 ===== */
.recent-section {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 24px;
}

.view-all {
  font-size: 0.85rem;
  color: var(--primary);
}

.orders-table {
  margin-top: 8px;
}

.table-header,
.table-row {
  display: grid;
  grid-template-columns: 2fr 1fr 1.5fr 1fr 1fr 0.8fr;
  gap: 16px;
  padding: 14px 0;
  align-items: center;
}

.table-header {
  font-family: var(--font-display);
  font-size: 0.75rem;
  letter-spacing: 0.1em;
  color: var(--text-muted);
  text-transform: uppercase;
  border-bottom: 1px solid var(--border-color);
}

.table-row {
  font-size: 0.9rem;
  border-bottom: 1px solid var(--border-light);
  transition: background var(--transition);
}

.table-row:hover {
  background: var(--bg-hover);
}

.order-id {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.amount {
  font-family: var(--font-display);
  font-weight: 600;
  color: var(--accent);
}

.status {
  display: inline-block;
  padding: 4px 10px;
  border-radius: var(--radius-full);
  font-size: 0.75rem;
  font-weight: 500;
}

.status.paid {
  background: rgba(0, 245, 160, 0.15);
  color: var(--success);
}

.status.pending {
  background: rgba(255, 217, 61, 0.15);
  color: var(--warning);
}

.status.shipped {
  background: rgba(0, 217, 255, 0.15);
  color: var(--info);
}

.status.cancelled {
  background: rgba(255, 46, 99, 0.15);
  color: var(--accent);
}

.time {
  font-size: 0.85rem;
  color: var(--text-muted);
}

/* ===== 响应式 ===== */
@media (max-width: 1200px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .charts-row {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }
  
  .table-header,
  .table-row {
    grid-template-columns: 1fr 1fr;
    gap: 8px;
  }
  
  .table-row span:nth-child(n+3) {
    display: none;
  }
}
</style>
