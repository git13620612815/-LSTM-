<template>
  <div class="page" v-if="task">
    <h2 class="page-title">预测结果</h2>
    <el-alert v-if="task.status === 'failed'" type="error" :title="task.error_message" show-icon />
    <div class="cards" v-else>
      <div class="stat"><span>模式</span><strong>{{ task.mode === "single" ? "单次" : "批量" }}</strong></div>
      <div class="stat"><span>MAE</span><strong>{{ task.metrics?.mae ?? "-" }}</strong></div>
      <div class="stat"><span>RMSE</span><strong>{{ task.metrics?.rmse ?? "-" }}</strong></div>
      <div class="stat"><span>MAPE(%)</span><strong>{{ task.metrics?.mape ?? "-" }}</strong></div>
    </div>
    <div class="panel" v-if="chart.labels.length">
      <SimpleChart :labels="chart.labels" :series="chart.series" />
    </div>
    <div class="panel" style="margin-top: 12px">
      <el-table :data="table" border max-height="420">
        <el-table-column prop="timestamp" label="时间" />
        <el-table-column prop="predicted_load" label="预测负荷" />
        <el-table-column prop="actual_load" label="真实负荷" />
        <el-table-column prop="kind" label="类型">
          <template #default="{ row }">{{ row.kind === "horizon" ? "未来24小时" : "单步" }}</template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import http from "../../api/http";
import SimpleChart from "../../components/SimpleChart.vue";

const route = useRoute();
const task = ref(null);
const table = ref([]);
const chart = ref({ labels: [], series: [] });

onMounted(async () => {
  const { data } = await http.get(`/api/forecast/tasks/${route.params.id}/`);
  task.value = data.data;
  table.value = data.data.points || [];
  const history = data.data.input?.history || [];
  const labels = [
    ...history.map((item) => item.timestamp),
    ...table.value.map((item) => item.timestamp),
  ];
  const unique = [...new Set(labels)];
  const historyMap = Object.fromEntries(history.map((item) => [item.timestamp, item.load_mw]));
  const predMap = Object.fromEntries(table.value.map((item) => [item.timestamp, item.predicted_load]));
  const actualMap = Object.fromEntries(table.value.filter((item) => item.actual_load != null).map((item) => [item.timestamp, item.actual_load]));
  chart.value = {
    labels: unique,
    series: [
      { name: "历史负荷", type: "line", smooth: true, data: unique.map((item) => historyMap[item] ?? null) },
      { name: "预测负荷", type: "line", smooth: true, data: unique.map((item) => predMap[item] ?? null) },
      { name: "真实负荷", type: "line", smooth: true, data: unique.map((item) => actualMap[item] ?? null) },
    ],
  };
});
</script>
