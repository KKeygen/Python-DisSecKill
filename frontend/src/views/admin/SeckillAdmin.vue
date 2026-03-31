<template>
  <div class="seckill-admin">
    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon">🎯</div>
        <div class="stat-content">
          <span class="stat-label">进行中活动</span>
          <span class="stat-value">{{ activeCount }}</span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">⏳</div>
        <div class="stat-content">
          <span class="stat-label">即将开始</span>
          <span class="stat-value">{{ upcomingCount }}</span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">📦</div>
        <div class="stat-content">
          <span class="stat-label">参与商品</span>
          <span class="stat-value">{{ totalProducts }}</span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">💰</div>
        <div class="stat-content">
          <span class="stat-label">今日销售额</span>
          <span class="stat-value">¥{{ todaySales.toLocaleString() }}</span>
        </div>
      </div>
    </div>

    <!-- 活动列表工具栏 -->
    <div class="toolbar">
      <div class="tab-group">
        <button 
          v-for="tab in tabs" 
          :key="tab.value"
          class="tab-btn" 
          :class="{ active: activeTab === tab.value }"
          @click="activeTab = tab.value"
        >
          {{ tab.label }}
          <span class="tab-count">{{ getTabCount(tab.value) }}</span>
        </button>
      </div>
      <button class="btn btn-primary" @click="showActivityModal = true">
        <span>+ 创建活动</span>
      </button>
    </div>

    <!-- 活动列表 -->
    <div class="activities-list">
      <div 
        v-for="activity in filteredActivities" 
        :key="activity.id" 
        class="activity-card"
        :class="activity.status"
      >
        <div class="activity-header">
          <div class="activity-status-bar" :class="activity.status"></div>
          <div class="activity-title">
            <h3>{{ activity.name }}</h3>
            <span class="activity-id">活动ID: {{ activity.id }}</span>
          </div>
          <span class="activity-status-badge" :class="activity.status">
            {{ getStatusText(activity.status) }}
          </span>
        </div>

        <div class="activity-time">
          <div class="time-item">
            <span class="time-label">开始时间</span>
            <span class="time-value">{{ activity.start_time }}</span>
          </div>
          <div class="time-arrow">→</div>
          <div class="time-item">
            <span class="time-label">结束时间</span>
            <span class="time-value">{{ activity.end_time }}</span>
          </div>
        </div>

        <div class="activity-products">
          <div class="products-header">
            <span class="products-title">活动商品</span>
            <button class="add-product-btn" @click="showProductPicker(activity)">+ 添加商品</button>
          </div>
          <div class="products-grid">
            <div 
              v-for="product in activity.products" 
              :key="product.id" 
              class="product-item"
            >
              <div class="product-avatar">{{ product.name.charAt(0) }}</div>
              <div class="product-details">
                <span class="product-name">{{ product.name }}</span>
                <div class="product-prices">
                  <span class="original-price">¥{{ product.price }}</span>
                  <span class="seckill-price">¥{{ product.seckill_price }}</span>
                </div>
              </div>
              <div class="product-stock">
                <div class="stock-bar">
                  <div 
                    class="stock-progress" 
                    :style="{ width: getStockPercent(product) + '%' }"
                  ></div>
                </div>
                <span class="stock-text">{{ product.sold }}/{{ product.stock }}</span>
              </div>
              <button class="remove-btn" @click="removeProduct(activity, product)">×</button>
            </div>
          </div>
        </div>

        <div class="activity-actions">
          <button v-if="activity.status === 'pending'" class="action-btn start" @click="startActivity(activity)">
            开始活动
          </button>
          <button v-if="activity.status === 'active'" class="action-btn pause" @click="pauseActivity(activity)">
            暂停活动
          </button>
          <button class="action-btn edit" @click="editActivity(activity)">编辑</button>
          <button class="action-btn delete" @click="deleteActivity(activity)">删除</button>
        </div>
      </div>

      <div v-if="filteredActivities.length === 0" class="empty-state">
        <span class="empty-icon">📭</span>
        <p>暂无{{ activeTab === 'all' ? '' : getStatusText(activeTab) }}活动</p>
        <button class="btn btn-primary" @click="showActivityModal = true">创建活动</button>
      </div>
    </div>

    <!-- 创建/编辑活动弹窗 -->
    <div v-if="showActivityModal" class="modal-overlay" @click.self="showActivityModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h3>{{ editingActivity ? '编辑活动' : '创建秒杀活动' }}</h3>
          <button class="close-btn" @click="showActivityModal = false">×</button>
        </div>
        
        <form @submit.prevent="saveActivity" class="modal-form">
          <div class="form-group">
            <label class="form-label">活动名称</label>
            <input v-model="activityForm.name" type="text" class="form-input" required placeholder="例如：618大促" />
          </div>
          
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">开始时间</label>
              <input v-model="activityForm.start_time" type="datetime-local" class="form-input" required />
            </div>
            <div class="form-group">
              <label class="form-label">结束时间</label>
              <input v-model="activityForm.end_time" type="datetime-local" class="form-input" required />
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">活动描述</label>
            <textarea v-model="activityForm.description" class="form-input form-textarea" rows="2" placeholder="活动说明..."></textarea>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label class="form-label">默认限购数量</label>
              <input v-model.number="activityForm.limit_per_user" type="number" class="form-input" min="1" />
            </div>
            <div class="form-group">
              <label class="form-label">活动标签</label>
              <input v-model="activityForm.tag" type="text" class="form-input" placeholder="爆品/首发/限量" />
            </div>
          </div>
          
          <div class="modal-actions">
            <button type="button" class="btn btn-ghost" @click="showActivityModal = false">取消</button>
            <button type="submit" class="btn btn-primary">保存</button>
          </div>
        </form>
      </div>
    </div>

    <!-- 商品选择器弹窗 -->
    <div v-if="showProductModal" class="modal-overlay" @click.self="showProductModal = false">
      <div class="modal-content wide">
        <div class="modal-header">
          <h3>添加商品到活动</h3>
          <button class="close-btn" @click="showProductModal = false">×</button>
        </div>
        
        <div class="product-picker">
          <div class="picker-search">
            <input v-model="productSearch" type="text" placeholder="搜索商品..." class="form-input" />
          </div>
          
          <div class="picker-list">
            <div 
              v-for="product in availableProducts" 
              :key="product.id" 
              class="picker-item"
              :class="{ selected: selectedProducts.includes(product.id) }"
              @click="toggleProduct(product)"
            >
              <div class="picker-check">
                <span v-if="selectedProducts.includes(product.id)">✓</span>
              </div>
              <div class="picker-info">
                <span class="picker-name">{{ product.name }}</span>
                <span class="picker-price">¥{{ product.price }}</span>
              </div>
            </div>
          </div>
          
          <div class="picker-config" v-if="selectedProducts.length > 0">
            <h4>设置秒杀参数</h4>
            <div class="config-grid">
              <div class="config-item">
                <label>秒杀价格</label>
                <input v-model.number="productConfig.seckill_price" type="number" class="form-input" />
              </div>
              <div class="config-item">
                <label>秒杀库存</label>
                <input v-model.number="productConfig.stock" type="number" class="form-input" />
              </div>
              <div class="config-item">
                <label>限购数量</label>
                <input v-model.number="productConfig.limit_per_user" type="number" class="form-input" />
              </div>
            </div>
          </div>
        </div>
        
        <div class="modal-actions">
          <button type="button" class="btn btn-ghost" @click="showProductModal = false">取消</button>
          <button type="button" class="btn btn-primary" @click="confirmAddProducts">
            添加 {{ selectedProducts.length }} 件商品
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { goodsApi, inventoryApi } from '../../api'

