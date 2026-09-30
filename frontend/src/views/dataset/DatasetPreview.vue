<template>
  <div class="page" v-if="detail">
    <h2 class="page-title">{{ detail.name }}</h2>
    <p>{{ detail.description || "暂无说明" }}</p>
    <div class="cards">
      <div class="stat"><span>样本数</span><strong>{{ detail.sample_count }}</strong></div>
      <div class="stat"><span>均值</span><strong>{{ detail.stat?.mean ?? "-" }}</strong></div>
      <div class="stat"><span>标准差</span><strong>{{ detail.stat?.std ?? "-" }}</strong></div>
      <div class="stat"><span>最小 / 最大</span><strong>{{ detail.stat?.minimum ?? "-" }} / {{ detail.stat?.maximum ?? "-" }}</strong></div>
    </div>
    <div class="panel" style="margin-bottom: 12px">
      <h3>数据字段</h3>
      <el-table :data="detail.columns" border>
        <el-table-column prop="label" label="字段" />
        <el-table-column prop="name" label="列名" />
        <el-table-column prop="dtype" label="类型" />
        <el-table-column prop="required" label="必填">
          <template #default="{ row }">{{ row.required ? "是" : "否" }}</template>
        </el-table-column>
      </el-table>
    </div>
    <div class="panel">
      <div class="toolbar">
        <el-date-picker v-model="range" type="datetimerange" value-format="YYYY-MM-DD HH:mm:ss" start-placeholder="开始" end-placeholder="结束" />
        <el-button type="primary" @click="loadRecords(1)">筛选</el-button>
      </div>
      <el-table :data="records" border @sort-change="sortChange">
        <el-table-column prop="timestamp" label="时间" sortable="custom" />
        <el-table-column prop="load_mw" label="负荷(MW)" sortable="custom" />
        <el-table-column prop="temperature" label="气温" />
        <el-table-column prop="is_holiday" label="节假日" />
      </el-table>
      <el-pagination
        style="margin-top: 12px"
        layout="total, prev, pager, next"
        :total="total"
        :page-size="20"
        :current-page="page"
        @current-change="loadRecords"
      />
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import http from "../../api/http";

const route = useRoute();
const detail = ref(null);
const records = ref([]);
const total = ref(0);
const page = ref(1);
const range = ref([]);
const ordering = ref("timestamp");

async function loadRecords(nextPage = page.value) {
  page.value = nextPage;
  const params = { page: page.value, page_size: 20, ordering: ordering.value };
  if (range.value?.length === 2) {
    params.start = range.value[0];
    params.end = range.value[1];
  }
  const { data } = await http.get(`/api/datasets/${route.params.id}/records/`, { params });
  records.value = data.data.results;
  total.value = data.data.count;
}

function sortChange({ prop, order }) {
  if (!order) ordering.value = "timestamp";
  else ordering.value = order === "descending" ? `-${prop}` : prop;
  loadRecords(1);
}

onMounted(async () => {
  const { data } = await http.get(`/api/datasets/${route.params.id}/`);
  detail.value = data.data;
  loadRecords(1);
});
</script>
