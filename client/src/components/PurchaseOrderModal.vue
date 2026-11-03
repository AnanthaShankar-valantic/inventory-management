<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="isOpen && backlogItem" class="modal-overlay" @click="close">
        <div class="modal-container" @click.stop>
          <div class="modal-header">
            <h3 class="modal-title">
              {{ mode === 'view' ? t('purchaseOrder.viewTitle') : t('purchaseOrder.createTitle') }}
            </h3>
            <button class="close-button" @click="close">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M15 5L5 15M5 5L15 15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
              </svg>
            </button>
          </div>

          <div class="modal-body">
            <div class="item-summary">
              <div class="item-name">{{ translateProductName(backlogItem.item_name) }}</div>
              <div class="item-meta">
                {{ t('purchaseOrder.sku') }}: {{ backlogItem.item_sku }} ·
                {{ t('purchaseOrder.orderId') }}: {{ backlogItem.order_id }}
              </div>
            </div>

            <!-- Create mode -->
            <form v-if="mode === 'create'" id="po-form" class="po-form" @submit.prevent="submit">
              <div class="form-group">
                <label for="po-supplier">{{ t('purchaseOrder.supplier') }}</label>
                <input id="po-supplier" v-model="form.supplier_name" type="text" class="po-input" required />
              </div>
              <div class="form-row">
                <div class="form-group">
                  <label for="po-quantity">{{ t('purchaseOrder.quantity') }}</label>
                  <input id="po-quantity" v-model.number="form.quantity" type="number" min="1" step="1" class="po-input" required />
                </div>
                <div class="form-group">
                  <label for="po-unit-cost">{{ t('purchaseOrder.unitCost') }}</label>
                  <input id="po-unit-cost" v-model.number="form.unit_cost" type="number" min="0.01" step="0.01" class="po-input" required />
                </div>
              </div>
              <div class="form-group">
                <label for="po-date">{{ t('purchaseOrder.expectedDelivery') }}</label>
                <input id="po-date" v-model="form.expected_delivery_date" type="date" class="po-input" required />
              </div>
              <div class="form-group">
                <label for="po-notes">{{ t('purchaseOrder.notes') }}</label>
                <textarea id="po-notes" v-model="form.notes" rows="3" class="po-input"></textarea>
              </div>
              <div v-if="error" class="po-error" role="alert">{{ error }}</div>
            </form>

            <!-- View mode -->
            <div v-else class="po-view">
              <div v-if="loading" class="po-state">{{ t('common.loading') }}</div>
              <div v-else-if="error" class="po-error" role="alert">{{ error }}</div>
              <div v-else-if="po" class="info-grid">
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.supplier') }}</div>
                  <div class="info-value">{{ po.supplier_name }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.quantity') }}</div>
                  <div class="info-value">{{ po.quantity }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.unitCost') }}</div>
                  <div class="info-value">{{ formatCurrencyWithDecimals(po.unit_cost, 'USD', 2) }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.totalCost') }}</div>
                  <div class="info-value">{{ formatCurrencyWithDecimals(po.quantity * po.unit_cost, 'USD', 2) }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.expectedDelivery') }}</div>
                  <div class="info-value">{{ po.expected_delivery_date }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.notes') }}</div>
                  <div class="info-value">{{ po.notes || '-' }}</div>
                </div>
              </div>
            </div>
          </div>

          <div class="modal-footer">
            <button type="button" class="btn-secondary" @click="close">{{ t('common.close') }}</button>
            <button v-if="mode === 'create'" type="submit" form="po-form" class="btn-primary" :disabled="submitting">
              {{ submitting ? t('purchaseOrder.submitting') : t('purchaseOrder.submit') }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, watch } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'
import { formatCurrencyWithDecimals } from '../utils/currency'

const { t, translateProductName } = useI18n()

const props = defineProps({
  isOpen: { type: Boolean, required: true },
  backlogItem: { type: Object, default: null },
  mode: { type: String, default: 'create', validator: (v) => ['create', 'view'].includes(v) }
})
const emit = defineEmits(['close', 'po-created'])

const form = ref({})
const po = ref(null)
const error = ref('')
const loading = ref(false)
const submitting = ref(false)

const resetForm = () => {
  const item = props.backlogItem
  // Default to the open shortage; clamp to 1 so the min-1 rule always holds.
  const shortage = item ? Math.max(1, item.quantity_needed - item.quantity_available) : 1
  form.value = { supplier_name: '', quantity: shortage, unit_cost: null, expected_delivery_date: '', notes: '' }
}

const loadPO = async () => {
  if (props.backlogItem.purchase_order) {
    po.value = props.backlogItem.purchase_order
    return
  }
  loading.value = true
  try {
    po.value = await api.getPurchaseOrderByBacklogItem(props.backlogItem.id)
  } catch (err) {
    console.error('Failed to load purchase order:', err)
    error.value = t('purchaseOrder.loadError')
  } finally {
    loading.value = false
  }
}

// Re-init on every open so stale input/errors/PO from a previous item never show.
watch(
  () => props.isOpen,
  (open) => {
    if (!open || !props.backlogItem) return
    error.value = ''
    po.value = null
    if (props.mode === 'view') loadPO()
    else resetForm()
  },
  { immediate: true }
)

const close = () => emit('close')

const submit = async () => {
  if (submitting.value) return
  submitting.value = true
  error.value = ''
  try {
    const created = await api.createPurchaseOrder({
      backlog_item_id: props.backlogItem.id,
      supplier_name: form.value.supplier_name.trim(),
      quantity: form.value.quantity,
      unit_cost: form.value.unit_cost,
      expected_delivery_date: form.value.expected_delivery_date,
      notes: form.value.notes.trim() || null
    })
    emit('po-created', created)
  } catch (err) {
    console.error('Failed to create purchase order:', err)
    error.value = t('purchaseOrder.createError')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-container {
  background: white;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  width: 90%;
  max-width: 560px;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem 2rem;
  border-bottom: 2px solid var(--border);
}

.modal-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--text);
  margin: 0;
}

.close-button {
  background: none;
  border: none;
  color: var(--text-sub);
  cursor: pointer;
  padding: 0.5rem;
  display: flex;
  border-radius: 6px;
  transition: all 0.2s ease;
}

.close-button:hover {
  background: var(--card-bg);
  color: var(--text);
}

.modal-body {
  padding: 2rem;
  overflow-y: auto;
  flex: 1;
}

.modal-footer {
  padding: 1.5rem 2rem;
  border-top: 2px solid var(--border);
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
}

.btn-secondary,
.btn-primary {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-secondary {
  background: var(--card-bg);
  color: var(--text-sub);
}

.btn-secondary:hover {
  background: var(--border);
}

.btn-primary {
  background: var(--val-gradient);
  color: var(--val-white);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.item-summary {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1rem 1.25rem;
  margin-bottom: 1.5rem;
}

.item-name {
  font-weight: 600;
  color: var(--text);
}

.item-meta {
  font-size: 0.875rem;
  color: var(--text-sub);
  margin-top: 0.25rem;
}

.po-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form-row {
  display: flex;
  gap: 1rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  flex: 1;
}

label {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-sub);
}

.po-input {
  padding: 0.75rem;
  border: 2px solid var(--border);
  border-radius: 8px;
  font-size: 0.95rem;
  font-family: inherit;
  color: var(--text);
  transition: border-color 0.2s ease;
}

.po-input:focus {
  outline: none;
  border-color: var(--val-blue);
}

.po-error {
  color: var(--val-coral);
  font-size: 0.875rem;
  font-weight: 600;
}

.po-state {
  color: var(--text-sub);
  text-align: center;
  padding: 1.5rem;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
}

.info-label {
  font-size: 0.813rem;
  font-weight: 600;
  color: var(--text-sub);
  margin-bottom: 0.25rem;
}

.info-value {
  color: var(--text);
  overflow-wrap: anywhere;
}

/* Modal transitions */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s ease;
}

.modal-enter-active .modal-container,
.modal-leave-active .modal-container {
  transition: transform 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .modal-container,
.modal-leave-to .modal-container {
  transform: scale(0.9);
}
</style>
