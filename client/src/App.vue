<template>
  <div class="app shell">
    <aside class="sidebar" :class="{ collapsed }">
      <div class="sidebar-top">
        <!-- Official Anthropic wordmark, inline SVG copied from anthropic.com -->
        <div class="logo" :title="t('nav.companyName')">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 570 64" fill="none" style="height:16px;width:auto;" aria-label="Anthropic" role="img">
            <path d="M139.492 12.9945H160.265V62.9392H173.525V12.9945H194.298V1.06077H139.492V12.9945Z" fill="currentColor"/>
            <path d="M116.066 44.3757L88.221 1.06077H73.1934V62.9392H86.011V19.6243L113.856 62.9392H128.884V1.06077H116.066V44.3757Z" fill="currentColor"/>
            <path d="M247.337 25.7238H218.166V1.06077H204.906V62.9392H218.166V37.6575H247.337V62.9392H260.597V1.06077H247.337V25.7238Z" fill="currentColor"/>
            <path d="M24.663 1.06077L0 62.9392H13.7901L18.834 49.9447H44.6365L49.6796 62.9392H63.4696L38.8066 1.06077H24.663ZM23.2946 38.453L31.7348 16.7072L40.175 38.453H23.2946Z" fill="currentColor"/>
            <path d="M370.475 0C352.619 0 339.978 13.2597 339.978 32.0884C339.978 50.7403 352.619 64 370.475 64C388.243 64 400.796 50.7403 400.796 32.0884C400.796 13.2597 388.243 0 370.475 0ZM370.475 51.6243C360.044 51.6243 353.68 44.1989 353.68 32.0884C353.68 19.8011 360.044 12.3757 370.475 12.3757C380.818 12.3757 387.094 19.8011 387.094 32.0884C387.094 44.1989 380.818 51.6243 370.475 51.6243Z" fill="currentColor"/>
            <path d="M555.845 42.1657C553.547 48.1768 548.95 51.6243 542.674 51.6243C532.243 51.6243 525.878 44.1989 525.878 32.0884C525.878 19.8011 532.243 12.3757 542.674 12.3757C548.95 12.3757 553.547 15.8232 555.845 21.8343H569.901C566.453 8.57459 556.11 0 542.674 0C524.818 0 512.177 13.2597 512.177 32.0884C512.177 50.7403 524.818 64 542.674 64C556.199 64 566.541 55.337 569.989 42.1657H555.845Z" fill="currentColor"/>
            <path d="M471.337 1.06077L496 62.9392H509.525L484.862 1.06077H471.337Z" fill="currentColor"/>
            <path d="M443.403 1.06077H413.171V62.9392H426.431V40.4862H443.403C457.459 40.4862 466.033 33.0608 466.033 20.7735C466.033 8.48619 457.459 1.06077 443.403 1.06077ZM442.784 28.5525H426.431V12.9945H442.784C449.326 12.9945 452.773 15.6464 452.773 20.7735C452.773 25.9006 449.326 28.5525 442.784 28.5525Z" fill="currentColor"/>
            <path d="M329.812 19.8895C329.812 8.22099 321.238 1.06077 307.182 1.06077H276.95V62.9392H290.21V38.7182H304.971L318.232 62.9392H332.906L318.223 36.8734C325.593 34.0402 329.812 28.0743 329.812 19.8895ZM290.21 12.9945H306.564C313.105 12.9945 316.552 15.3812 316.552 19.8895C316.552 24.3978 313.105 26.7845 306.564 26.7845H290.21V12.9945Z" fill="currentColor"/>
          </svg>
        </div>
        <button
          class="collapse-toggle"
          type="button"
          :aria-label="collapsed ? 'Expand sidebar' : 'Collapse sidebar'"
          @click="collapsed = !collapsed"
        >
          <i class="ph" :class="collapsed ? 'ph-caret-double-right' : 'ph-caret-double-left'"></i>
        </button>
      </div>
      <nav class="nav-links">
        <router-link
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          :title="t(item.label)"
          :class="{ active: $route.path === item.to }"
        >
          <i class="ph" :class="item.icon"></i>
          <span class="nav-label">{{ t(item.label) }}</span>
        </router-link>
      </nav>
      <div class="sidebar-footer">
        <LanguageSwitcher />
        <ProfileMenu
          @show-profile-details="showProfileDetails = true"
          @show-tasks="showTasks = true"
        />
      </div>
    </aside>
    <div class="content-column">
      <FilterBar />
      <main class="main-content">
        <router-view />
      </main>
    </div>

    <ProfileDetailsModal
      :is-open="showProfileDetails"
      @close="showProfileDetails = false"
    />

    <TasksModal
      :is-open="showTasks"
      :tasks="tasks"
      @close="showTasks = false"
      @add-task="addTask"
      @delete-task="deleteTask"
      @toggle-task="toggleTask"
    />
  </div>
