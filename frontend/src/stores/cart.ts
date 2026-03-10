import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export interface CartItem {
  id: number
  name: string
  price: number
  quantity: number
  image?: string
}

const STORAGE_KEY = 'disseckill_cart'

function loadCart(): CartItem[] {
  try {
    const data = localStorage.getItem(STORAGE_KEY)
    return data ? JSON.parse(data) : []
  } catch {
    return []
  }
}

export const useCartStore = defineStore('cart', () => {
  const items = ref<CartItem[]>(loadCart())

  // 持久化到 localStorage
  watch(items, (v) => localStorage.setItem(STORAGE_KEY, JSON.stringify(v)), { deep: true })

  function addItem(product: { id: number; name: string; price: number }) {
    const existing = items.value.find((i) => i.id === product.id)
    if (existing) {
      existing.quantity += 1
    } else {
      items.value.push({ ...product, quantity: 1 })
    }
  }

  function removeItem(id: number) {
    items.value = items.value.filter((i) => i.id !== id)
  }

  function updateQuantity(id: number, qty: number) {
    const item = items.value.find((i) => i.id === id)
    if (item && qty > 0) {
      item.quantity = qty
    }
  }

  function clear() {
    items.value = []
  }

  return { items, addItem, removeItem, updateQuantity, clear }
})
