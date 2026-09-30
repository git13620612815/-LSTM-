<template>
  <div class="page">
    <h2 class="page-title">负荷预测</h2>
    <el-alert v-if="model" :title="model.message" :type="model.ready ? 'success' : 'warning'" show-icon style="margin-bottom: 12px">
      <template v-if="model.metrics">验证集 MAE {{ model.metrics.mae }}，RMSE {{ model.metrics.rmse }}，MAPE {{ model.metrics.mape }}%</template>
    </el-alert>
    <el-tabs v-model="tab">
      <el-tab-pane label="单次预测" name="single">
        <el-radio-group v-model="mode" style="margin-bottom: 12px">
          <el-radio-button value="dataset">从数据集选取</el-radio-button>
          <el-radio-button value="manual">手工录入</el-radio-button>
        </el-radio-group>
        <div v-if="mode === 'dataset'" class="toolbar">
          <el-select v-model="datasetId" placeholder="已发布数据集" style="width: 240px" @change="fillEnd">
            <el-option v-for="item in datasets" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
          <el-date-picker v-model="endTime" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" placeholder="历史窗口结束时刻" />
          <el-button type="primary" :loading="loading" @click="predictDataset">预测下一小时</el-button>
        </div>
        <div v-else>
          <el-date-picker v-model="startTime" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" placeholder="起始时刻" />
          <el-input v-model="loadsText" type="textarea" :rows="8" placeholder="按时间顺序填写 24 个负荷值，每行一个" style="margin: 12px 0" />
          <el-button type="primary" :loading="loading" @click="predictManual">预测下一小时</el-button>
        </div>
      </el-tab-pane>
      <el-tab-pane label="批量预测" name="batch">
        <el-upload :auto-upload="false" :limit="1" accept=".csv" :on-change="onFile">
          <el-button>选择 CSV</el-button>
        </el-upload>
        <el-button type="primary" style="margin-top: 12px" :loading="loading" @click="predictBatch">开始批量预测</el-button>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import http from "../../api/http";

const router = useRouter();
const tab = ref("single");
const mode = ref("dataset");
const model = ref(null);
const datasets = ref([]);
const datasetId = ref();
const endTime = ref("");
const startTime = ref("");
const loadsText = ref("");
const file = ref(null);
const loading = ref(false);

function fillEnd() {
  const found = datasets.value.find((item) => item.id === datasetId.value);
  endTime.value = found?.end_time || "";
}

function onFile(upload) {
  file.value = upload.raw;
}

async function predictDataset() {
  loading.value = true;
  try {
    const { data } = await http.post("/api/forecast/single/", { dataset_id: datasetId.value, end_time: endTime.value });
    router.push(`/forecast/tasks/${data.data.task_id}`);
  } finally {
    loading.value = false;
  }
}

async function predictManual() {
  const loads = loadsText.value.split(/\n+/).map((item) => item.trim()).filter(Boolean);
  const start = new Date(startTime.value.replace(/-/g, "/"));
  const points = loads.map((load, index) => {
    const time = new Date(start.getTime() + index * 3600 * 1000);
    const pad = (n) => String(n).padStart(2, "0");
    const timestamp = `${time.getFullYear()}-${pad(time.getMonth() + 1)}-${pad(time.getDate())} ${pad(time.getHours())}:00:00`;
    return { timestamp, load_mw: Number(load), is_holiday: 0 };
  });
  loading.value = true;
  try {
    const { data } = await http.post("/api/forecast/single/", { points });
    router.push(`/forecast/tasks/${data.data.task_id}`);
  } finally {
    loading.value = false;
  }
}

async function predictBatch() {
  const body = new FormData();
  body.append("file", file.value);
  loading.value = true;
  try {
    const { data } = await http.post("/api/forecast/batch/", body);
    router.push(`/forecast/tasks/${data.data.task_id}`);
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  const status = await http.get("/api/forecast/model/");
  model.value = status.data.data;
  const list = await http.get("/api/datasets/", { params: { status: "published" } });
  datasets.value = list.data.data.results.filter((item) => item.status === "published");
});
</script>
