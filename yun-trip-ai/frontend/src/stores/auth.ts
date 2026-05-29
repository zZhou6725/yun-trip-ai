// ============================================================
// 云途 AI 行程规划 - 用户认证状态管理
// ============================================================
// 使用 Vue 响应式 API 管理登录状态，Token 持久化在 localStorage。
// ============================================================

import { reactive, computed } from "vue";
import api from "../services/api";
import type { TokenResponse, UserInfo, UserLoginRequest, UserRegisterRequest } from "../types";

// ---------- 响应式状态 ----------
const state = reactive({
  token: (localStorage.getItem("access_token") || "") as string,
  user: (() => {
    try {
      const raw = localStorage.getItem("user_info");
      return raw ? (JSON.parse(raw) as UserInfo) : null;
    } catch {
      return null;
    }
  })(),
});

// ---------- 计算属性 ----------
export const isLoggedIn = computed(() => !!state.token);
export const currentUser = computed(() => state.user);

// ---------- 保存到本地存储 ----------
function persist(token: string, user: UserInfo) {
  state.token = token;
  state.user = user;
  localStorage.setItem("access_token", token);
  localStorage.setItem("user_info", JSON.stringify(user));
}

// ---------- 清除状态 ----------
function clear() {
  state.token = "";
  state.user = null;
  localStorage.removeItem("access_token");
  localStorage.removeItem("user_info");
}

// ---------- 注册 ----------
export async function register(data: UserRegisterRequest): Promise<UserInfo> {
  const res = await api.post("/user/register", data);
  return res.data as UserInfo;
}

// ---------- 登录 ----------
export async function login(data: UserLoginRequest): Promise<TokenResponse> {
  const res = await api.post("/user/login", data);
  const result = res.data as TokenResponse;
  persist(result.access_token, result.user);
  return result;
}

// ---------- 登出 ----------
export function logout() {
  clear();
  window.location.reload();
}