<!-- ============================================================
 云途 AI 行程规划 - 登录/注册页面
 统一项目视觉风格：渐变背景 + 毛玻璃卡片 + 主题按钮
============================================================ -->
<script setup lang="ts">
import { ref, reactive } from "vue";
import { register, login } from "../stores/auth";
import type { UserRegisterRequest, UserLoginRequest } from "../types";

const activeTab = ref<"login" | "register">("login");
const loading = ref(false);
const errorMsg = ref("");

const loginForm = reactive<UserLoginRequest>({
  username: "",
  password: "",
});

const registerForm = reactive<UserRegisterRequest>({
  username: "",
  email: "",
  password: "",
});

async function handleLogin() {
  errorMsg.value = "";
  if (!loginForm.username || !loginForm.password) {
    errorMsg.value = "请填写用户名和密码。";
    return;
  }
  loading.value = true;
  try {
    await login({ ...loginForm });
  } catch (e: unknown) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
    errorMsg.value = detail || "登录失败，请检查用户名或密码。";
  } finally {
    loading.value = false;
  }
}

async function handleRegister() {
  errorMsg.value = "";
  if (!registerForm.username || !registerForm.email || !registerForm.password) {
    errorMsg.value = "请填写所有字段。";
    return;
  }
  if (registerForm.password.length < 6) {
    errorMsg.value = "密码至少 6 位。";
    return;
  }
  loading.value = true;
  try {
    await register({ ...registerForm });
    await login({
      username: registerForm.username,
      password: registerForm.password,
    });
  } catch (e: unknown) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
    errorMsg.value = detail || "注册失败，请稍后重试。";
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="login-shell">
    <div class="login-shell__glow login-shell__glow--left"></div>
    <div class="login-shell__glow login-shell__glow--right"></div>

    <div class="login-card">
      <div class="login-brand">
        <div class="login-brand__badge">Trip Planner</div>
        <h1 class="login-brand__title">云途 AI 行程规划助手</h1>
        <p class="login-brand__sub">AI 驱动 · 智能旅行规划</p>
      </div>

      <!-- Tab Switcher -->
      <div class="login-tabs">
        <button
          :class="['login-tab', { 'login-tab--active': activeTab === 'login' }]"
          @click="activeTab = 'login'"
        >
          登录
        </button>
        <button
          :class="['login-tab', { 'login-tab--active': activeTab === 'register' }]"
          @click="activeTab = 'register'"
        >
          注册
        </button>
      </div>

      <!-- Error Alert -->
      <div v-if="errorMsg" class="login-error">
        <span class="login-error__icon">!</span>
        {{ errorMsg }}
      </div>

      <!-- Login Form -->
      <form v-if="activeTab === 'login'" class="login-form" @submit.prevent="handleLogin">
        <label class="login-label">用户名</label>
        <input
          v-model="loginForm.username"
          class="login-input"
          placeholder="请输入用户名"
          autocomplete="username"
        />

        <label class="login-label">密码</label>
        <input
          v-model="loginForm.password"
          class="login-input"
          type="password"
          placeholder="请输入密码"
          autocomplete="current-password"
          @keydown.enter="handleLogin"
        />

        <button type="submit" class="login-submit" :disabled="loading">
          {{ loading ? "登录中..." : "登录" }}
        </button>
      </form>

      <!-- Register Form -->
      <form v-else class="login-form" @submit.prevent="handleRegister">
        <label class="login-label">用户名</label>
        <input
          v-model="registerForm.username"
          class="login-input"
          placeholder="3~50 个字符"
          autocomplete="username"
        />

        <label class="login-label">邮箱</label>
        <input
          v-model="registerForm.email"
          class="login-input"
          type="email"
          placeholder="请输入邮箱"
          autocomplete="email"
        />

        <label class="login-label">密码</label>
        <input
          v-model="registerForm.password"
          class="login-input"
          type="password"
          placeholder="至少 6 位"
          autocomplete="new-password"
          @keydown.enter="handleRegister"
        />

        <button type="submit" class="login-submit" :disabled="loading">
          {{ loading ? "注册中..." : "注册并登录" }}
        </button>
      </form>
    </div>
  </div>
</template>

<style scoped>
.login-shell {
  position: relative;
  display: grid;
  place-items: center;
  min-height: 100vh;
  padding: 24px;
  background:
    radial-gradient(circle at top left, rgba(191, 219, 254, 0.55), transparent 30%),
    radial-gradient(circle at right 18%, rgba(147, 197, 253, 0.35), transparent 22%),
    linear-gradient(180deg, #eff6ff 0%, #ecf3fb 100%);
  overflow: hidden;
}

.login-shell__glow {
  position: absolute;
  width: 360px;
  height: 360px;
  border-radius: 50%;
  filter: blur(28px);
  opacity: 0.45;
  pointer-events: none;
}

.login-shell__glow--left {
  top: -120px;
  left: -100px;
  background: rgba(59, 130, 246, 0.4);
}

.login-shell__glow--right {
  right: -90px;
  bottom: 100px;
  background: rgba(37, 99, 235, 0.25);
}

.login-card {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 420px;
  padding: 36px 32px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 24px 60px rgba(98, 116, 164, 0.14);
  backdrop-filter: blur(16px);
}

.login-brand {
  text-align: center;
  margin-bottom: 24px;
}

.login-brand__badge {
  display: inline-flex;
  align-items: center;
  padding: 6px 14px;
  border-radius: 999px;
  background: rgba(59, 130, 246, 0.1);
  color: #2563eb;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.04em;
}

.login-brand__title {
  margin: 12px 0 6px;
  font-size: 28px;
  font-weight: 800;
  background: linear-gradient(135deg, #3b82f6, #1d4ed8);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.login-brand__sub {
  margin: 0;
  color: #8a94a6;
  font-size: 13px;
}

.login-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
  padding: 6px;
  border-radius: 14px;
  background: rgba(59, 130, 246, 0.06);
}

.login-tab {
  flex: 1;
  border: none;
  border-radius: 10px;
  padding: 10px;
  background: transparent;
  color: #667085;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.login-tab--active {
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  color: #fff;
}

.login-error {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  padding: 10px 14px;
  border-radius: 12px;
  background: rgba(239, 68, 68, 0.08);
  color: #dc2626;
  font-size: 13px;
  font-weight: 600;
}

.login-error__icon {
  display: inline-grid;
  place-items: center;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #ef4444;
  color: #fff;
  font-size: 12px;
  font-weight: 800;
}

.login-form {
  display: grid;
  gap: 6px;
}

.login-label {
  display: block;
  color: #465467;
  font-size: 13px;
  font-weight: 700;
  margin-top: 10px;
}

.login-input {
  margin-top: 6px;
  width: 100%;
  height: 44px;
  border: 1px solid rgba(98, 116, 164, 0.18);
  border-radius: 12px;
  padding: 0 14px;
  background: #fbfcff;
  color: #334155;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
  box-sizing: border-box;
}

.login-input:focus {
  border-color: rgba(59, 130, 246, 0.65);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.login-submit {
  margin-top: 20px;
  width: 100%;
  height: 48px;
  border: none;
  border-radius: 14px;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: #fff;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 12px 28px rgba(59, 130, 246, 0.25);
  transition: opacity 0.2s, transform 0.15s;
}

.login-submit:hover {
  transform: translateY(-1px);
  box-shadow: 0 16px 32px rgba(59, 130, 246, 0.3);
}

.login-submit:disabled {
  opacity: 0.7;
  cursor: wait;
  transform: none;
}
</style>