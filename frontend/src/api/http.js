import axios from "axios";
import { ElMessage } from "element-plus";

const http = axios.create({ baseURL: "", timeout: 60000 });

http.interceptors.request.use((config) => {
  const access = localStorage.getItem("access");
  if (access) config.headers.Authorization = `Bearer ${access}`;
  return config;
});

let refreshing = null;

async function refreshAccess() {
  const refresh = localStorage.getItem("refresh");
  if (!refresh) throw new Error("no refresh");
  const { data } = await axios.post("/api/auth/refresh/", { refresh });
  localStorage.setItem("access", data.data.access);
  return data.data.access;
}

http.interceptors.response.use(
  (response) => response,
  async (error) => {
    const config = error.config || {};
    const status = error.response?.status;
    if (status === 401 && !config._retry && !String(config.url).includes("/api/auth/")) {
      config._retry = true;
      try {
        refreshing = refreshing || refreshAccess();
        const access = await refreshing;
        refreshing = null;
        config.headers.Authorization = `Bearer ${access}`;
        return http(config);
      } catch {
        refreshing = null;
        localStorage.removeItem("access");
        localStorage.removeItem("refresh");
        if (location.pathname !== "/login") location.href = "/login";
      }
    }
    if (error.response?.data instanceof Blob) {
      const text = await error.response.data.text();
      try {
        const body = JSON.parse(text);
        ElMessage.error(body.message || "请求失败");
      } catch {
        ElMessage.error("请求失败");
      }
    } else if (status !== 401) {
      ElMessage.error(error.response?.data?.message || "请求失败");
    }
    return Promise.reject(error);
  }
);

export default http;
