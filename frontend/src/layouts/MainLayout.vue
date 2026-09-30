<template>
  <el-container class="shell">
    <el-aside width="220px" class="side">
      <div class="brand">负荷预测系统</div>
      <el-menu :default-active="route.path" router background-color="#12324f" text-color="#d5e4f0" active-text-color="#ffffff">
        <el-menu-item index="/datasets">数据集预览</el-menu-item>
        <el-menu-item index="/forecast">负荷预测</el-menu-item>
        <el-menu-item index="/records">历史记录</el-menu-item>
        <el-menu-item index="/profile">个人中心</el-menu-item>
        <el-sub-menu v-if="store.isAdmin" index="admin">
          <template #title>系统管理</template>
          <el-menu-item index="/admin/users">用户管理</el-menu-item>
          <el-menu-item index="/admin/roles">角色权限</el-menu-item>
          <el-menu-item index="/admin/datasets">数据集管理</el-menu-item>
        </el-sub-menu>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="head">
        <span>{{ store.username }} · {{ store.isAdmin ? "管理员" : "普通用户" }}</span>
        <el-button link type="primary" @click="exit">退出</el-button>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { useRoute, useRouter } from "vue-router";
import { useUserStore } from "../stores/user";

const route = useRoute();
const router = useRouter();
const store = useUserStore();

async function exit() {
  await store.logout();
  router.push("/login");
}
</script>

<style scoped>
.shell { min-height: 100vh; }
.side { background: #12324f; }
.brand { color: #fff; font-weight: 700; padding: 18px 16px; letter-spacing: 1px; }
.head {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 12px;
  background: #fff;
  border-bottom: 1px solid #d7e0e8;
}
.el-menu { border-right: none; }
</style>
