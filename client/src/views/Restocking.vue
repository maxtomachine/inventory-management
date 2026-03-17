<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <!-- Budget Slider Card -->
    <div class="card budget-card">
      <div class="card-header">
        <h3 class="card-title">{{ t('restocking.budget') }}</h3>
      </div>
      <div class="budget-control">
        <div class="budget-display">
          <span class="budget-value">{{ currencySymbol }}{{ budget.toLocaleString() }}</span>
        </div>
        <div class="slider-wrapper">
          <input
            v-model.number="budget"
            type="range"
            min="5000"
            max="100000"
            step="1000"
            class="budget-slider"
          />
          <div class="slider-labels">
            <span>{{ currencySymbol }}5,000</span>
            <span>{{ currencySymbol }}100,000</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Success Banner -->
    <div v-if="orderSuccess" class="success-banner">
      <div class="success-content">
        <span class="success-icon">&#10003;</span>
        <span>{{ t('restocking.orderSuccess') }} &mdash; {{ t('restocking.orderNumber') }}: <strong>{{ successOrderNumber }}</strong></span>
      </div>
      <button class="dismiss-btn" @click="orderSuccess = false">&times;</button>
    </div>

    <!-- Recommendations Card -->
    <div class="card">
      <div class="card-header">
        <h3 class="card-title">{{ t('restocking.recommendations') }}</h3>
      </div>

      <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
      <div v-else-if="error" class="error">{{ error }}</div>
      <div v-else-if="recommendations.length === 0" class="empty-state">
        {{ t('restocking.noRecommendations') }}
      </div>
      <div v-else>
        <div class="table-container">
          <table class="recommendations-table">
            <thead>
              <tr>
                <th class="col-check">
                  <input
                    type="checkbox"
                    :checked="allSelected"
                    :indeterminate.prop="someSelected && !allSelected"
                    @change="toggleAll"
                    class="row-checkbox"
                  />
                </th>
                <th>{{ t('restocking.table.itemName') }}</th>
                <th>{{ t('restocking.table.sku') }}</th>
                <th class="col-num">{{ t('restocking.table.currentDemand') }}</th>
                <th class="col-num">{{ t('restocking.table.forecastedDemand') }}</th>
                <th>{{ t('restocking.table.trend') }}</th>
                <th class="col-num">{{ t('restocking.table.recommendedQty') }}</th>
                <th class="col-num">{{ t('restocking.table.unitCost') }}</th>
                <th class="col-num">{{ t('restocking.table.lineTotal') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="item in recommendations"
                :key="item.item_sku"
                :class="{ 'row-selected': selectedSkus.has(item.item_sku) }"
              >
                <td class="col-check">
                  <input
                    type="checkbox"
                    :checked="selectedSkus.has(item.item_sku)"
                    @change="toggleItem(item.item_sku)"
                    class="row-checkbox"
                  />
                </td>
                <td><strong>{{ item.item_name }}</strong></td>
                <td class="sku-cell">{{ item.item_sku }}</td>
                <td class="col-num">{{ item.current_demand }}</td>
                <td class="col-num">{{ item.forecasted_demand }}</td>
                <td>
                  <span :class="['badge', item.trend]">
                    {{ t(`trends.${item.trend}`) }}
                  </span>
                </td>
                <td class="col-num">{{ item.recommended_qty }}</td>
                <td class="col-num">{{ currencySymbol }}{{ item.unit_cost.toLocaleString() }}</td>
                <td class="col-num line-total">{{ currencySymbol }}{{ item.line_total.toLocaleString() }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Summary Bar -->
        <div class="summary-bar">
          <div class="summary-stats">
            <div class="summary-stat">
              <span class="summary-label">{{ t('restocking.summary.selectedItems') }}</span>
              <span class="summary-value">{{ selectedCount }}</span>
            </div>
            <div class="summary-divider"></div>
            <div class="summary-stat">
              <span class="summary-label">{{ t('restocking.summary.selectedTotal') }}</span>
              <span class="summary-value">{{ currencySymbol }}{{ selectedTotal.toLocaleString() }}</span>
            </div>
            <div class="summary-divider"></div>
            <div class="summary-stat">
              <span
                class="summary-label"
                :class="{ 'over-budget-label': isOverBudget }"
              >
                {{ isOverBudget ? t('restocking.summary.overBudget') : t('restocking.summary.remainingBudget') }}
              </span>
              <span
                class="summary-value"
                :class="{ 'over-budget-value': isOverBudget }"
              >
                {{ isOverBudget ? '-' : '' }}{{ currencySymbol }}{{ Math.abs(remainingBudget).toLocaleString() }}
              </span>
            </div>
          </div>
          <button
            class="place-order-btn"
            :disabled="selectedCount === 0 || orderSubmitting"
            @click="placeOrder"
          >
            <span v-if="orderSubmitting" class="btn-spinner"></span>
            {{ orderSubmitting ? t('common.loading') : t('restocking.placeOrder') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'

export default {
  name: 'Restocking',
  setup() {
    const { t, currentCurrency } = useI18n()

    const currencySymbol = computed(() => {
      return currentCurrency.value === 'JPY' ? '¥' : '$'
    })

    const budget = ref(25000)
    const recommendations = ref([])
    const selectedSkus = ref(new Set())
    const loading = ref(false)
    const error = ref(null)
    const orderSubmitting = ref(false)
    const orderSuccess = ref(false)
    const successOrderNumber = ref('')

    let debounceTimer = null

    const loadRecommendations = async () => {
      loading.value = true
      error.value = null
      try {
        const data = await api.getRestockingRecommendations(budget.value)
        recommendations.value = data
        // Select all items by default
        selectedSkus.value = new Set(data.map(item => item.item_sku))
      } catch (err) {
        error.value = 'Failed to load recommendations: ' + err.message
      } finally {
        loading.value = false
      }
    }

    // Watch budget with 300ms debounce
    watch(budget, () => {
      clearTimeout(debounceTimer)
      debounceTimer = setTimeout(() => {
        loadRecommendations()
      }, 300)
    })

    const toggleItem = (sku) => {
      const next = new Set(selectedSkus.value)
      if (next.has(sku)) {
        next.delete(sku)
      } else {
        next.add(sku)
      }
      selectedSkus.value = next
    }

    const allSelected = computed(() => {
      return recommendations.value.length > 0 &&
        selectedSkus.value.size === recommendations.value.length
    })

    const someSelected = computed(() => {
      return selectedSkus.value.size > 0
    })

    const toggleAll = () => {
      if (allSelected.value) {
        selectedSkus.value = new Set()
      } else {
        selectedSkus.value = new Set(recommendations.value.map(item => item.item_sku))
      }
    }

    const selectedCount = computed(() => selectedSkus.value.size)

    const selectedTotal = computed(() => {
      return recommendations.value
        .filter(item => selectedSkus.value.has(item.item_sku))
        .reduce((sum, item) => sum + item.line_total, 0)
    })

    const remainingBudget = computed(() => budget.value - selectedTotal.value)

    const isOverBudget = computed(() => remainingBudget.value < 0)

    const placeOrder = async () => {
      if (selectedCount.value === 0 || orderSubmitting.value) return

      orderSubmitting.value = true
      error.value = null
      try {
        const items = recommendations.value
          .filter(item => selectedSkus.value.has(item.item_sku))
          .map(item => ({
            item_sku: item.item_sku,
            item_name: item.item_name,
            quantity: item.recommended_qty,
            unit_cost: item.unit_cost
          }))

        const result = await api.submitRestockOrder(items)
        successOrderNumber.value = result.order_number || result.id || 'N/A'
        orderSuccess.value = true
        selectedSkus.value = new Set()
        await loadRecommendations()
      } catch (err) {
        error.value = 'Failed to submit order: ' + err.message
      } finally {
        orderSubmitting.value = false
      }
    }

    onMounted(loadRecommendations)

    return {
      t,
      currencySymbol,
      budget,
      recommendations,
      selectedSkus,
      loading,
      error,
      orderSubmitting,
      orderSuccess,
      successOrderNumber,
      toggleItem,
      toggleAll,
      allSelected,
      someSelected,
      selectedCount,
      selectedTotal,
      remainingBudget,
      isOverBudget,
      placeOrder
    }
  }
}
</script>

<style scoped>
.restocking {
  padding-bottom: 2rem;
}

/* Budget Card */
.budget-card {
  margin-bottom: 1.25rem;
}

.budget-control {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1.25rem;
  padding: 1rem 0 0.5rem;
}

.budget-display {
  text-align: center;
}

.budget-value {
  font-size: 2.5rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.04em;
  font-variant-numeric: tabular-nums;
}

.slider-wrapper {
  width: 100%;
  max-width: 600px;
}

.budget-slider {
  width: 100%;
  height: 6px;
  appearance: none;
  -webkit-appearance: none;
  background: #e2e8f0;
  border-radius: 3px;
  outline: none;
  cursor: pointer;
  accent-color: #3b82f6;
  display: block;
}

.budget-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #3b82f6;
  cursor: pointer;
  border: 2px solid white;
  box-shadow: 0 0 0 2px #3b82f6, 0 2px 4px rgba(0, 0, 0, 0.15);
  transition: box-shadow 0.15s ease;
}

.budget-slider::-webkit-slider-thumb:hover {
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.3), 0 2px 4px rgba(0, 0, 0, 0.15);
}

.budget-slider::-moz-range-thumb {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #3b82f6;
  cursor: pointer;
  border: 2px solid white;
  box-shadow: 0 0 0 2px #3b82f6, 0 2px 4px rgba(0, 0, 0, 0.15);
}

.slider-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 0.5rem;
  font-size: 0.813rem;
  color: #64748b;
  font-weight: 500;
}

/* Success Banner */
.success-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #d1fae5;
  border: 1px solid #6ee7b7;
  border-radius: 8px;
  padding: 0.875rem 1.25rem;
  margin-bottom: 1.25rem;
  color: #065f46;
}

.success-content {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 0.938rem;
  font-weight: 500;
}

.success-icon {
  font-size: 1.125rem;
  font-weight: 700;
}

.dismiss-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: #065f46;
  font-size: 1.375rem;
  line-height: 1;
  padding: 0 0.25rem;
  opacity: 0.7;
  transition: opacity 0.15s;
}

