<template>
    <div class="container">
        <div class="row justify-content-center">
            <div class="col-lg-12">
                <div class="card shadow-lg border-0 rounded-lg mt-12">
                    <div class="card-header">
                        <h3 class="text-center font-weight-light my-3">
                            Receive your Secret
                        </h3>
                    </div>
                    <div class="card-body">
                        <div
                            v-show="decryptSuccess"
                            class="alert alert-success"
                            role="alert"
                        >
                            Your secret was successfully decrypted and
                            self-destruction has taken place.
                        </div>
                        <div
                            v-show="decryptWarning"
                            class="alert alert-warning"
                            role="alert"
                        >
                            Pressing the Decrypt button will cause the secret to
                            self-destruct and become inaccessible.
                        </div>
                        <div
                            v-show="decryptFailure"
                            class="alert alert-danger"
                            role="alert"
                        >
                            {{ decryptFailureMessage }}
                        </div>

                        <form @submit.prevent="">
                            <div
                                class="form-floating mb-3"
                                v-show="!decryptSuccess"
                            >
                                <input
                                    class="form-control"
                                    id="decrpytion_passphrase"
                                    v-model="password"
                                />
                                <label for="decrpytion_passphrase"
                                    >Decryption Passphrase</label
                                >
                            </div>
                            <div
                                class="form-floating mb-3"
                                v-show="decryptSuccess"
                            >
                                <textarea
                                    class="form-control"
                                    rows="10"
                                    v-model="secret"
                                    readonly
                                ></textarea>
                            </div>
                            <div
                                class="d-flex align-items-center justify-content-between mt-4 mb-0"
                            >
                                <button
                                    class="btn btn-primary"
                                    @click="fetchAndDecrypt"
                                    v-show="!decryptSuccess"
                                >
                                    Decrypt
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
const dec = new TextDecoder();
import axios from "axios";
const apiEndpoint = [
    import.meta.env.VITE_WEBAPI_ENDPOINT.replace(/\/$/, ""),
    "/secret/",
].join("");

export default {
    props: ["id"],
    data() {
        return {
            decryptWarning: true,
            decryptSuccess: false,
            decryptFailure: false,
            decryptFailureMessage: "",

            password: "",
            secret: null,

            encryptedObj: {
                secret: [],
                salt: [],
                iv: [],
            },
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
        // base64 to buffer
        base64ToBufferAsync(base64) {
            var dataUrl = "data:application/octet-binary;base64," + base64;

            return new Promise(function (resolve) {
                fetch(dataUrl)
                    .then((res) => res.arrayBuffer())
                    .then((buffer) => {
                        resolve(new Uint8Array(buffer));
                    });
            });
        },
        async fetchAndDecrypt() {
            if (!this.encryptedObj || this.encryptedObj.secret.length == 0) {
                try {
                    const response = await axios.get(apiEndpoint + this.id);

                    this.encryptedObj.salt = response.data.secret.salt;
                    this.encryptedObj.iv = response.data.secret.iv;
                    this.encryptedObj.secret = response.data.secret.secret;
                    this.decryptWarning = false;
                } catch (err) {
                    this.decryptWarning = false;
                    if (err.response.status == 404) {
                        this.decryptFailure = true;
                        this.decryptFailureMessage =
                            "Secret did not exist or has already self-destructed, please ask the sender to generate you a new URL.";
                    } else {
                        this.decryptFailure = true;
                        this.decryptFailureMessage =
                            "An unknown error occurred, please try again soon.";
                    }
                    return;
                }
            }

            const salt = await this.base64ToBufferAsync(this.encryptedObj.salt);
            const iv = await this.base64ToBufferAsync(this.encryptedObj.iv);

            const key = await this.getKey(this.password, salt);

            try {
                let decrypted = await window.crypto.subtle.decrypt(
                    {
                        name: "AES-GCM",
                        iv: iv,
                    },
                    key,
                    await this.base64ToBufferAsync(this.encryptedObj.secret)
                );

                this.secret = dec.decode(decrypted);
                this.decryptFailure = false;
                this.decryptSuccess = true;
            } catch (e) {
                this.decryptFailure = true;
                this.decryptFailureMessage =
                    "An incorrect decryption passphrase was provided, please check that it is correct.";
            }
        },
    },
};
</script>
