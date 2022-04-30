<template>
    <div class="container">
        <div class="row justify-content-center">
            <div class="col-lg-12">
                <div class="card shadow-lg border-0 rounded-lg mt-12">
                    <div class="card-header">
                        <h3 class="text-center font-weight-light my-3">
                            Create a New Secret
                        </h3>
                    </div>
                    <div class="card-body">
                        <div
                            v-show="encryptSuccess"
                            class="alert alert-success"
                            role="alert"
                        >
                            Your secret was successfully encrypted stored,
                            please send this URL to your recipient. <br />
                            <router-link :to="'/secret/' + decryptSecretId">
                                {{ decryptSecretUrl }}
                            </router-link>
                        </div>
                        <div
                            v-show="encryptFailure"
                            class="alert alert-danger"
                            role="alert"
                        >
                            {{ encryptFailureMessage }}
                        </div>

                        <form @submit.prevent="">
                            <div class="form-floating mb-3">
                                <input
                                    class="form-control"
                                    id="encryption_passphrase"
                                    v-model="password"
                                    required
                                    minlength="8"
                                />
                                <label for="encryption_passphrase"
                                    >Encryption Passphrase</label
                                >
                            </div>
                            <div
                                class="form-floating mb-3"
                                v-show="!encryptSuccess"
                                required
                            >
                                <textarea
                                    class="form-control"
                                    name="secret"
                                    rows="5"
                                    v-model="secret"
                                ></textarea>
                                <label for="secret">Secret</label>
                            </div>
                            <div
                                class="d-flex align-items-center justify-content-between mt-4 mb-0"
                            >
                                <button
                                    class="btn btn-primary"
                                    @click="encryptAndStore"
                                    v-show="!encryptSuccess"
                                >
                                    Store
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<style>
.form-floating > textarea {
    min-height: 100px !important;
}

@media (min-width: 1024px) {
    .container {
        min-width: 800px;
        min-height: 100vh;
        display: inline-grid;
        align-items: center;
    }
}
</style>

<script>
const enc = new TextEncoder();
import axios from "axios";
const apiEndpoint = [
    import.meta.env.VITE_WEBAPI_ENDPOINT.replace(/\/$/, ""),
    "/secret/",
].join("");

export default {
    data() {
        return {
            encryptFailureMessage: "",
            encryptFailure: false,
            encryptSuccess: false,
            decryptSecretId: "",
            decryptSecretUrl: "",

            password: "",
            secret: "",
        };
    },
    methods: {
        async getKey(passphrase, salt) {
            const keyMaterial = await window.crypto.subtle.importKey(
                "raw",
                enc.encode(passphrase),
                { name: "PBKDF2" },
                false,
                ["deriveBits", "deriveKey"]
            );
            return window.crypto.subtle.deriveKey(
                {
                    name: "PBKDF2",
                    salt: salt,
                    iterations: 100000,
                    hash: "SHA-256",
                },
                keyMaterial,
                { name: "AES-GCM", length: 256 },
                true,
                ["encrypt", "decrypt"]
            );
        },
        // buffer to base64
        async bufferToBase64Async(buffer) {
            var blob = new Blob([buffer], { type: "application/octet-binary" });
            var fileReader = new FileReader();
            return new Promise(function (resolve) {
                fileReader.onload = function () {
                    var dataUrl = fileReader.result;
                    var base64 = dataUrl.substr(dataUrl.indexOf(",") + 1);
                    resolve(base64);
                };
                fileReader.readAsDataURL(blob);
            });
        },
        async encryptAndStore() {
            if (this.password.length < 8) {
                this.encryptFailureMessage =
                    "Your encryption passphrase must be at least 8 characters long.";
                this.encryptFailure = true;
                return;
            }
            if (this.secret.length == 0) {
                this.encryptFailureMessage = "Your secret cannot be empty.";
                this.encryptFailure = true;
                return;
            }

            const salt = window.crypto.getRandomValues(new Uint8Array(16));
            const iv = window.crypto.getRandomValues(new Uint8Array(12));

            const key = await this.getKey(this.password, salt);

            const ciphertext = await window.crypto.subtle.encrypt(
                {
                    name: "AES-GCM",
                    iv: iv,
                },
                key,
                enc.encode(this.secret)
            );

            const encryptedObj = {
                secret: await this.bufferToBase64Async(
                    new Uint8Array(ciphertext)
                ),
                salt: await this.bufferToBase64Async(salt),
                iv: await this.bufferToBase64Async(iv),
            };

            try {
                const response = await axios.put(apiEndpoint, {
                    secret: encryptedObj,
                });

                this.decryptSecretId = response.data.secret_id;
                this.decryptSecretUrl = [
                    window.location.origin,
                    "secret",
                    response.data.secret_id,
                ].join("/");
                this.encryptSuccess = true;
                this.encryptFailure = false;
            } catch (err) {
                if (err.response.status == 400) {
                    this.encryptFailure = true;
                    this.encryptFailureMessage =
                        "Invalid data was sent to the API, please change your input and try again.";
                } else {
                    this.encryptFailure = true;
                    this.encryptFailureMessage =
                        "An unknown error occurred, please try again soon.";
                }
                return;
            }
        },
    },
};
</script>
