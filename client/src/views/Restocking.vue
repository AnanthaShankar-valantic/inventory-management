<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div class="card budget-card">
      <label class="budget-label" for="budget-slider">
        {{ t('restocking.budget') }}: <strong>{{ formatMoney(budget) }}</strong>
      </label>
      <input
        id="budget-slider"
        v-model.number="budget"
        class="budget-slider"
        type="range"
        min="0"
        max="40000"
        step="500"
      />
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <div class="stats-grid">
        <div class="stat-card info">
          <div class="stat-label">{{ t('restocking.totalCost') }}</div>
          <div class="stat-value">{{ formatMoney(result.total_cost) }}</div>
        </div>
        <div class="stat-card success">
          <div class="stat-label">{{ t('restocking.remainingBudget') }}</div>
          <div class="stat-value">{{ formatMoney(result.remaining_budget) }}</div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.recommendedItems') }} ({{ result.items.length }})</h3>
          <button
            class="place-order-btn"
            :disabled="!result.items.length || submitting || stale"
            @click="placeOrder"
          >
            {{ submitting ? t('restocking.placing') : t('restocking.placeOrder') }}
          </button>
        </div>

        <div v-if="orderError" class="error">{{ orderError }}</div>
        <div v-if="confirmation" class="confirmation">{{ confirmation }}</div>

        <div v-if="!result.items.length" class="empty">{{ t('restocking.noItems') }}</div>
        <div v-else class="table-container">
          <table>
            <thead>
              <tr>
                <th>{{ t('restocking.table.sku') }}</th>
                <th>{{ t('restocking.table.name') }}</th>
                <th class="num">{{ t('restocking.table.quantity') }}</th>
                <th class="num">{{ t('restocking.table.unitCost') }}</th>
                <th class="num">{{ t('restocking.table.lineCost') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in result.items" :key="item.sku">
                <td><strong>{{ item.sku }}</strong></td>
                <td>{{ translateProductName(item.name) }}</td>
                <td class="num">{{ item.quantity.toLocaleString() }}</td>
                <td class="num">{{ formatMoney(item.unit_cost, 2) }}</td>
                <td class="num"><strong>{{ formatMoney(item.line_cost) }}</strong></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'
import { formatCurrencyWithDecimals } from '../utils/currency'

export default {
  name: 'Restocking',
  setup() {
    const { t, currentCurrency, currentLocale, translateProductName } = useI18n()

    const budget = ref(10000)
    const result = ref({ items: [], total_cost: 0, remaining_budget: 0 })
    const loading = ref(true)
    const error = ref(null)
    const submitting = ref(false)
    const orderError = ref(null)
    const confirmation = ref(null)

    // Backend returns USD; formatCurrency converts when the UI currency is JPY.
    const formatMoney = (amount, decimals = 0) =>
      formatCurrencyWithDecimals(amount, currentCurrency.value, decimals)

    const formatDate = (dateString) => {
      const date = new Date(dateString)
      if (isNaN(date.getTime())) return dateString
      return date.toLocaleDateString(currentLocale.value === 'ja' ? 'ja-JP' : 'en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      })
    }

    // Slider drags fire many requests; only the latest one may update the UI.
    let requestId = 0
    const loadRecommendations = async () => {
      const id = ++requestId
      try {
        error.value = null
        const data = await api.getRestockRecommendations(budget.value)
        if (id !== requestId) return
        result.value = data
        stale.value = false
      } catch (err) {
        if (id !== requestId) return
        error.value = 'Failed to load recommendations: ' + err.message
        console.error('Load error:', err)
      } finally {
        if (id === requestId) loading.value = false
      }
    }

    // True while the list on screen was computed for an older budget; ordering then would buy items the slider no longer shows.
    const stale = ref(false)
    let debounceTimer = null
    watch(budget, () => {
      stale.value = true
      clearTimeout(debounceTimer)
      debounceTimer = setTimeout(loadRecommendations, 250)
    })

    const placeOrder = async () => {
      if (submitting.value || stale.value || !result.value.items.length) return
      submitting.value = true
      orderError.value = null
      confirmation.value = null
      try {
        const order = await api.placeRestockOrder(
          result.value.items.map(({ sku, quantity }) => ({ sku, quantity }))
        )
        confirmation.value = t('restocking.orderPlaced', {
          orderNumber: order.order_number,
          days: order.lead_time_days,
          date: formatDate(order.expected_delivery)
        })
        await loadRecommendations()
      } catch (err) {
        orderError.value = t('restocking.orderFailed') + ': ' + (err.response?.data?.detail || err.message)
        console.error('Order error:', err)
      } finally {
        submitting.value = false
      }
    }

    onMounted(loadRecommendations)
    onBeforeUnmount(() => clearTimeout(debounceTimer))

    return {
      t,
      budget,
      result,
      loading,
      error,
      submitting,
      stale,
      orderError,
      confirmation,
      formatMoney,
      placeOrder,
      translateProductName
    }
  }
}
</script>

<style scoped>
.budget-card {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

.budget-label {
  color: var(--text-sub);
  font-size: 0.875rem;
}

.budget-label strong {
  color: var(--text);
}

.budget-slider {
  width: 100%;
  accent-color: var(--text);
}

.place-order-btn {
  background: var(--text);
  color: white;
  border: none;
  border-radius: 6px;
  padding: 0.5rem 1rem;
  font-weight: 500;
  cursor: pointer;
}

.place-order-btn:disabled {
  background: var(--border);
  color: var(--text-sub);
  cursor: not-allowed;
}

.confirmation {
  margin-bottom: 1rem;
  padding: 0.75rem 1rem;
  border: 1px solid #bbf7d0;
  background: #f0fdf4;
  border-radius: 6px;
  color: #166534;
}

.empty {
  padding: 1.5rem;
  text-align: center;
  color: var(--text-sub);
}

.num {
  text-align: right;
}
</style>