</template>

<script>
import { ref, watch, onMounted, onBeforeUnmount, computed } from 'vue'
import { api } from './api'
import { useAuth } from './composables/useAuth'
import { useI18n } from './composables/useI18n'
import FilterBar from './components/FilterBar.vue'
import ProfileMenu from './components/ProfileMenu.vue'
import ProfileDetailsModal from './components/ProfileDetailsModal.vue'
import TasksModal from './components/TasksModal.vue'
import LanguageSwitcher from './components/LanguageSwitcher.vue'

export default {
  name: 'App',
  components: {
    FilterBar,
    ProfileMenu,
    ProfileDetailsModal,
    TasksModal,
    LanguageSwitcher
  },
  setup() {
    const { currentUser } = useAuth()
    const { t } = useI18n()
    const showProfileDetails = ref(false)
    const showTasks = ref(false)
    const apiTasks = ref([])

    const navItems = [
      { to: '/', label: 'nav.overview', icon: 'ph-chart-line-up' },
      { to: '/inventory', label: 'nav.inventory', icon: 'ph-package' },
      { to: '/orders', label: 'nav.orders', icon: 'ph-shopping-cart' },
      { to: '/spending', label: 'nav.finance', icon: 'ph-currency-circle-dollar' },
      { to: '/demand', label: 'nav.demandForecast', icon: 'ph-trend-up' },
      { to: '/restocking', label: 'nav.restocking', icon: 'ph-arrow-counter-clockwise' },
      { to: '/reports', label: 'nav.reports', icon: 'ph-chart-bar' }
    ]

    // Sidebar collapse: saved choice wins; below 1024px it collapses automatically
    const narrow = window.matchMedia('(max-width: 1023px)')
    const stored = localStorage.getItem('sidebarCollapsed')
    const collapsed = ref(narrow.matches || stored === 'true')
    watch(collapsed, v => localStorage.setItem('sidebarCollapsed', String(v)))
    const onNarrow = e => { if (e.matches) collapsed.value = true }
    narrow.addEventListener('change', onNarrow)
    onBeforeUnmount(() => narrow.removeEventListener('change', onNarrow))

    // Merge mock tasks from currentUser with API tasks
    const tasks = computed(() => {
      return [...currentUser.value.tasks, ...apiTasks.value]
    })

    const loadTasks = async () => {
      try {
        apiTasks.value = await api.getTasks()
      } catch (err) {
        console.error('Failed to load tasks:', err)
      }
    }

    const addTask = async (taskData) => {
      try {
        const newTask = await api.createTask(taskData)
        // Add new task to the beginning of the array
        apiTasks.value.unshift(newTask)
      } catch (err) {
        console.error('Failed to add task:', err)
      }
    }

    const deleteTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const isMockTask = currentUser.value.tasks.some(t => t.id === taskId)

        if (isMockTask) {
          // Remove from mock tasks
          const index = currentUser.value.tasks.findIndex(t => t.id === taskId)
          if (index !== -1) {
            currentUser.value.tasks.splice(index, 1)
          }
        } else {
          // Remove from API tasks
          await api.deleteTask(taskId)
          apiTasks.value = apiTasks.value.filter(t => t.id !== taskId)
        }
      } catch (err) {
        console.error('Failed to delete task:', err)
      }
    }

    const toggleTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const mockTask = currentUser.value.tasks.find(t => t.id === taskId)

        if (mockTask) {
          // Toggle mock task status
          mockTask.status = mockTask.status === 'pending' ? 'completed' : 'pending'
        } else {
          // Toggle API task
          const updatedTask = await api.toggleTask(taskId)
          const index = apiTasks.value.findIndex(t => t.id === taskId)
          if (index !== -1) {
            apiTasks.value[index] = updatedTask
          }
        }
      } catch (err) {
        console.error('Failed to toggle task:', err)
      }
    }

    onMounted(loadTasks)

    return {
      t,
      navItems,
      collapsed,
      showProfileDetails,
      showTasks,
      tasks,
      addTask,
      deleteTask,
      toggleTask
    }
  }
}
</script>

