// ============================================================
// 云途 AI 行程规划 - 前端类型定义（与后端 Pydantic Schema 对齐）
// ============================================================

/** 用户注册请求 */
export interface UserRegisterRequest {
  username: string;
  email: string;
  password: string;
}

/** 用户登录请求 */
export interface UserLoginRequest {
  username: string;
  password: string;
}

/** 用户信息 */
export interface UserInfo {
  id: number;
  username: string;
  email: string;
  created_at: string | null;
}

/** 登录响应 */
export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: UserInfo;
}

/** 行程生成请求 */
export interface TripRequestPayload {
  destination: string;
  start_date: string;
  end_date: string;
  travelers: number;
  budget: number;
  preferences: string[];
  pace?: string | null;
  dietary_preferences: string[];
  hotel_level?: string | null;
  special_notes?: string | null;
}

/** 行程编辑请求 */
export interface TripEditPayload {
  trip_id: string;
  current_itinerary: Itinerary;
  user_instruction: string;
  edit_scope?: string | null;
  preserve_constraints: string[];
}

/** 景点 */
export interface SpotItem {
  name: string;
  start_time?: string | null;
  end_time?: string | null;
  description?: string | null;
  estimated_cost?: number;
  location?: string | null;
  image_url?: string | null;
  address?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  poi_id?: string | null;
}

/** 餐饮 */
export interface MealItem {
  name: string;
  meal_type: string;
  estimated_cost?: number;
  notes?: string | null;
}

/** 酒店 */
export interface HotelItem {
  name: string;
  level?: string | null;
  estimated_cost?: number;
  location?: string | null;
  address?: string | null;
  latitude?: number | null;
  longitude?: number | null;
}

/** 交通 */
export interface TransportItem {
  mode: string;
  from_place?: string | null;
  to_place?: string | null;
  estimated_cost?: number;
  duration?: string | null;
  distance_km?: number | null;
  estimated_minutes?: number | null;
}

/** 预算拆分 */
export interface BudgetBreakdown {
  transport: number;
  hotel: number;
  meals: number;
  tickets: number;
  other: number;
  total: number;
}

/** 单日行程 */
export interface DayPlan {
  day_index: number;
  date?: string | null;
  theme?: string | null;
  spots: SpotItem[];
  meals: MealItem[];
  hotel?: HotelItem | null;
  transport: TransportItem[];
  notes: string[];
}

/** 完整行程 */
export interface Itinerary {
  trip_id: string;
  destination: string;
  summary: string;
  days: DayPlan[];
  estimated_budget: number;
  budget_breakdown: BudgetBreakdown;
  tips: string[];
  source_notes: string[];
}

/** 行程保存响应 */
export interface TripSaveResponse {
  message: string;
  trip_id: string;
}

/** 行程摘要 */
export interface TripSummaryItem {
  trip_id: string;
  destination: string;
  summary: string;
  created_at?: string | null;
  updated_at?: string | null;
}

/** 行程列表 */
export interface TripListResponse {
  total: number;
  items: TripSummaryItem[];
}

/** 行程详情 */
export interface TripDetailResponse {
  trip_id: string;
  itinerary: Itinerary;
  created_at?: string | null;
  updated_at?: string | null;
}

/** 天气预报单日 */
export interface WeatherForecastDay {
  date?: string | null;
  week?: string | null;
  day_weather?: string | null;
  night_weather?: string | null;
  day_temp?: string | null;
  night_temp?: string | null;
  day_wind?: string | null;
  night_wind?: string | null;
}

/** 天气预报响应 */
export interface WeatherForecastResponse {
  city: string;
  province?: string | null;
  adcode?: string | null;
  report_time?: string | null;
  days: WeatherForecastDay[];
}
