<script setup>
import { RouterLink, RouterView } from "vue-router";
</script>

<template>
    <nav class="sb-topnav navbar navbar-expand navbar-dark bg-dark">
        <!-- Navbar Brand-->
        <router-link class="navbar-brand ps-3" :to="{ name: 'home' }"
            >Snap Secret</router-link
        >

        <div
            class="d-none d-md-inline-block form-inline ms-auto me-0 me-md-3 my-2 my-md-0"
        >
            <router-link class="btn btn-secondary me-2" :to="{ name: 'secret-file.new' }"
                >New File Secret</router-link
            >

            <router-link class="btn btn-primary" :to="{ name: 'secret.new' }"
                >New Text Secret</router-link
            >
        </div>
    </nav>

    <RouterView />
</template>

<style>
@import "@/assets/base.css";

#app {
    max-width: 1400px;
    margin: 0 auto;
    padding: 2rem;

    font-weight: normal;
    padding-top: 65px;
}

@media (min-width: 1024px) {
    body {
        display: flex;
        place-items: center;
    }

    #app {
        display: grid;
        padding: 0 2rem;
    }

    header {
        display: flex;
        place-items: center;
        padding-right: calc(var(--section-gap) / 2);
    }

    header .wrapper {
        display: flex;
        place-items: flex-start;
        flex-wrap: wrap;
    }

    .logo {
        margin: 0 2rem 0 0;
    }
}
</style>
