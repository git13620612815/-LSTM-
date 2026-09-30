<template>
  <div class="page">
    <h2 class="page-title">角色权限</h2>
    <div class="grid-2">
      <div class="panel" v-for="role in roles" :key="role.code">
        <h3>{{ role.name }}</h3>
        <el-checkbox-group v-model="role.permissions">
          <el-checkbox v-for="item in catalog" :key="item.code" :value="item.code" style="display: block">{{ item.name }}</el-checkbox>
        </el-checkbox-group>
        <el-button type="primary" style="margin-top: 12px" @click="save(role)">保存</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import http from "../../api/http";

const roles = ref([]);
const catalog = ref([]);

async function load() {
  const { data } = await http.get("/api/admin/roles/");
  roles.value = data.data.roles;
  catalog.value = data.data.catalog;
}

async function save(role) {
  await http.put(`/api/admin/roles/${role.code}/`, { permissions: role.permissions });
  ElMessage.success("权限已更新");
}

onMounted(load);
</script>
