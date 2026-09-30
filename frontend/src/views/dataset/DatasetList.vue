<template>
  <div class="page">
    <h2 class="page-title">数据集</h2>
    <el-table :data="rows" border>
      <el-table-column prop="name" label="名称" />
      <el-table-column prop="sample_count" label="样本数" width="100" />
      <el-table-column prop="start_time" label="开始" min-width="160" />
      <el-table-column prop="end_time" label="结束" min-width="160" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">{{ statusText[row.status] }}</template>
      </el-table-column>
      <el-table-column label="操作" width="180">
        <template #default="{ row }">
          <el-button link type="primary" @click="$router.push(`/datasets/${row.id}`)">预览</el-button>
          <el-button link type="primary" @click="$router.push(`/analysis/${row.id}`)">分析</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import http from "../../api/http";

const rows = ref([]);
const statusText = { draft: "草稿", published: "已发布", disabled: "已停用" };

onMounted(async () => {
  const { data } = await http.get("/api/datasets/");
  rows.value = data.data.results;
});
</script>
