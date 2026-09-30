<template>
  <div class="page">
    <h2 class="page-title">数据集管理</h2>
    <div class="toolbar">
      <el-button type="primary" @click="openUpload">上传数据集</el-button>
    </div>
    <el-table :data="rows" border>
      <el-table-column prop="name" label="名称" />
      <el-table-column prop="sample_count" label="样本数" width="90" />
      <el-table-column prop="status" label="状态" width="90">
        <template #default="{ row }">{{ statusText[row.status] }}</template>
      </el-table-column>
      <el-table-column prop="start_time" label="开始" min-width="150" />
      <el-table-column prop="end_time" label="结束" min-width="150" />
      <el-table-column label="操作" width="360">
        <template #default="{ row }">
          <el-button link @click="publish(row, 'published')">发布</el-button>
          <el-button link @click="publish(row, 'disabled')">停用</el-button>
          <el-button link type="primary" :loading="trainingId === row.id" @click="train(row)">训练</el-button>
          <el-button link type="primary" @click="pick(row)">重新导入</el-button>
          <el-button link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-dialog v-model="visible" title="上传数据集" width="460px">
      <el-form label-width="80px">
        <el-form-item label="名称"><el-input v-model="name" /></el-form-item>
        <el-form-item label="说明"><el-input v-model="description" /></el-form-item>
        <el-form-item label="文件"><input type="file" accept=".csv" @change="onFile" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="upload">上传</el-button>
      </template>
    </el-dialog>
    <input ref="reimportInput" type="file" accept=".csv" hidden @change="reimport" />
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import http from "../../api/http";

const rows = ref([]);
const visible = ref(false);
const name = ref("");
const description = ref("");
const file = ref(null);
const current = ref(null);
const trainingId = ref(null);
const reimportInput = ref();
const statusText = { draft: "草稿", published: "已发布", disabled: "已停用" };

async function load() {
  const { data } = await http.get("/api/datasets/");
  rows.value = data.data.results;
}

function openUpload() {
  name.value = "";
  description.value = "";
  file.value = null;
  visible.value = true;
}

function onFile(event) {
  file.value = event.target.files[0];
}

async function upload() {
  const body = new FormData();
  body.append("name", name.value);
  body.append("description", description.value);
  body.append("file", file.value);
  await http.post("/api/admin/datasets/upload/", body);
  visible.value = false;
  ElMessage.success("已导入为草稿");
  load();
}

async function train(row) {
  await ElMessageBox.confirm(`使用「${row.name}」训练 LSTM？这会覆盖当前模型。`, "训练模型");
  trainingId.value = row.id;
  try {
    const { data } = await http.post(`/api/admin/datasets/${row.id}/train/`, null, { timeout: 300000 });
    const score = data.data;
    ElMessage.success(`训练完成，MAE ${score.mae}，RMSE ${score.rmse}，MAPE ${score.mape}%`);
  } finally {
    trainingId.value = null;
  }
}

async function publish(row, status) {
  await http.put(`/api/admin/datasets/${row.id}/`, { status });
  ElMessage.success("状态已更新");
  load();
}

function pick(row) {
  current.value = row;
  reimportInput.value.click();
}

async function reimport(event) {
  const selected = event.target.files[0];
  const body = new FormData();
  body.append("file", selected);
  await http.post(`/api/admin/datasets/${current.value.id}/reimport/`, body);
  ElMessage.success("已重新导入");
  event.target.value = "";
  load();
}

async function remove(row) {
  await ElMessageBox.confirm(`删除数据集 ${row.name}？`, "删除");
  await http.delete(`/api/admin/datasets/${row.id}/`);
  load();
}

onMounted(load);
</script>
