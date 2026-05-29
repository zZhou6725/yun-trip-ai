// ============================================================
// 云途 AI 行程规划 - 路由配置
// App.vue 内部管理 tab 切换，路由只做最外层匹配。
// ============================================================
import { createRouter, createWebHistory } from "vue-router";
import App from "../App.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/:pathMatch(.*)*", component: App },
  ],
});

export default router;