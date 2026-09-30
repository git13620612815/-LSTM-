<template>
  <div class="page">
    <h2 class="page-title">历史预测记录</h2>
    <div class="toolbar">
      <el-select v-model="query.mode" clearable placeholder="模式" style="width: 140px">
        <el-option label="单次预测" value="single" />
        <el-option label="批量预测" value="batch" />
      </el-select>
      <el-select v-model="query.status" clearable placeholder="状态" style="width: 120px">
        <el-option label="成功" value="success" />
        <el-option label="失败" value="failed" />
      </el-select>
      <el-date-picker v-model="range" type="datetimerange" value-format="YYYY-MM-DD HH:mm:ss" />
      <el-button type="primary" @click="load(1)">筛选</el-button>
      <el-button @click="download">导出</el-button>
    </div>
    <el-table :data="rows" border>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="username" label="用户" />
      <el-table-column prop="mode" label="模式">
        <template #default="{ row }">{{ row.mode === "single" ? "单次" : "批量" }}</template>
      </el-table-column>
      <el-table-column prop="status" label="状态">
        <template #default="{ row }">{{ row.status === "success" ? "成功" : "失败" }}</template>
      </el-table-column>
      <el-table-column prop="created_at" label="时间" min-width="160" />
      <el-table-column label="操作" width="100">
        <template #default="{ row }">
          <el-button link type="primary" @click="$router.push(`/forecast/tasks/${row.id}`)">查看</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination style="margin-top: 12px" layout="total, prev, pager, next" :total="total" :page-size="10" :current-page="page" @current-change="load" />
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import http from "../../api/http";

const rows = ref([]);
const total = ref(0);
const page = ref(1);
const range = ref([]);
const query = reactive({ mode: "", status: "" });

function params() {
  return {
    page: page.value,
    page_size: 10,
    mode: query.mode || undefined,
    status: query.status || undefined,
    start: range.value?.[0],
    end: range.value?.[1],
  };
}

async function load(next = page.value) {
  page.value = next;
  const { data } = await http.get("/api/forecast/tasks/", { params: params() });
  rows.value = data.data.results;
  total.value = data.data.count;
}

async function download() {
  const response = await http.get("/api/forecast/tasks/export/", { params: params(), responseType: "blob" });
  const url = URL.createObjectURL(response.data);
  const link = document.createElement("a");
  link.href = url;
  link.download = "forecast_records.csv";
  link.click();
  URL.revokeObjectURL(url);
}

onMounted(() => load(1));
</script>
