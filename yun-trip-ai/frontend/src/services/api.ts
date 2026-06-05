// ============================================================
// 云途 AI 行程规划 - API 服务层
// 基于 axios 封装，自动注入 JWT Token，过期时跳转登录页。
// ============================================================

import axios from "axios";
import type { AxiosInstance, InternalAxiosRequestConfig } from "axios";
import type {
  Itinerary,
  TripDetailResponse,
  TripEditPayload,
  TripListResponse,
  TripRequestPayload,
  TripSaveResponse,
  WeatherForecastResponse,
} from "../types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

const api: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 300000,
  headers: { "Content-Type": "application/json" },
});

// ---------- 请求拦截器：自动注入 Bearer Token ----------
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem("access_token");
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ---------- 响应拦截器：401 时清除 Token 并跳转登录页 ----------
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("user_info");
      window.location.reload();
    }
    return Promise.reject(error);
  }
);

// ---------- 行程相关 ----------
export async function generateTrip(payload: TripRequestPayload): Promise<Itinerary> {
  const response = await api.post<Itinerary>("/trip/generate", payload);
  return response.data;
}

export async function editTrip(payload: TripEditPayload): Promise<Itinerary> {
  const response = await api.post<Itinerary>("/trip/edit", payload);
  return response.data;
}

export async function saveTrip(itinerary: Itinerary): Promise<TripSaveResponse> {
  const response = await api.post<TripSaveResponse>("/trip/save", {
    trip_id: itinerary.trip_id,
    itinerary,
  });
  return response.data;
}

export async function listTrips(): Promise<TripListResponse> {
  const response = await api.get<TripListResponse>("/trip");
  return response.data;
}

export async function getTripDetail(tripId: string): Promise<TripDetailResponse> {
  const response = await api.get<TripDetailResponse>(`/trip/${tripId}`);
  return response.data;
}

export async function deleteTrip(tripId: string): Promise<{ message: string; trip_id: string }> {
  const response = await api.delete<{ message: string; trip_id: string }>(`/trip/${encodeURIComponent(tripId)}`);
  return response.data;
}

// ---------- 天气 ----------
export async function fetchWeatherForecast(city: string): Promise<WeatherForecastResponse> {
  const response = await api.get<WeatherForecastResponse>("/weather/forecast", {
    params: { city },
  });
  return response.data;
}

// ---------- 导出 ----------
export async function fetchMarkdownExport(tripId: string): Promise<Blob> {
  const response = await api.get(`/export/${encodeURIComponent(tripId)}/markdown`, {
    responseType: "blob",
  });
  return response.data;
}

export async function fetchPdfExport(tripId: string): Promise<Blob> {
  const response = await api.get(`/export/${encodeURIComponent(tripId)}/pdf`, {
    responseType: "blob",
  });
  return response.data;
}

export default api;
