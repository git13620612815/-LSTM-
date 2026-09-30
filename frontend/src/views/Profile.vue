<template>
  <div class="page">
    <h2 class="page-title">个人中心</h2>
    <el-alert v-if="store.mustChangePassword" type="warning" title="管理员已重置密码，请先修改密码" show-icon style="margin-bottom: 12px" />
    <el-tabs v-model="tab">
      <el-tab-pane label="资料" name="profile">
        <el-form :model="profile" label-width="80px" style="max-width: 460px">
          <el-form-item label="用户名"><el-input :model-value="profile.username" disabled /></el-form-item>
          <el-form-item label="手机号"><el-input v-model="profile.phone" /></el-form-item>
          <el-form-item label="单位"><el-input v-model="profile.department" /></el-form-item>
          <el-button type="primary" @click="save">保存</el-button>
        </el-form>
      </el-tab-pane>
      <el-tab-pane label="修改密码" name="password">
        <el-form :model="pwd" label-width="80px" style="max-width: 460px">
          <el-form-item label="原密码"><el-input v-model="pwd.old_password" type="password" show-password /></el-form-item>
          <el-form-item label="新密码"><el-input v-model="pwd.new_password" type="password" show-password /></el-form-item>
          <el-button type="primary" @click="changePassword">更新密码</el-button>
        </el-form>
      </el-tab-pane>
      <el-tab-pane label="登录记录" name="logs">
        <el-table :data="logs" border>
          <el-table-column prop="created_at" label="时间" />
          <el-table-column prop="ip" label="IP" />
          <el-table-column prop="result" label="结果">
            <template #default="{ row }">{{ resultText[row.result] || row.result }}</template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import http from "../api/http";
import { useUserStore } from "../stores/user";

const store = useUserStore();
const tab = ref(store.mustChangePassword ? "password" : "profile");
const profile = reactive({ username: "", phone: "", department: "" });
const pwd = reactive({ old_password: "", new_password: "" });
const logs = ref([]);
const resultText = { success: "成功", failed: "失败", locked: "锁定" };

async function load() {
  const { data } = await http.get("/api/users/me/");
  Object.assign(profile, data.data);
  const logRes = await http.get("/api/users/me/login-logs/");
  logs.value = logRes.data.data;
}

async function save() {
  const { data } = await http.put("/api/users/me/", profile);
  store.save(data.data);
  ElMessage.success("资料已保存");
}

async function changePassword() {
  await http.post("/api/users/me/password/", pwd);
  store.mustChangePassword = false;
  localStorage.setItem("mustChange", "0");
  ElMessage.success("密码已更新，请重新登录");
  await store.logout();
  location.href = "/login";
}

onMounted(load);
</script>