interface Product {
  id: number
  name: string
  price: number
  seckill_price: number
  stock: number
  sold: number
  limit_per_user: number
}

interface Activity {
  id: number
  name: string
  description: string
  start_time: string
  end_time: string
  status: 'pending' | 'active' | 'ended' | 'paused'
  tag: string
  limit_per_user: number
  products: Product[]
}

const tabs = [
  { label: '全部', value: 'all' },
  { label: '进行中', value: 'active' },
  { label: '即将开始', value: 'pending' },
  { label: '已结束', value: 'ended' },
]

const activeTab = ref('all')
const showActivityModal = ref(false)
const showProductModal = ref(false)
const editingActivity = ref<Activity | null>(null)
const currentActivity = ref<Activity | null>(null)
const productSearch = ref('')
const selectedProducts = ref<number[]>([])

const activityForm = ref({
  name: '',
  description: '',
  start_time: '',
  end_time: '',
  tag: '',
  limit_per_user: 2,
})

const productConfig = ref({
  seckill_price: 0,
  stock: 100,
  limit_per_user: 2,
})

// 模拟活动数据
const activities = ref<Activity[]>([
  {
    id: 1,
    name: '618年中大促',
    description: '全年最低价',
    start_time: '2025-06-18 00:00',
    end_time: '2025-06-20 23:59',
    status: 'active',
    tag: '超值',
    limit_per_user: 2,
    products: [
      { id: 1, name: '小米14 Ultra', price: 5999, seckill_price: 4999, stock: 100, sold: 67, limit_per_user: 1 },
      { id: 2, name: '索尼耳机', price: 2999, seckill_price: 1999, stock: 50, sold: 45, limit_per_user: 2 },
    ]
  },
  {
    id: 2,
    name: '数码节特惠',
    description: '数码产品专场',
    start_time: '2025-07-01 10:00',
    end_time: '2025-07-03 22:00',
    status: 'pending',
    tag: '预热',
    limit_per_user: 3,
    products: [
      { id: 3, name: 'iPad Air', price: 4799, seckill_price: 3899, stock: 80, sold: 0, limit_per_user: 1 },
    ]
  },
  {
    id: 3,
    name: '520情人节',
    description: '情人节限定',
    start_time: '2025-05-20 00:00',
    end_time: '2025-05-20 23:59',
    status: 'ended',
    tag: '限定',
    limit_per_user: 1,
    products: [],
  },
])

