import { createRouter, createWebHistory } from "vue-router";
import { useUserStore } from "../stores/user";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", component: () => import("../views/auth/Login.vue") },
    { path: "/register", component: () => import("../views/auth/Register.vue") },
    {
      path: "/",
      component: () => import("../layouts/MainLayout.vue"),
      redirect: "/datasets",
      children: [
        { path: "datasets", component: () => import("../views/dataset/DatasetList.vue") },
        { path: "datasets/:id", component: () => import("../views/dataset/DatasetPreview.vue") },
        { path: "analysis/:id", component: () => import("../views/analysis/Analysis.vue") },
        { path: "forecast", component: () => import("../views/forecast/Forecast.vue") },
        { path: "forecast/tasks/:id", component: () => import("../views/forecast/Result.vue") },
        { path: "records", component: () => import("../views/records/Records.vue") },
        { path: "profile", component: () => import("../views/Profile.vue") },
        { path: "admin/users", meta: { admin: true }, component: () => import("../views/admin/Users.vue") },
        { path: "admin/roles", meta: { admin: true }, component: () => import("../views/admin/Roles.vue") },
        { path: "admin/datasets", meta: { admin: true }, component: () => import("../views/admin/Datasets.vue") },
      ],
    },
  ],
});

router.beforeEach((to) => {
  const store = useUserStore();
  const logged = !!localStorage.getItem("access");
  if (!logged && !["/login", "/register"].includes(to.path)) return "/login";
  if (logged && ["/login", "/register"].includes(to.path)) return "/datasets";
  if (store.mustChangePassword && to.path !== "/profile" && to.path !== "/login") return "/profile";
  if (to.meta.admin && store.role !== "admin") return "/datasets";
});

export default router;
