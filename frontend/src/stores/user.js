import { defineStore } from "pinia";
import http from "../api/http";

export const useUserStore = defineStore("user", {
  state: () => ({
    username: localStorage.getItem("username") || "",
    role: localStorage.getItem("role") || "",
    permissions: JSON.parse(localStorage.getItem("permissions") || "[]"),
    mustChangePassword: localStorage.getItem("mustChange") === "1",
  }),
  getters: {
    isAdmin: (state) => state.role === "admin",
    can: (state) => (code) => state.permissions.includes(code),
  },
  actions: {
    save(data) {
      this.username = data.username;
      this.role = data.role;
      this.permissions = data.permissions || [];
      this.mustChangePassword = !!data.must_change_password;
      localStorage.setItem("username", data.username);
      localStorage.setItem("role", data.role);
      localStorage.setItem("permissions", JSON.stringify(this.permissions));
      localStorage.setItem("mustChange", this.mustChangePassword ? "1" : "0");
      if (data.access) localStorage.setItem("access", data.access);
      if (data.refresh) localStorage.setItem("refresh", data.refresh);
    },
    async login(form) {
      const { data } = await http.post("/api/auth/login/", form);
      this.save(data.data);
    },
    async logout() {
      const refresh = localStorage.getItem("refresh");
      try {
        if (refresh) await http.post("/api/auth/logout/", { refresh });
      } finally {
        this.clear();
      }
    },
    clear() {
      this.username = "";
      this.role = "";
      this.permissions = [];
      this.mustChangePassword = false;
      ["access", "refresh", "username", "role", "permissions", "mustChange"].forEach((key) =>
        localStorage.removeItem(key)
      );
    },
  },
});