// 模拟可选商品
const allProducts = ref([
  { id: 1, name: '小米14 Ultra', price: 5999 },
  { id: 2, name: '索尼 WH-1000XM5', price: 2999 },
  { id: 3, name: 'iPad Air 2025', price: 4799 },
  { id: 4, name: '戴森 V15 吸尘器', price: 4490 },
  { id: 5, name: '华为 Mate 60 Pro', price: 6999 },
  { id: 6, name: 'PS5 主机', price: 3499 },
])

// 计算统计
const activeCount = computed(() => activities.value.filter(a => a.status === 'active').length)
const upcomingCount = computed(() => activities.value.filter(a => a.status === 'pending').length)
const totalProducts = computed(() => activities.value.reduce((sum, a) => sum + a.products.length, 0))
const todaySales = ref(128650)

const filteredActivities = computed(() => {
  if (activeTab.value === 'all') return activities.value
  return activities.value.filter(a => a.status === activeTab.value)
})

const availableProducts = computed(() => {
  if (!productSearch.value) return allProducts.value
  return allProducts.value.filter(p => 
    p.name.toLowerCase().includes(productSearch.value.toLowerCase())
  )
})

function getTabCount(tab: string) {
  if (tab === 'all') return activities.value.length
  return activities.value.filter(a => a.status === tab).length
}

function getStatusText(status: string) {
  const map: Record<string, string> = {
    pending: '待开始',
    active: '进行中',
    ended: '已结束',
    paused: '已暂停',
  }
  return map[status] || status
}

function getStockPercent(product: Product) {
  return product.stock === 0 ? 100 : Math.round((product.sold / product.stock) * 100)
}

function editActivity(activity: Activity) {
  editingActivity.value = activity
  activityForm.value = { ...activity }
  showActivityModal.value = true
}

function saveActivity() {
  if (activityForm.value.start_time >= activityForm.value.end_time) {
    alert('结束时间必须晚于开始时间')
    return
  }
  if (editingActivity.value) {
    Object.assign(editingActivity.value, activityForm.value)
  } else {
    activities.value.unshift({
      id: Date.now(),
      ...activityForm.value,
      status: 'pending',
      products: [],
    })
  }
  resetActivityForm()
  showActivityModal.value = false
}

function startActivity(activity: Activity) {
  // Initialize all products in Redis
  for (const product of activity.products) {
    try {
      inventoryApi.initSeckill(product.id, {
        stock: product.stock - product.sold,
        seckill_price: product.seckill_price,
        limit_per_user: product.limit_per_user,
      })
    } catch (err) {
      console.error(`Failed to init seckill for product ${product.id}:`, err)
    }
  }
  activity.status = 'active'
}

function pauseActivity(activity: Activity) {
  activity.status = 'paused'
}

function deleteActivity(activity: Activity) {
  if (confirm(`确定删除活动 "${activity.name}" 吗？`)) {
    activities.value = activities.value.filter(a => a.id !== activity.id)
  }
}

function showProductPicker(activity: Activity) {
  currentActivity.value = activity
  selectedProducts.value = []
  showProductModal.value = true
}

function toggleProduct(product: { id: number }) {
  const idx = selectedProducts.value.indexOf(product.id)
  if (idx >= 0) {
    selectedProducts.value.splice(idx, 1)
  } else {
    selectedProducts.value.push(product.id)
  }
}

