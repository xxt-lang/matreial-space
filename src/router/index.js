import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import FlowDemo from '../views/FlowDemo.vue'

const routes = [
  { path: '/', name: 'home', component: Home },
  { path: '/flow', name: 'flow', component: FlowDemo },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
