<template>
  <div class="products-page">
    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="search-box">
        <span class="search-icon">🔍</span>
        <input 
          v-model="searchQuery" 
          type="text" 
          placeholder="搜索商品名称..." 
          class="search-input"
        />
      </div>
      <div class="toolbar-right">
        <select v-model="filterCategory" class="filter-select">
          <option value="">全部分类</option>
          <option v-for="cat in categories" :key="cat.id" :value="cat.id">{{ cat.name }}</option>
        </select>
        <button class="btn btn-primary" @click="showModal = true">
          <span>+ 添加商品</span>
        </button>
      </div>
    </div>

    <!-- 商品表格 -->
    <div class="products-table">
      <div class="table-header">
        <span class="col-check"><input type="checkbox" /></span>
        <span class="col-product">商品信息</span>
        <span class="col-price">价格</span>
        <span class="col-stock">库存</span>
        <span class="col-status">状态</span>
        <span class="col-actions">操作</span>
      </div>
      
      <div class="table-body">
        <div class="table-row" v-for="product in filteredProducts" :key="product.id">
          <span class="col-check"><input type="checkbox" /></span>
          <div class="col-product">
            <div class="product-image">{{ product.name.charAt(0) }}</div>
            <div class="product-info">
              <span class="product-name">{{ product.name }}</span>
              <span class="product-id">ID: {{ product.id }}</span>
            </div>
          </div>
          <div class="col-price">
            <span class="price-current">¥{{ product.price }}</span>
            <span v-if="product.is_seckill" class="price-seckill">秒杀: ¥{{ product.seckill_price }}</span>
          </div>
          <div class="col-stock">
            <span class="stock-value" :class="{ low: product.stock < 100 }">{{ product.stock }}</span>
            <span class="stock-label">件</span>
          </div>
          <div class="col-status">
            <span class="status-badge" :class="product.status === 1 ? 'active' : 'inactive'">
              {{ product.status === 1 ? '在售' : '下架' }}
            </span>
            <span v-if="product.is_seckill" class="seckill-badge">⚡秒杀</span>
          </div>
          <div class="col-actions">
            <button class="action-btn edit" @click="editProduct(product)">编辑</button>
            <button class="action-btn" @click="toggleStatus(product)">
              {{ product.status === 1 ? '下架' : '上架' }}
            </button>
            <button class="action-btn delete" @click="deleteProduct(product)">删除</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 分页 -->
    <div class="pagination">
      <span class="page-info">共 {{ products.length }} 件商品</span>
      <div class="page-btns">
        <button class="page-btn" :disabled="currentPage === 1" @click="currentPage--">←</button>
        <span class="page-current">{{ currentPage }}</span>
        <button class="page-btn" :disabled="currentPage >= totalPages" @click="currentPage++">→</button>
      </div>
    </div>

    <!-- 添加/编辑弹窗 -->
    <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h3>{{ editingProduct ? '编辑商品' : '添加商品' }}</h3>
          <button class="close-btn" @click="showModal = false">×</button>
        </div>
        
        <form @submit.prevent="saveProduct" class="modal-form">
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">商品名称</label>
              <input v-model="form.name" type="text" class="form-input" required />
            </div>
            <div class="form-group">
              <label class="form-label">分类</label>
              <select v-model="form.category_id" class="form-input">
                <option v-for="cat in categories" :key="cat.id" :value="cat.id">{{ cat.name }}</option>
              </select>
            </div>
          </div>
          
          <div class="form-group">
            <label class="form-label">商品描述</label>
            <textarea v-model="form.desc" class="form-input form-textarea" rows="3"></textarea>
          </div>
          
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">售价 (元)</label>
              <input v-model.number="form.price" type="number" class="form-input" step="0.01" required />
            </div>
            <div class="form-group">
              <label class="form-label">库存</label>
              <input v-model.number="form.stock" type="number" class="form-input" required />
            </div>
            <div class="form-group">
              <label class="form-label">单位</label>
              <input v-model="form.unit" type="text" class="form-input" placeholder="件" />
            </div>
          </div>
          
          <div class="form-check">
            <label class="checkbox-label">
              <input v-model="form.is_seckill" type="checkbox" />
              <span>参与秒杀活动</span>
            </label>
          </div>
          
          <div v-if="form.is_seckill" class="form-row seckill-options">
            <div class="form-group">
              <label class="form-label">秒杀价格</label>
              <input v-model.number="form.seckill_price" type="number" class="form-input" step="0.01" />
            </div>
            <div class="form-group">
              <label class="form-label">秒杀库存</label>
              <input v-model.number="form.seckill_stock" type="number" class="form-input" />
            </div>
            <div class="form-group">
              <label class="form-label">限购数量</label>
              <input v-model.number="form.limit_per_user" type="number" class="form-input" />
            </div>
          </div>
          
          <div class="modal-actions">
            <button type="button" class="btn btn-ghost" @click="showModal = false">取消</button>
            <button type="submit" class="btn btn-primary">保存</button>
          </div>
        </form>
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
  desc: string
  price: number
  stock: number
  unit: string
  status: number
  category_id: number
  is_seckill: boolean
  seckill_price?: number
  seckill_stock?: number
  limit_per_user?: number
}

