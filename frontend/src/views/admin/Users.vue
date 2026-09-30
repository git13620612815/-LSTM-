<template>
  <div class="page">
    <h2 class="page-title">用户管理</h2>
    <div class="toolbar">
      <el-input v-model="keyword" placeholder="搜索用户名" style="width: 200px" />
      <el-button type="primary" @click="load">搜索</el-button>
      <el-button @click="openCreate">新增用户</el-button>
    </div>
    <el-table :data="rows" border>
      <el-table-column prop="username" label="用户名" />
      <el-table-column prop="phone" label="手机号" />
      <el-table-column prop="department" label="单位" />
      <el-table-column prop="role_name" label="角色" />
      <el-table-column prop="is_active" label="状态">
        <template #default="{ row }">{{ row.is_active ? "正常" : "禁用" }}</template>
      </el-table-column>
      <el-table-column label="操作" width="280">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link @click="reset(row)">重置密码</el-button>
          <el-button link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-dialog v-model="visible" :title="editing ? '编辑用户' : '新增用户'" width="460px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="用户名"><el-input v-model="form.username" :disabled="editing" /></el-form-item>
        <el-form-item v-if="!editing" label="密码"><el-input v-model="form.password" /></el-form-item>
        <el-form-item label="手机号"><el-input v-model="form.phone" /></el-form-item>
        <el-form-item label="单位"><el-input v-model="form.department" /></el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role"><el-option label="管理员" value="admin" /><el-option label="普通用户" value="user" /></el-select>
        </el-form-item>
        <el-form-item v-if="editing" label="启用"><el-switch v-model="form.is_active" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import http from "../../api/http";

const rows = ref([]);
const keyword = ref("");
const visible = ref(false);
const editing = ref(false);
const form = reactive({ id: null, username: "", password: "", phone: "", department: "", role: "user", is_active: true });

async function load() {
  const { data } = await http.get("/api/admin/users/", { params: { q: keyword.value } });
  rows.value = data.data.results;
}

function openCreate() {
  editing.value = false;
  Object.assign(form, { id: null, username: "", password: "", phone: "", department: "", role: "user", is_active: true });
  visible.value = true;
}

function openEdit(row) {
  editing.value = true;
  Object.assign(form, row);
  visible.value = true;
}

async function save() {
  if (editing.value) await http.put(`/api/admin/users/${form.id}/`, form);
  else await http.post("/api/admin/users/", form);
  visible.value = false;
  ElMessage.success("已保存");
  load();
}

async function reset(row) {
  const { data } = await http.post(`/api/admin/users/${row.id}/reset-password/`);
  ElMessageBox.alert(`临时密码：${data.data.password}`, "密码已重置");
}

async function remove(row) {
  await ElMessageBox.confirm(`确认删除用户 ${row.username}？若已有预测记录将改为禁用。`, "删除用户");
  const { data } = await http.delete(`/api/admin/users/${row.id}/`);
  ElMessage.success(data.data.disabled ? "已禁用并保留历史记录" : "已删除");
  load();
}

onMounted(load);
</script>