function confirmAddProducts() {
  if (!currentActivity.value) return
  
  const existingIds = currentActivity.value.products.map(p => p.id)
  const newProducts = allProducts.value
    .filter(p => selectedProducts.value.includes(p.id) && !existingIds.includes(p.id))
    .map(p => ({
      ...p,
      seckill_price: productConfig.value.seckill_price || Math.round(p.price * 0.8),
      stock: productConfig.value.stock,
      sold: 0,
      limit_per_user: productConfig.value.limit_per_user,
    }))
  
  // Initialize seckill inventory in Redis for each product
  for (const product of newProducts) {
    try {
      inventoryApi.initSeckill(product.id, {
        stock: product.stock,
        seckill_price: product.seckill_price,
        limit_per_user: product.limit_per_user,
      })
    } catch (err) {
      console.error(`Failed to init seckill for product ${product.id}:`, err)
    }
  }
  
  currentActivity.value.products.push(...newProducts)
  showProductModal.value = false
}

function removeProduct(activity: Activity, product: Product) {
  activity.products = activity.products.filter(p => p.id !== product.id)
}

function resetActivityForm() {
  editingActivity.value = null
  activityForm.value = {
    name: '',
    description: '',
    start_time: '',
    end_time: '',
    tag: '',
    limit_per_user: 2,
  }
}

async function loadActivities() {
  // Activities are managed locally for now since backend doesn't have activity endpoint
  // But we can load seckill-enabled products
  try {
    const res = await goodsApi.list({ page: 1, size: 100 })
    const goods = res.data.items || res.data || []
    // Filter seckill products and group by activity (simplified)
    allProducts.value = goods.map((g: any) => ({
      id: g.id,
      name: g.name,
      price: g.price,
    }))
  } catch (err) {
    console.error('Failed to load products:', err)
  }
}

onMounted(() => {
  loadActivities()
})
</script>

<style scoped>
.seckill-admin {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* ===== 统计卡片 ===== */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px 24px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
}

.stat-icon {
  width: 48px;
  height: 48px;
  background: var(--bg-elevated);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
}

.stat-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-label {
  font-size: 0.8rem;
  color: var(--text-muted);
}

.stat-value {
  font-family: var(--font-display);
  font-size: 1.4rem;
  font-weight: 700;
}

/* ===== 工具栏 ===== */
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.tab-group {
  display: flex;
  gap: 8px;
  padding: 4px;
  background: var(--bg-card);
  border-radius: var(--radius-md);
}

.tab-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  font-size: 0.9rem;
  cursor: pointer;
  transition: all var(--transition);
}

.tab-btn:hover {
  color: var(--text-primary);
}

.tab-btn.active {
  background: var(--primary);
  color: var(--bg-void);
}

.tab-count {
  padding: 2px 8px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: var(--radius-full);
  font-size: 0.75rem;
}

.tab-btn.active .tab-count {
  background: rgba(0, 0, 0, 0.2);
}

/* ===== 活动列表 ===== */
.activities-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.activity-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  overflow: hidden;
}

.activity-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-light);
}

.activity-status-bar {
  width: 4px;
  height: 40px;
  border-radius: 2px;
}

.activity-status-bar.active {
  background: var(--success);
  box-shadow: 0 0 10px var(--success);
}

.activity-status-bar.pending {
  background: var(--warning);
}

.activity-status-bar.ended {
  background: var(--text-muted);
}

.activity-status-bar.paused {
  background: var(--info);
}

.activity-title {
  flex: 1;
}

.activity-title h3 {
  font-family: var(--font-display);
  font-size: 1.1rem;
  margin-bottom: 4px;
}

.activity-id {
  font-size: 0.75rem;
  color: var(--text-muted);
  font-family: var(--font-mono);
}

.activity-status-badge {
  padding: 6px 14px;
  border-radius: var(--radius-full);
  font-size: 0.8rem;
  font-weight: 500;
}

.activity-status-badge.active {
  background: rgba(0, 245, 160, 0.15);
  color: var(--success);
}

.activity-status-badge.pending {
  background: rgba(255, 181, 71, 0.15);
  color: var(--warning);
}

.activity-status-badge.ended {
  background: var(--bg-elevated);
  color: var(--text-muted);
}

.activity-status-badge.paused {
  background: rgba(0, 183, 235, 0.15);
  color: var(--info);
}

/* 时间区域 */
.activity-time {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 16px 24px;
  background: var(--bg-elevated);
}

.time-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.time-label {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.time-value {
  font-family: var(--font-mono);
  font-size: 0.9rem;
}

.time-arrow {
  color: var(--text-muted);
  font-size: 1.2rem;
}

/* 商品区域 */
.activity-products {
  padding: 20px 24px;
}

.products-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.products-title {
  font-family: var(--font-display);
  font-size: 0.85rem;
  letter-spacing: 0.05em;
  color: var(--text-muted);
}

.add-product-btn {
  padding: 6px 14px;
  background: var(--bg-elevated);
  border: 1px dashed var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  font-size: 0.8rem;
  cursor: pointer;
  transition: all var(--transition);
}

.add-product-btn:hover {
  border-color: var(--primary);
  color: var(--primary);
}

.products-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.product-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
  background: var(--bg-elevated);
  border-radius: var(--radius-md);
  position: relative;
}