const products = ref<Product[]>([])
const categories = ref([
  { id: 1, name: '数码电子' },
  { id: 2, name: '家用电器' },
  { id: 3, name: '服饰鞋包' },
  { id: 4, name: '食品饮料' },
])

const searchQuery = ref('')
const filterCategory = ref('')
const currentPage = ref(1)
const showModal = ref(false)
const editingProduct = ref<Product | null>(null)

const form = ref({
  name: '',
  desc: '',
  price: 0,
  stock: 0,
  unit: '件',
  category_id: 1,
  is_seckill: false,
  seckill_price: 0,
  seckill_stock: 0,
  limit_per_user: 2,
})

const filteredProducts = computed(() => {
  return products.value.filter(p => {
    const matchSearch = !searchQuery.value || p.name.includes(searchQuery.value)
    const matchCategory = !filterCategory.value || p.category_id === Number(filterCategory.value)
    return matchSearch && matchCategory
  })
})

const totalPages = computed(() => Math.max(1, Math.ceil(filteredProducts.value.length / 20)))

async function loadProducts() {
  try {
    const res = await goodsApi.list({ page: currentPage.value, size: 20 })
    products.value = res.data.items || res.data || []
  } catch (err) {
    console.error('Failed to load products:', err)
    // Keep existing mock data as fallback
  }
}

function editProduct(product: Product) {
  editingProduct.value = product
  form.value = { ...product }
  showModal.value = true
}

async function saveProduct() {
  try {
    if (editingProduct.value) {
      // Update existing product
      await goodsApi.update(editingProduct.value.id, form.value)
      const idx = products.value.findIndex(p => p.id === editingProduct.value!.id)
      if (idx >= 0) {
        products.value[idx] = { ...products.value[idx], ...form.value }
      }
    } else {
      // Create new product
      const res = await goodsApi.create(form.value)
      const newProduct = res.data || { id: Date.now(), status: 1, ...form.value }
      products.value.unshift(newProduct)
      
      // If is_seckill, initialize seckill inventory
      if (form.value.is_seckill && newProduct.id) {
        await inventoryApi.initSeckill(newProduct.id, {
          stock: form.value.seckill_stock,
          seckill_price: form.value.seckill_price,
          limit_per_user: form.value.limit_per_user,
        })
      }
    }
    resetForm()
    showModal.value = false
  } catch (err) {
    console.error('Failed to save product:', err)
    alert('保存失败，请重试')
  }
}

async function toggleStatus(product: Product) {
  const newStatus = product.status === 1 ? 0 : 1
  try {
    await goodsApi.update(product.id, { status: newStatus })
    product.status = newStatus
  } catch (err) {
    console.error('Failed to toggle status:', err)
    alert('操作失败，请重试')
  }
}

async function deleteProduct(product: Product) {
  if (confirm(`确定删除商品 "${product.name}" 吗？`)) {
    try {
      await goodsApi.delete(product.id)
      products.value = products.value.filter(p => p.id !== product.id)
    } catch (err) {
      console.error('Failed to delete product:', err)
      alert('删除失败，请重试')
    }
  }
}

function resetForm() {
  editingProduct.value = null
  form.value = {
    name: '',
    desc: '',
    price: 0,
    stock: 0,
    unit: '件',
    category_id: 1,
    is_seckill: false,
    seckill_price: 0,
    seckill_stock: 0,
    limit_per_user: 2,
  }
}

onMounted(() => {
  loadProducts()
})
</script>

<style scoped>
.products-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* ===== 工具栏 ===== */
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.search-box {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  width: 320px;
}

