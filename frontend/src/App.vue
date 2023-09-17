<script setup>
import { RouterLink, RouterView } from "vue-router";
import 'bootstrap';
</script>

<template>
    <nav class="navbar navbar-expand-md navbar-dark bg-dark">
        <!-- Navbar Brand-->
        <div class="container-fluid">
            <router-link class="navbar-brand ps-1" :to="{ name: 'home' }">🤫 Snap Secret</router-link>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarCollapse"
                aria-controls="navbarCollapse" aria-expanded="false" aria-label="Toggle navigation">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarCollapse">
                <ul class="navbar-nav ms-auto">
                    <li class="nav-item">
                        <a class="nav-link btn btn-secondary me-2 ms-2 mt-1 mb-1" @click="newSecretFilePage">New File Secret</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link btn btn-primary me-2 ms-2 mt-1 mb-1" @click="newSecretPage">New Text Secret</a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <RouterView />
</template>

<style>
@import "@/assets/base.css";
@import "bootstrap-icons/font/bootstrap-icons.css";

html, body {
    margin: 0;
    padding: 0;
}

main {
    max-width: 1400px;
    margin: 0 auto;
    padding: 2rem;

    font-weight: normal;
    padding-top: 65px;
}
</style>
<script>
export default {
    methods: {
        // Fix New Secret buttone not working when
        //   you are already on the page
        newSecretPage() {
            if (location.pathname == "/new") {
                location.reload();
            } else {
                this.$router.push("/new")
            }
        },
        newSecretFilePage() {
            if (location.pathname == "/file-new") {
                location.reload();
            } else {
                this.$router.push("/file-new")
            }
        },
    },
}
</script>