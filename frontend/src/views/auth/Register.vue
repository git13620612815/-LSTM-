<template>
  <div class="auth">
    <el-card class="card">
      <h2>注册</h2>
      <el-form :model="form" label-position="top">
        <el-form-item label="用户名"><el-input v-model="form.username" /></el-form-item>
        <el-form-item label="手机号"><el-input v-model="form.phone" /></el-form-item>
        <el-form-item label="密码"><el-input v-model="form.password" type="password" show-password /></el-form-item>
        <el-form-item label="确认密码"><el-input v-model="form.confirm_password" type="password" show-password /></el-form-item>
        <el-button type="primary" style="width: 100%" :loading="loading" @click="submit">注册</el-button>
      </el-form>
      <p class="hint">已有账号？<router-link to="/login">登录</router-link></p>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import http from "../../api/http";

const form = reactive({ username: "", phone: "", password: "", confirm_password: "" });
const loading = ref(false);
const router = useRouter();

async function submit() {
  loading.value = true;
  try {
    await http.post("/api/auth/register/", form);
    ElMessage.success("注册成功，请登录");
    router.push("/login");
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.auth { min-height: 100vh; display: grid; place-items: center; background: #12324f; }
.card { width: 380px; }
.hint { color: #607180; font-size: 13px; }
</style>
