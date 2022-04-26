<script setup>
import WelcomeItem from "./WelcomeItem.vue";
import { RouterLink } from "vue-router";
</script>

<template>
    <WelcomeItem>
        <template #heading>What is SnapSecret?</template>
        SnapSecret is a simple and easy way to securely send secrets (such as
        passwords, API keys, etc.) to other people. This is done by encrypting
        the secret within your browser with a password before sending it to the
        backend storage. This ensures that the backend will never receive or
        store the secret in it's unencrypted form.
    </WelcomeItem>

    <WelcomeItem>
        <template #heading>Usage</template>

        You will first need to submit your secret via the
        <router-link :to="{ name: 'secret.new' }">New Secret</router-link> page.
        Once completed, your secret will be retrievable via a one time access
        link that is generated. You can then share this link with the intended
        recipient, and they will be able use this to decrypt the contents. If
        the recipient does not access the page within 24 hours, it will
        automatically self destruct and become invalid.
    </WelcomeItem>
</template>
