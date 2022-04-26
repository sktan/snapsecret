import { createRouter, createWebHistory } from "vue-router";
import HomeView from "../views/HomeView.vue";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/",
      name: "home",
      component: HomeView,
    },
    {
      path: "/new",
      name: "secret.new",
      component: () => import("../views/NewSecretView.vue"),
    },
    {
      path: "/secret/:id",
      name: "secret.get",
      component: () => import("../views/GetSecretView.vue"),
      props: true,
    },
  ],
});

export default router;