.dismiss-btn:hover {
  opacity: 1;
}

/* Empty state */
.empty-state {
  text-align: center;
  padding: 3rem;
  color: #64748b;
  font-size: 0.938rem;
}

/* Table */
.recommendations-table {
  width: 100%;
  table-layout: auto;
}

.col-check {
  width: 40px;
  text-align: center;
}

.col-num {
  text-align: right;
}

.row-checkbox {
  width: 16px;
  height: 16px;
  cursor: pointer;
  accent-color: #3b82f6;
}

.sku-cell {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 0.813rem;
  color: #64748b;
}

.line-total {
  font-weight: 600;
  color: #0f172a;
}

.row-selected {
  background: #f0f7ff;
}

.row-selected:hover {
  background: #e8f1ff;
}

/* Summary Bar */
.summary-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.5rem;
  padding: 1rem 1.25rem;
  margin: 0 -1.25rem -1.25rem;
  border-top: 1px solid #e2e8f0;
  background: #f8fafc;
  border-radius: 0 0 10px 10px;
}

.summary-stats {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}

.summary-stat {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.summary-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.summary-value {
  font-size: 1.125rem;
  font-weight: 700;
  color: #0f172a;
  font-variant-numeric: tabular-nums;
}

.over-budget-label {
  color: #dc2626;
}

.over-budget-value {
  color: #dc2626;
}

.summary-divider {
  width: 1px;
  height: 36px;
  background: #e2e8f0;
  flex-shrink: 0;
}

/* Place Order Button */
.place-order-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 8px;
  padding: 0.75rem 1.5rem;
  font-size: 0.938rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s ease, opacity 0.15s ease;
  white-space: nowrap;
  flex-shrink: 0;
}

.place-order-btn:hover:not(:disabled) {
  background: #2563eb;
}

.place-order-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.btn-spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
