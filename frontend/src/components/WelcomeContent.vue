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
        (OTA) link that is generated. You can then share this link with the
        intended recipient, and they will be able use this to decrypt the
        contents. If the recipient does not access the page within 24 hours, it
        will automatically self destruct and become invalid.
    </WelcomeItem>

    <WelcomeItem>
        <template #heading>Sending the OTA link</template>

        Your are free to send the OTA link via any medium, as there is it is not
        considered sensitive data. The preferred way for the decryption
        passphrase to be communicated to the recipient is via a separate medium
        (e.g. sms, voice call, pre-shared key). Remind the user that the OTA
        link will expire in 24 hours, or if it has been accessed by someone
        else. If the OTA link has self-destructed prior to 24 hours, you are
        recommended to generate a new secret to send as it is possible that it
        has been intercepted by another party.
    </WelcomeItem>
</template>
