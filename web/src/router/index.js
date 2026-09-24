import { createRouter, createWebHistory } from 'vue-router'
import HomeLayout from '../views/home/HomeLayout.vue'
import WorkspaceManage from '../views/home/WorkspaceManage.vue'
import LLMConfig from '../views/home/LLMConfig.vue'
import SkillConfig from '../views/home/SkillConfig.vue'
import Work from '../views/workSpace/work.vue'
import FlowDemo from '../views/FlowDemo.vue'

const routes = [
  // 首页：左侧导航 + 子页面，默认进入工作空间管理
  {
    path: '/',
    component: HomeLayout,
    redirect: { name: 'workspace-manage' },
    children: [
      {
        path: 'workspaces',
        name: 'workspace-manage',
        component: WorkspaceManage,
        meta: { title: '工作空间管理' },
      },
      { path: 'llm', name: 'llm-config', component: LLMConfig, meta: { title: 'LLM 配置' } },
      { path: 'skill', name: 'skill-config', component: SkillConfig, meta: { title: 'Skill 配置' } },
    ],
  },
  // 画布：独立全屏页，不带首页导航；workspaceId 可选（从工作空间列表双击进入时带上）
  { path: '/workspace/:workspaceId?', name: 'canvas', component: Work },
  { path: '/flow', name: 'flow', component: FlowDemo },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
