import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: () => import('@/components/AppLayout.vue'),
      children: [
        {
          path: '',
          name: 'bookcase',
          component: () => import('@/views/BookcaseView.vue'),
          meta: { title: '书架' },
        },
        {
          path: 'search',
          name: 'search',
          component: () => import('@/views/SearchView.vue'),
          meta: { title: '搜索' },
        },
        {
          path: 'import',
          name: 'import',
          component: () => import('@/views/ImportView.vue'),
          meta: { title: '导入书籍' },
        },
        {
          path: 'sources',
          name: 'sources',
          component: () => import('@/views/SourceView.vue'),
          meta: { title: '书源管理' },
        },
        {
          path: 'logs',
          name: 'logs',
          component: () => import('@/views/LogsView.vue'),
          meta: { title: '系统日志' },
        },
        {
          path: 'settings',
          name: 'settings',
          component: () => import('@/views/SettingsView.vue'),
          meta: { title: '设置' },
        },
      ],
    },
    {
      path: '/book-detail',
      name: 'book-detail',
      component: () => import('@/views/BookDetailView.vue'),
      meta: { title: '书籍详情' },
    },
    {
      path: '/read/:book/:chapter?',
      name: 'read',
      component: () => import('@/views/ReadView.vue'),
      meta: { title: '阅读' },
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
  ],
})

router.afterEach((to) => {
  const title = to.meta?.title
  if (title) {
    document.title = `${title} · 阅读`
  }
})

export default router