.product-avatar {
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
}

.product-details {
  flex: 1;
}

.product-name {
  font-size: 0.9rem;
  display: block;
  margin-bottom: 4px;
}

.product-prices {
  display: flex;
  gap: 12px;
  align-items: center;
}

.original-price {
  font-size: 0.8rem;
  color: var(--text-muted);
  text-decoration: line-through;
}

.seckill-price {
  font-family: var(--font-display);
  font-weight: 600;
  color: var(--accent);
}

.product-stock {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
  min-width: 100px;
}

.stock-bar {
  width: 80px;
  height: 6px;
  background: var(--bg-card);
  border-radius: 3px;
  overflow: hidden;
}

.stock-progress {
  height: 100%;
  background: linear-gradient(90deg, var(--primary), var(--accent));
  border-radius: 3px;
  transition: width 0.3s;
}

.stock-text {
  font-size: 0.75rem;
  color: var(--text-muted);
  font-family: var(--font-mono);
}

.remove-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 20px;
  height: 20px;
  background: transparent;
  border: none;
  color: var(--text-muted);
  font-size: 1rem;
  cursor: pointer;
  opacity: 0;
  transition: opacity var(--transition);
}

.product-item:hover .remove-btn {
  opacity: 1;
}

.remove-btn:hover {
  color: var(--accent);
}

/* 操作区域 */
.activity-actions {
  display: flex;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid var(--border-light);
}

.activity-actions .action-btn {
  padding: 8px 20px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  font-size: 0.85rem;
  cursor: pointer;
  transition: all var(--transition);
}

.activity-actions .action-btn:hover {
  border-color: var(--primary);
  color: var(--primary);
}

.activity-actions .action-btn.start {
  background: var(--success);
  border-color: var(--success);
  color: var(--bg-void);
}

.activity-actions .action-btn.pause {
  background: var(--warning);
  border-color: var(--warning);
  color: var(--bg-void);
}

.activity-actions .action-btn.delete:hover {
  border-color: var(--accent);
  color: var(--accent);
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 60px 20px;
  background: var(--bg-card);
  border: 1px dashed var(--border-color);
  border-radius: var(--radius-xl);
}

.empty-icon {
  font-size: 3rem;
  display: block;
  margin-bottom: 16px;
}

.empty-state p {
  color: var(--text-muted);
  margin-bottom: 20px;
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

.modal-content.wide {
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

.form-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.form-group {
  margin-bottom: 20px;
}

.form-textarea {
  resize: vertical;
  min-height: 60px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid var(--border-color);
  flex-shrink: 0;
}

/* 商品选择器 */
.product-picker {
  padding: 24px;
  flex: 1;
  overflow-y: auto;
}

.picker-search {
  margin-bottom: 16px;
}

.picker-list {
  max-height: 200px;
  overflow-y: auto;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
}

.picker-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-light);
  cursor: pointer;
  transition: background var(--transition);
}

.picker-item:hover {
  background: var(--bg-hover);
}

.picker-item.selected {
  background: rgba(0, 245, 212, 0.1);
}

.picker-item:last-child {
  border-bottom: none;
}

.picker-check {
  width: 24px;
  height: 24px;
  border: 2px solid var(--border-color);
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary);
  font-weight: bold;
}

.picker-item.selected .picker-check {
  background: var(--primary);
  border-color: var(--primary);
  color: var(--bg-void);
}

.picker-info {
  flex: 1;
  display: flex;
  justify-content: space-between;
}

.picker-name {
  font-size: 0.9rem;
}

.picker-price {
  color: var(--text-muted);
  font-family: var(--font-mono);
}

.picker-config {
  margin-top: 20px;
  padding: 16px;
  background: var(--bg-elevated);
  border-radius: var(--radius-md);
}

.picker-config h4 {
  font-size: 0.9rem;
  margin-bottom: 12px;
}

.config-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.config-item label {
  display: block;
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-bottom: 4px;
}

/* ===== 响应式 ===== */
@media (max-width: 1024px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }
  
  .toolbar {
    flex-direction: column;
    gap: 16px;
  }
  
  .tab-group {
    width: 100%;
    overflow-x: auto;
  }
  
  .activity-time {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
  
  .time-arrow {
    transform: rotate(90deg);
  }
  
  .form-row,
  .config-grid {
    grid-template-columns: 1fr;
  }
}
</style>
