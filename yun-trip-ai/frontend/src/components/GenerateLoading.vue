<!-- ============================================================
 云途 AI 行程规划 - 行程生成加载组件
 骨架屏 + 进度步骤动画，替代纯文本"正在生成中..."
============================================================ -->
<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";

const steps = [
  { key: "rag", title: "检索攻略数据", desc: "正在从本地攻略库中匹配最佳行程建议" },
  { key: "llm", title: "生成行程方案", desc: "AI 正在规划每日景点、餐饮与住宿安排" },
  { key: "map", title: "补全地图信息", desc: "同步高德地图坐标、路线与实景图片" },
  { key: "done", title: "整理最终结果", desc: "汇总预算、天气提示与导出文档" },
];

const activeStep = ref(0);
const elapsed = ref(0);
let timer: ReturnType<typeof setInterval> | null = null;
let timer2: ReturnType<typeof setInterval> | null = null;

// Simulate step progression based on typical LLM timing
// RAG + Embedding: ~5s, LLM: ~60-120s, Amap: ~10s, Done: final
const stepIntervals = [5000, 60000, 80000, 100000];

onMounted(() => {
  timer2 = setInterval(() => {
    elapsed.value++;
  }, 1000);

  stepIntervals.forEach((delay, index) => {
    setTimeout(() => {
      activeStep.value = index;
    }, delay);
  });
});

onUnmounted(() => {
  if (timer) clearInterval(timer);
  if (timer2) clearInterval(timer2);
});

defineExpose({ activeStep });
</script>

<template>
  <div class="loading-overlay">
    <div class="loading-card">
      <!-- header icon -->
      <div class="loading-icon">
        <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
          <circle cx="24" cy="24" r="20" stroke="rgba(59,130,246,0.3)" stroke-width="3" />
          <path
            d="M24 4a20 20 0 0 1 20 20"
            stroke="url(#grad)"
            stroke-width="3"
            stroke-linecap="round"
          />
          <defs>
            <linearGradient id="grad" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stop-color="#3b82f6" />
              <stop offset="100%" stop-color="#2563eb" />
            </linearGradient>
          </defs>
        </svg>
      </div>

      <div class="loading-title">正在生成旅行计划</div>

      <!-- progress bar -->
      <div class="progress-track">
        <div class="progress-fill" :style="{ width: `${(activeStep / (steps.length - 1)) * 100}%` }" />
      </div>

      <!-- elapsed time -->
      <div class="elapsed">
        {{ Math.floor(elapsed / 60) }}:{{ String(elapsed % 60).padStart(2, "0") }}
      </div>

      <!-- steps -->
      <div class="steps-list">
        <div
          v-for="(step, i) in steps"
          :key="step.key"
          class="step-row"
          :class="{
            'step-row--done': i < activeStep,
            'step-row--active': i === activeStep,
          }"
        >
          <div class="step-indicator">
            <span v-if="i < activeStep" class="step-check">&#10003;</span>
            <span v-else-if="i === activeStep" class="step-pulse" />
            <span v-else class="step-dot" />
          </div>
          <div class="step-text">
            <div class="step-title">{{ step.title }}</div>
            <div v-if="i <= activeStep" class="step-desc">{{ step.desc }}</div>
          </div>
        </div>
      </div>

      <!-- tip -->
      <div class="loading-tip">
        {{ activeStep < 2 ? 'AI 模型处理需要一些时间，请耐心等待' : '即将完成，正在整理最终结果' }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.loading-overlay {
  display: grid;
  place-items: center;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0); }
}

.loading-card {
  width: 100%;
  max-width: 560px;
  padding: 40px 36px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 24px 60px rgba(98, 116, 164, 0.14);
  backdrop-filter: blur(16px);
  text-align: center;
}

.loading-icon {
  margin-bottom: 16px;
  animation: spin 1.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-title {
  font-size: 20px;
  font-weight: 800;
  color: #1e3a5f;
  margin-bottom: 20px;
}

.progress-track {
  height: 6px;
  border-radius: 999px;
  background: rgba(59, 130, 246, 0.12);
  overflow: hidden;
  margin-bottom: 10px;
}

.progress-fill {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1);
}

.elapsed {
  font-size: 13px;
  color: #8a94a6;
  margin-bottom: 28px;
  font-variant-numeric: tabular-nums;
}

.steps-list {
  display: grid;
  gap: 8px;
  text-align: left;
}

.step-row {
  display: flex;
  gap: 14px;
  padding: 12px 16px;
  border-radius: 14px;
  background: rgba(98, 116, 164, 0.03);
  transition: all 0.4s ease;
}

.step-row--active {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.08), rgba(37, 99, 235, 0.08));
  border: 1px solid rgba(59, 130, 246, 0.15);
}

.step-row--done {
  opacity: 0.6;
}

.step-indicator {
  flex: 0 0 auto;
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
}

.step-check {
  color: #10b981;
  font-weight: 800;
  font-size: 16px;
}

.step-pulse {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  animation: pulse 1.2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50%      { transform: scale(1.5); opacity: 0.5; }
}

.step-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(98, 116, 164, 0.18);
}

.step-text {
  flex: 1;
}

.step-title {
  font-weight: 700;
  color: #1e3a5f;
  font-size: 14px;
  line-height: 1.5;
}

.step-desc {
  font-size: 13px;
  color: #667085;
  margin-top: 4px;
  line-height: 1.5;
}

.loading-tip {
  margin-top: 24px;
  padding: 12px;
  border-radius: 12px;
  background: rgba(59, 130, 246, 0.05);
  color: #667085;
  font-size: 13px;
}
</style>