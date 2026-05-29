<!-- ============================================================
 云途 AI 行程规划 - 根组件
 带鉴权的 tab 导航 + 渐变 Hero 头部
============================================================ -->
<script setup lang="ts">
import { ref } from "vue";
import { currentUser, isLoggedIn, logout } from "./stores/auth";
import type { Itinerary } from "./types";
import History from "./views/History.vue";
import Home from "./views/Home.vue";
import Result from "./views/Result.vue";
import Login from "./views/Login.vue";

const currentView = ref<"home" | "result" | "history">("home");
const latestItinerary = ref<Itinerary | null>(null);

function handleGenerated(itinerary: Itinerary) {
  latestItinerary.value = itinerary;
  currentView.value = "result";
}

function openTrip(itinerary: Itinerary) {
  latestItinerary.value = itinerary;
  currentView.value = "result";
}

function updateCurrentItinerary(itinerary: Itinerary) {
  latestItinerary.value = itinerary;
  currentView.value = "result";
}
</script>

<template>
  <!-- 未登录 → 登录页 -->
  <Login v-if="!isLoggedIn" />

  <div v-else class="app-shell">
    <div class="app-shell__glow app-shell__glow--left"></div>
    <div class="app-shell__glow app-shell__glow--right"></div>

    <header class="hero">
      <div class="hero__topbar">
        <div class="hero__user" v-if="isLoggedIn">
          <span class="hero__username">{{ currentUser?.username }}</span>
          <button class="logout-btn" @click="logout">退出</button>
        </div>
      </div>

      <div class="hero__brand">
        <div class="hero__badge">Trip Planner</div>
        <h1 class="hero__title">云途 AI 行程规划助手</h1>
      </div>

      <nav class="hero__tabs">
        <button
          :class="['hero__tab', { 'hero__tab--active': currentView === 'home' }]"
          @click="currentView = 'home'"
        >规划页</button>
        <button
          :class="['hero__tab', { 'hero__tab--active': currentView === 'result' }, { 'hero__tab--disabled': !latestItinerary }]"
          :disabled="!latestItinerary"
          @click="currentView = 'result'"
        >结果页</button>
        <button
          :class="['hero__tab', { 'hero__tab--active': currentView === 'history' }]"
          @click="currentView = 'history'"
        >历史列表</button>
      </nav>
    </header>

    <main class="page-content">
      <Home v-if="currentView === 'home'" @generated="handleGenerated" />
      <Result
        v-else-if="currentView === 'result'"
        :itinerary="latestItinerary"
        @back-home="currentView = 'home'"
        @view-history="currentView = 'history'"
        @updated="updateCurrentItinerary"
      />
      <History
        v-else
        :active="currentView === 'history'"
        @open-trip="openTrip"
      />
    </main>
  </div>
</template>

<style scoped>
:global(body) {
  margin: 0;
  min-width: 320px;
  font-family: "Microsoft YaHei", "PingFang SC", "Segoe UI", sans-serif;
  background:
    radial-gradient(circle at top left, rgba(191, 219, 254, 0.55), transparent 30%),
    radial-gradient(circle at right 18%, rgba(147, 197, 253, 0.35), transparent 22%),
    linear-gradient(180deg, #eff6ff 0%, #ecf3fb 100%);
  color: #1e293b;
}

:global(*) {
  box-sizing: border-box;
}

.app-shell {
  position: relative;
  min-height: 100vh;
  padding: 40px 24px 64px;
  overflow: hidden;
}

.app-shell__glow {
  position: absolute;
  width: 360px;
  height: 360px;
  border-radius: 50%;
  filter: blur(28px);
  opacity: 0.45;
  pointer-events: none;
}

.app-shell__glow--left {
  top: -120px;
  left: -100px;
  background: rgba(59, 130, 246, 0.4);
}

.app-shell__glow--right {
  right: -90px;
  bottom: 100px;
  background: rgba(37, 99, 235, 0.25);
}

/* ========== Hero ========== */
.hero {
  position: relative;
  z-index: 1;
  max-width: 1280px;
  margin: 0 auto 28px;
}

.hero::before {
  content: "";
  position: absolute;
  inset: -28px 0 auto;
  height: 210px;
  z-index: -1;
  border-radius: 36px;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 40%, #1d4ed8 100%);
  box-shadow: 0 28px 72px rgba(37, 99, 235, 0.28);
}

/* Top bar — user info right-aligned */
.hero__topbar {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  padding: 4px 16px 0;
}

.hero__user {
  display: flex;
  align-items: center;
  gap: 12px;
}

.hero__username {
  color: rgba(255, 255, 255, 0.9);
  font-size: 14px;
  font-weight: 600;
}

.logout-btn {
  border: 1px solid rgba(255, 255, 255, 0.45);
  border-radius: 8px;
  padding: 4px 14px;
  background: transparent;
  color: rgba(255, 255, 255, 0.85);
  font-size: 13px;
  cursor: pointer;
  transition: background 0.2s;
}
.logout-btn:hover {
  background: rgba(255, 255, 255, 0.18);
}

/* Brand area — centered badge + title */
.hero__brand {
  text-align: center;
  padding-top: 8px;
}

.hero__badge {
  display: inline-flex;
  align-items: center;
  padding: 6px 16px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.82);
  color: #2563eb;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.05em;
  box-shadow: 0 8px 24px rgba(37, 99, 235, 0.12);
}

.hero__title {
  margin: 14px 0 0;
  color: #fff;
  font-size: 44px;
  font-weight: 800;
  line-height: 1.15;
  letter-spacing: 0.02em;
}

/* Tabs */
.hero__tabs {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin-top: 22px;
  padding: 8px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.16);
  backdrop-filter: blur(12px);
}

.hero__tab {
  border: none;
  border-radius: 12px;
  padding: 10px 28px;
  background: transparent;
  color: rgba(255, 255, 255, 0.8);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}
.hero__tab:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.1);
}

.hero__tab--active {
  background: rgba(255, 255, 255, 0.94);
  color: #2563eb;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.06);
}

.hero__tab--disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* Content */
.page-content {
  position: relative;
  z-index: 1;
  max-width: 1280px;
  margin: 0 auto;
}

/* Responsive */
@media (max-width: 768px) {
  .app-shell {
    padding: 20px 12px 36px;
  }
  .hero__title {
    font-size: 30px;
  }
  .hero::before {
    inset: -18px 0 auto;
    height: 200px;
  }
  .hero__tab {
    padding: 8px 18px;
    font-size: 13px;
  }
}
</style>