.search-icon {
  font-size: 1rem;
  opacity: 0.5;
}

.search-input {
  flex: 1;
  background: transparent;
  border: none;
  color: var(--text-primary);
  font-size: 0.9rem;
  outline: none;
}

.search-input::placeholder {
  color: var(--text-muted);
}

.toolbar-right {
  display: flex;
  gap: 12px;
}

.filter-select {
  padding: 10px 16px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-size: 0.9rem;
  cursor: pointer;
}

/* ===== 表格 ===== */
.products-table {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.table-header,
.table-row {
  display: grid;
  grid-template-columns: 40px 2fr 1fr 0.8fr 1fr 1.5fr;
  gap: 16px;
  padding: 16px 20px;
  align-items: center;
}

.table-header {
  background: var(--bg-elevated);
  font-family: var(--font-display);
  font-size: 0.75rem;
  letter-spacing: 0.1em;
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

.table-row:last-child {
  border-bottom: none;
}

/* 商品列 */
.col-product {
  display: flex;
  align-items: center;
  gap: 14px;
}

.product-image {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, var(--primary-dark), var(--primary));
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-display);
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--bg-void);
}

.product-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.product-name {
  font-weight: 500;
}

.product-id {
  font-size: 0.75rem;
  color: var(--text-muted);
  font-family: var(--font-mono);
}

/* 价格列 */
.col-price {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.price-current {
  font-family: var(--font-display);
  font-size: 1.1rem;
  font-weight: 600;
}

.price-seckill {
  font-size: 0.8rem;
  color: var(--accent);
}

/* 库存列 */
.col-stock {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.stock-value {
  font-family: var(--font-display);
  font-size: 1.1rem;
  font-weight: 600;
}

.stock-value.low {
  color: var(--warning);
}

.stock-label {
  font-size: 0.8rem;
  color: var(--text-muted);
}

/* 状态列 */
.col-status {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.status-badge {
  padding: 4px 12px;
  border-radius: var(--radius-full);
  font-size: 0.75rem;
  font-weight: 500;
}

.status-badge.active {
  background: rgba(0, 245, 160, 0.15);
  color: var(--success);
}

.status-badge.inactive {
  background: rgba(96, 96, 128, 0.2);
  color: var(--text-muted);
}

.seckill-badge {
  padding: 4px 10px;
  background: rgba(255, 46, 99, 0.15);
  color: var(--accent);
  border-radius: var(--radius-full);
  font-size: 0.7rem;
  font-weight: 600;
}

/* 操作列 */
.col-actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  padding: 6px 14px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  font-size: 0.8rem;
  cursor: pointer;
  transition: all var(--transition);
}

.action-btn:hover {
  border-color: var(--primary);
  color: var(--primary);
}

.action-btn.edit:hover {
  border-color: var(--info);
  color: var(--info);
}

.action-btn.delete:hover {
  border-color: var(--accent);
  color: var(--accent);
}

/* ===== 分页 ===== */
.pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.page-info {
  font-size: 0.9rem;
  color: var(--text-muted);
}

.page-btns {
  display: flex;
  align-items: center;
  gap: 8px;
}

.page-btn {
  width: 36px;
  height: 36px;
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

.page-current {
  padding: 0 16px;
  font-family: var(--font-display);
  font-weight: 600;
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
  max-width: 600px;
  max-height: 90vh;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  overflow: hidden;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-color);
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
  max-height: 60vh;
  overflow-y: auto;
}

.form-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 16px;
}

.form-group {
  margin-bottom: 20px;
}

.form-textarea {
  resize: vertical;
  min-height: 80px;
}

.form-check {
  margin-bottom: 20px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  color: var(--text-secondary);
}

.checkbox-label input {
  width: 18px;
  height: 18px;
  accent-color: var(--primary);
}

.seckill-options {
  padding: 16px;
  background: var(--bg-elevated);
  border-radius: var(--radius-md);
  margin-bottom: 20px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color);
}

/* ===== 响应式 ===== */
@media (max-width: 1024px) {
  .table-header,
  .table-row {
    grid-template-columns: 40px 2fr 1fr 1fr;
  }
  
  .col-stock,
  .col-actions {
    display: none;
  }
}

@media (max-width: 640px) {
  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }
  
  .search-box {
    width: 100%;
  }
  
  .toolbar-right {
    justify-content: space-between;
  }
}
</style>
