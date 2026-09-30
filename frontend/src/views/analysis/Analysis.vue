<template>
  <div class="page">
    <h2 class="page-title">数据分析</h2>
    <div class="cards" v-if="overview">
      <div class="stat"><span>平均负荷</span><strong>{{ overview.mean }}</strong></div>
      <div class="stat"><span>最小</span><strong>{{ overview.minimum }}</strong></div>
      <div class="stat"><span>最大</span><strong>{{ overview.maximum }}</strong></div>
      <div class="stat"><span>标准差</span><strong>{{ overview.std }}</strong></div>
    </div>
    <div class="panel" style="margin-bottom: 12px">
      <div class="toolbar">
        <el-radio-group v-model="granularity" @change="loadSeries">
          <el-radio-button value="day">按日</el-radio-button>
          <el-radio-button value="hour">按小时</el-radio-button>
        </el-radio-group>
        <span v-if="aggregated">点数过多，已按日聚合</span>
      </div>
      <SimpleChart :labels="series.labels" :values="series.values" />
    </div>
    <div class="grid-2">
      <div class="panel">
        <h3>负荷分布</h3>
        <SimpleChart :labels="dist.labels" :values="dist.values" kind="bar" y-name="样本数" />
      </div>
      <div class="panel">
        <h3>24 小时平均负荷</h3>
        <SimpleChart :labels="hour.labels" :values="hour.values" kind="bar" />
      </div>
    </div>
    <div class="panel" style="margin-top: 12px">
      <h3>星期平均负荷</h3>
      <SimpleChart :labels="week.labels" :values="week.values" kind="bar" />
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import http from "../../api/http";
import SimpleChart from "../../components/SimpleChart.vue";

const route = useRoute();
const overview = ref(null);
const series = ref({ labels: [], values: [] });
const dist = ref({ labels: [], values: [] });
const hour = ref({ labels: [], values: [] });
const week = ref({ labels: [], values: [] });
const granularity = ref("day");
const aggregated = ref(false);
const id = route.params.id;

async function loadSeries() {
  const { data } = await http.get(`/api/analysis/${id}/series/`, { params: { granularity: granularity.value } });
  series.value = data.data;
  aggregated.value = data.data.aggregated;
}

onMounted(async () => {
  const [a, b, c] = await Promise.all([
    http.get(`/api/analysis/${id}/overview/`),
    http.get(`/api/analysis/${id}/distribution/`),
    http.get(`/api/analysis/${id}/profile/`),
  ]);
  overview.value = a.data.data;
  dist.value = b.data.data;
  hour.value = c.data.data.hour;
  week.value = c.data.data.weekday;
  loadSeries();
});
</script>
