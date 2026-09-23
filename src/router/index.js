import { createRouter, createWebHistory } from 'vue-router'
import Work from '../views/workSpace/work.vue'
import Home from '../views/Home.vue'
import FlowDemo from '../views/FlowDemo.vue'

const routes = [
  // 项目主页面：工作区画布
  { path: '/', name: 'workspace', component: Work },
  { path: '/home', name: 'home', component: Home },
  { path: '/flow', name: 'flow', component: FlowDemo },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
