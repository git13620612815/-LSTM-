<template>
  <div ref="box" class="chart"></div>
</template>

<script setup>
import * as echarts from "echarts";
import { onBeforeUnmount, onMounted, ref, watch } from "vue";

const props = defineProps({
  labels: { type: Array, default: () => [] },
  values: { type: Array, default: () => [] },
  series: { type: Array, default: null },
  kind: { type: String, default: "line" },
  yName: { type: String, default: "负荷(MW)" },
});

const box = ref();
let chart;

function render() {
  if (!chart) return;
  const series = props.series || [{ name: props.yName, type: props.kind, data: props.values, smooth: true }];
  chart.setOption(
    {
      tooltip: { trigger: "axis" },
      legend: { top: 0 },
      grid: { left: 48, right: 16, top: 36, bottom: 48 },
      xAxis: { type: "category", data: props.labels, axisLabel: { hideOverlap: true } },
      yAxis: { type: "value", name: props.yName },
      series,
    },
    true
  );
}

function onResize() {
  chart && chart.resize();
}

onMounted(() => {
  chart = echarts.init(box.value);
  render();
  window.addEventListener("resize", onResize);
});

watch(() => [props.labels, props.values, props.series, props.kind], render, { deep: true });

onBeforeUnmount(() => {
  window.removeEventListener("resize", onResize);
  chart && chart.dispose();
});
</script>
