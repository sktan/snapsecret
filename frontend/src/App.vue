<script setup>
import { RouterLink, RouterView } from "vue-router";
</script>

<template>
    <nav class="sb-topnav navbar navbar-expand navbar-dark bg-dark">
        <!-- Navbar Brand-->
        <router-link class="navbar-brand ps-3" :to="{ name: 'home' }">Snap Secret</router-link>

        <div class="d-none d-md-inline-block form-inline ms-auto me-0 me-md-3 my-2 my-md-0">
            <button class="btn btn-secondary me-2" @click="newSecretFilePage">New File Secret</button>

            <button class="btn btn-primary" @click="newSecretPage">New Text Secret</button>
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