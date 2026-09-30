<template>
  <div class="auth">
    <section class="intro">
      <h1>电网短期负荷预测</h1>
      <p>基于 LSTM 的小时负荷预测，支持数据预览、分析与批量预测。</p>
    </section>
    <el-card class="card">
      <h2>登录</h2>
      <el-form :model="form" @submit.prevent="submit">
        <el-form-item><el-input v-model="form.username" placeholder="用户名" /></el-form-item>
        <el-form-item><el-input v-model="form.password" type="password" show-password placeholder="密码" /></el-form-item>
        <el-button type="primary" style="width: 100%" :loading="loading" @click="submit">登录</el-button>
      </el-form>
      <p class="hint">没有账号？<router-link to="/register">注册</router-link></p>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { useUserStore } from "../../stores/user";

const form = reactive({ username: "", password: "" });
const loading = ref(false);
const router = useRouter();
const store = useUserStore();

async function submit() {
  loading.value = true;
  try {
    await store.login(form);
    router.push(store.mustChangePassword ? "/profile" : "/datasets");
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.auth { min-height: 100vh; display: grid; grid-template-columns: 1.2fr 1fr; }
.intro { background: #12324f; color: #fff; display: flex; flex-direction: column; justify-content: center; padding: 64px; }
.intro h1 { margin: 0 0 12px; font-size: 36px; }
.card { margin: auto; width: 360px; }
.hint { color: #607180; font-size: 13px; }
@media (max-width: 800px) { .auth { grid-template-columns: 1fr; } .intro { display: none; } }
</style>
