<template>
  <div class="container cart-page">
    <h1 class="page-title">🛒 购物车</h1>

    <div v-if="cartItems.length > 0" class="cart-layout">
      <div class="cart-items">
        <div v-for="(item, index) in cartItems" :key="item.id" class="cart-item card">
          <div class="item-img">📦</div>
          <div class="item-info">
            <h3>{{ item.name }}</h3>
            <p class="item-price">¥{{ item.price }}</p>
          </div>
          <div class="item-quantity">
            <button class="qty-btn" @click="changeQty(index, -1)" :disabled="item.quantity <= 1">−</button>
            <span class="qty-value">{{ item.quantity }}</span>
            <button class="qty-btn" @click="changeQty(index, 1)">+</button>
          </div>
          <div class="item-subtotal">
            ¥{{ (item.price * item.quantity).toFixed(2) }}
          </div>
          <button class="remove-btn" @click="removeItem(index)" title="删除">✕</button>
        </div>
      </div>

      <div class="cart-summary card">
        <h2>订单摘要</h2>
        <div class="summary-row">
          <span>商品数量</span>
          <span>{{ totalCount }} 件</span>
        </div>
        <div class="summary-row">
          <span>商品总价</span>
          <span>¥{{ totalPrice.toFixed(2) }}</span>
        </div>
        <div class="summary-row">
          <span>运费</span>
          <span class="free-shipping">免运费</span>
        </div>
        <hr />
        <div class="summary-row total">
          <span>合计</span>
          <span class="total-price">¥{{ totalPrice.toFixed(2) }}</span>
        </div>
        <button class="btn btn-primary btn-block btn-lg" @click="handleCheckout">
          去结算
        </button>
      </div>
    </div>

    <div v-else class="empty-cart">
      <div class="empty-icon">🛒</div>
      <p>购物车是空的</p>
      <router-link to="/goods" class="btn btn-primary">去逛逛</router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useCartStore } from '../stores/cart'
import { useRouter } from 'vue-router'

const cart = useCartStore()
const router = useRouter()

const cartItems = computed(() => cart.items)
const totalCount = computed(() => cart.items.reduce((s, i) => s + i.quantity, 0))
const totalPrice = computed(() => cart.items.reduce((s, i) => s + i.price * i.quantity, 0))

function changeQty(index: number, delta: number) {
  const item = cart.items[index]
  cart.updateQuantity(item.id, item.quantity + delta)
}

function removeItem(index: number) {
  cart.removeItem(cart.items[index].id)
}

function handleCheckout() {
  router.push('/orders')
}
</script>

<style scoped>
.page-title {
  font-size: 1.8rem;
  font-weight: 700;
  margin-bottom: 24px;
}

.cart-layout {
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 24px;
  align-items: start;
}

.cart-items {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.cart-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
}

.item-img {
  width: 64px;
  height: 64px;
  background: var(--bg-input);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.8rem;
  flex-shrink: 0;
}

.item-info {
  flex: 1;
  min-width: 0;
}

.item-info h3 {
  font-size: 0.95rem;
  font-weight: 600;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.item-price {
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.item-quantity {
  display: flex;
  align-items: center;
  gap: 8px;
}

.qty-btn {
  width: 32px;
  height: 32px;
  border: 1.5px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: var(--bg-card);
  cursor: pointer;
  font-size: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition);
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
  min-width: 24px;
  text-align: center;
  font-weight: 600;
}

.item-subtotal {
  font-weight: 600;
  color: var(--danger);
  min-width: 80px;
  text-align: right;
}

.remove-btn {
  width: 28px;
  height: 28px;
  border: none;
  background: none;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 0.9rem;
  border-radius: 50%;
  transition: all var(--transition);
}

.remove-btn:hover {
  background: #fef2f2;
  color: var(--danger);
}

/* ===== Summary ===== */
.cart-summary {
  position: sticky;
  top: 80px;
}

.cart-summary h2 {
  font-size: 1.1rem;
  margin-bottom: 20px;
}

.summary-row {
  display: flex;
  justify-content: space-between;
  font-size: 0.9rem;
  color: var(--text-secondary);
  margin-bottom: 12px;
}

.summary-row.total {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 20px;
}

.total-price {
  color: var(--danger);
  font-size: 1.3rem;
}

.free-shipping {
  color: var(--success);
  font-weight: 500;
}

hr {
  border: none;
  border-top: 1px solid var(--border-light);
  margin: 16px 0;
}

/* ===== Empty ===== */
.empty-cart {
  text-align: center;
  padding: 80px 0;
}

.empty-icon {
  font-size: 4rem;
  opacity: 0.3;
  margin-bottom: 16px;
}

.empty-cart p {
  color: var(--text-muted);
  margin-bottom: 20px;
  font-size: 1.1rem;
}

@media (max-width: 768px) {
  .cart-layout {
    grid-template-columns: 1fr;
  }
  .cart-item {
    flex-wrap: wrap;
  }
}
</style>