<style>
:root {
  /* Gradient */
  --val-coral:    #ff4b4b;
  --val-peach:    #ff744f;
  --val-gradient: linear-gradient(135deg, #ff4b4b, #ff744f);

  /* Base */
  --val-black:    #100c2a;
  --val-white:    #ffffff;

  /* Secondary */
  --val-indigo:   #193773;
  --val-blue:     #3c4bc8;
  --val-purple:   #5b26b7;

  /* Tertiary */
  --val-gold:     #c0aa81;
  --val-silver:   #cdcdcd;
  --val-lavender: #a78db6;

  /* Theme-aware tokens */
  --bg:           var(--val-white);
  --text:         var(--val-black);
  --text-sub:     var(--val-indigo);
  --border:       #f0eeee;
  --card-bg:      #fafafa;

  /* Spacing scale (8px grid) */
  --sp-1:  8px;   --sp-2: 16px;  --sp-3: 24px;  --sp-4: 32px;
  --sp-6: 48px;   --sp-8: 64px;  --sp-10: 80px;

  --sidebar-w: 240px;
  --sidebar-w-collapsed: 72px;
  --shadow-card: 0 1px 3px rgba(16, 12, 42, 0.06);
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Maven Pro', sans-serif;
  font-size: 17px;
  line-height: 1.5;
  background: var(--card-bg);
  color: var(--text);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

button, input, select, textarea {
  font-family: inherit;
}

.app {
  min-height: 100vh;
}

.shell {
  display: flex;
}

.sidebar {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  width: var(--sidebar-w);
  z-index: 100;
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
  padding: var(--sp-2);
  background: var(--bg);
  border-right: 1px solid var(--border);
}

.sidebar.collapsed {
  width: var(--sidebar-w-collapsed);
}

.sidebar-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-1);
  min-height: 40px;
  padding: 0 var(--sp-1);
}

.logo {
  display: flex;
  align-items: center;
  overflow: hidden;
  min-width: 0;
  color: var(--text);
}

/* Collapsed: clip to the leading "A" glyph of the wordmark */
.sidebar.collapsed .sidebar-top {
  flex-direction: column;
  padding: 0;
}

.logo svg {
  flex-shrink: 0;
}

.sidebar.collapsed .logo {
  width: 28px;
}

.collapse-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  flex-shrink: 0;
  background: transparent;
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text-sub);
  cursor: pointer;
  font-size: 16px;
}

.collapse-toggle:hover {
  background: var(--card-bg);
}

.nav-links {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
  overflow-y: auto;
}

.nav-links a {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  color: var(--text-sub);
  text-decoration: none;
  font-weight: 500;
  font-size: 16px;
  border-radius: 8px;
  position: relative;
  transition: background 0.15s ease, color 0.15s ease;
}

.nav-links a .ph {
  font-size: 20px;
  flex-shrink: 0;
}

.nav-links a:hover {
  color: var(--text);
  background: var(--card-bg);
}

.nav-links a.active {
  color: var(--text);
  font-weight: 600;
  background: rgba(255, 75, 75, 0.08);
}

.nav-links a.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8px;
  bottom: 8px;
  width: 3px;
  border-radius: 2px;
  background: var(--val-gradient);
}

.nav-links a.active .ph {
  color: var(--val-coral);
}

