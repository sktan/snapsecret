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
      path: "/file-new",
      name: "secret-file.new",
      component: () => import("../views/NewSecretFileView.vue"),
    },
    {
      path: "/secret/:id",
      name: "secret.get",
      component: () => import("../views/GetSecretView.vue"),
      props: true,
    },
    {
      path: "/404", component: () => import("../views/404.vue"),
    },
    {
      path: "/:pathMatch(.*)*", component: () => import("../views/404.vue"),
    }
  ],
});

export default router;
