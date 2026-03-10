<template>
  <div class="container goods-list-page">
    <h1 class="page-title">商品列表</h1>

    <!-- 分类筛选 -->
    <div class="filter-bar">
      <button
        v-for="cat in categories"
        :key="cat.id"
        class="filter-tag"
        :class="{ active: selectedCategory === cat.id }"
        @click="selectedCategory = selectedCategory === cat.id ? null : cat.id"
      >
        {{ cat.name }}
      </button>
    </div>

    <!-- 商品网格 -->
    <div class="goods-grid">
      <div v-for="item in goods" :key="item.id" class="goods-card" @click="$router.push(`/goods/${item.id}`)">
        <div class="goods-img">
          <span v-if="item.is_seckill" class="seckill-badge">秒杀</span>
          <div class="img-placeholder">📦</div>
        </div>
        <div class="goods-info">
          <h3 class="goods-name">{{ item.name }}</h3>
          <p class="goods-desc">{{ item.desc || '暂无描述' }}</p>
          <div class="goods-bottom">
            <span class="price">¥{{ item.price }}</span>
            <span v-if="item.is_seckill" class="seckill-price">秒杀价 ¥{{ item.seckill_price }}</span>
          </div>
        </div>
      </div>
    </div>

    <p v-if="goods.length === 0" class="empty-text">暂无商品数据</p>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { goodsApi } from '../api'

interface Category { id: number; name: string }
interface GoodsItem {
  id: number; name: string; desc: string | null; price: number
  is_seckill: boolean; seckill_price: number | null
}

const categories = ref<Category[]>([])
const goods = ref<GoodsItem[]>([])
const selectedCategory = ref<number | null>(null)

async function loadCategories() {
  try {
    const res = await goodsApi.categories()
    categories.value = res.data
  } catch { /* 分类加载失败不阻塞 */ }
}

async function loadGoods() {
  try {
    const params: any = { page: 1, size: 50 }
    if (selectedCategory.value) params.category_id = selectedCategory.value
    const res = await goodsApi.list(params)
    goods.value = res.data.items
  } catch { goods.value = [] }
}

watch(selectedCategory, loadGoods)
onMounted(() => { loadCategories(); loadGoods() })
</script>

<style scoped>
.goods-list-page {
  padding-bottom: 48px;
}

.page-title {
  font-size: 1.8rem;
  font-weight: 700;
  margin-bottom: 24px;
}

.filter-bar {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 28px;
}

.filter-tag {
  padding: 6px 18px;
  border-radius: 20px;
  border: 1.5px solid var(--border-color);
  background: var(--bg-card);
  cursor: pointer;
  font-size: 0.9rem;
  color: var(--text-secondary);
  transition: all var(--transition);
}

.filter-tag:hover {
  border-color: var(--primary);
  color: var(--primary);
}

.filter-tag.active {
  background: var(--primary);
  border-color: var(--primary);
  color: #fff;
}

.goods-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 20px;
}

.goods-card {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
  cursor: pointer;
  transition: all 0.3s ease;
  border: 1px solid var(--border-light);
}

.goods-card:hover {
  box-shadow: var(--shadow-lg);
  transform: translateY(-4px);
}

.goods-img {
  position: relative;
  height: 180px;
  background: linear-gradient(135deg, #f0f4ff, #faf5ff);
  display: flex;
  align-items: center;
  justify-content: center;
}

.img-placeholder {
  font-size: 4rem;
  opacity: 0.4;
}

.seckill-badge {
  position: absolute;
  top: 12px;
  right: 12px;
  background: linear-gradient(135deg, #ef4444, #ec4899);
  color: #fff;
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
}

.goods-info {
  padding: 16px;
}

.goods-name {
  font-size: 1rem;
  font-weight: 600;
  margin-bottom: 6px;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.goods-desc {
  font-size: 0.85rem;
  color: var(--text-muted);
  margin-bottom: 12px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.goods-bottom {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.price {
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--danger);
}

.seckill-price {
  font-size: 0.8rem;
  color: var(--primary);
  font-weight: 500;
}

.empty-text {
  text-align: center;
  color: var(--text-muted);
  padding: 64px 0;
  font-size: 1rem;
}
</style>