.sidebar.collapsed .nav-links a {
  justify-content: center;
  padding: 10px 0;
}

.sidebar.collapsed .nav-label {
  display: none;
}

/* Collapsed footer: icon-only buttons; menus open to the right so they are not clipped */
.sidebar.collapsed .profile-button,
.sidebar.collapsed .language-button {
  justify-content: center;
  padding: 8px;
}

.sidebar.collapsed .language-label,
.sidebar.collapsed .profile-name,
.sidebar.collapsed .chevron {
  display: none;
}

.sidebar.collapsed .dropdown-menu {
  bottom: 0;
  left: calc(100% + 8px);
}

.sidebar-footer {
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
}

.content-column {
  flex: 1;
  min-width: 0;
  margin-left: var(--sidebar-w);
}

.sidebar.collapsed ~ .content-column {
  margin-left: var(--sidebar-w-collapsed);
}

.main-content {
  width: 100%;
  max-width: 100%;
  padding: var(--sp-3) var(--sp-4);
}

.page-header {
  margin-bottom: var(--sp-3);
}

.page-header h2 {
  font-size: 30px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 4px;
}

.page-header p {
  color: var(--text-sub);
  font-size: 16px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: var(--sp-2);
  margin-bottom: var(--sp-3);
}

.stat-card {
  background: var(--val-white);
  padding: var(--sp-3);
  border-radius: 12px;
  border: 1px solid var(--border);
  box-shadow: var(--shadow-card);
  transition: box-shadow 0.2s ease;
}

.stat-card:hover {
  box-shadow: 0 4px 12px rgba(16, 12, 42, 0.08);
}

.stat-label {
  color: var(--text-sub);
  font-size: 13px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: var(--sp-1);
}

.stat-value {
  font-size: 36px;
  font-weight: 600;
  line-height: 1.1;
  color: var(--text);
}

.stat-card.warning .stat-value {
  color: #ea580c;
}

.stat-card.success .stat-value {
  color: #059669;
}

.stat-card.danger .stat-value {
  color: #dc2626;
}

.stat-card.info .stat-value {
  color: #2563eb;
}

.card {
  background: var(--val-white);
  border-radius: 12px;
  padding: var(--sp-3);
  border: 1px solid var(--border);
  box-shadow: var(--shadow-card);
  margin-bottom: var(--sp-3);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--sp-2);
  padding-bottom: var(--sp-2);
  border-bottom: 1px solid var(--border);
}

.card-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text);
}

.table-container {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead {
  background: var(--card-bg);
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
}

th {
  text-align: left;
  padding: var(--sp-1) 12px;
  font-weight: 600;
  color: var(--text-sub);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

td {
  padding: var(--sp-1) 12px;
  border-top: 1px solid var(--border);
  color: var(--text);
  font-size: 14px;
}

tbody tr {
  transition: background-color 0.15s ease;
}

tbody tr:hover {
  background: var(--card-bg);
}

.badge {
  display: inline-block;
  padding: 0.313rem 0.75rem;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

.badge.success {
  background: #d1fae5;
  color: #065f46;
}

.badge.warning {
  background: #fed7aa;
  color: #92400e;
}

.badge.danger {
  background: #fecaca;
  color: #991b1b;
}

.badge.info {
  background: #dbeafe;
  color: #1e40af;
}

.badge.increasing {
  background: #d1fae5;
  color: #065f46;
}

.badge.decreasing {
  background: #fecaca;
  color: #991b1b;
}

.badge.stable {
  background: #e0e7ff;
  color: #3730a3;
}

.badge.high {
  background: #fecaca;
  color: #991b1b;
}

.badge.medium {
  background: #fed7aa;
  color: #92400e;
}

.badge.low {
  background: #dbeafe;
  color: #1e40af;
}

.loading {
  text-align: center;
  padding: 3rem;
  color: var(--text-sub);
  font-size: 0.938rem;
}

.error {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #991b1b;
  padding: 1rem;
  border-radius: 8px;
  margin: 1rem 0;
  font-size: 0.938rem;
}
</style>
