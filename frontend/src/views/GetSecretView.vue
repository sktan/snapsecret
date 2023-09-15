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
                        <div v-show="decryptSuccess" class="alert alert-success" role="alert">
                            Your secret was successfully decrypted and
                            self-destruction has taken place.
                        </div>
                        <div v-show="decryptWarning" class="alert alert-warning" role="alert">
                            Pressing the Decrypt button will cause the secret to
                            self-destruct and become inaccessible.
                        </div>
                        <div v-show="decryptFailure" class="alert alert-danger" role="alert">
                            {{ decryptFailureMessage }}
                        </div>

                        <form @submit.prevent="">
                            <div class="form-floating mb-3" v-show="!decryptSuccess">
                                <input class="form-control" id="decrpytion_passphrase" v-model="password" />
                                <label for="decrpytion_passphrase">Decryption Passphrase</label>
                            </div>
                            <div v-show="decryptSuccess" class="input-group mb-3">
                                <button type="button" v-bind:class="{
                                    'btn-clipboard': !clipboardSuccess,
                                    'btn-clipboard-success':
                                        clipboardSuccess,
                                }" v-show="!isFile" title="Copy to clipboard" @click="copyToClipboard">
                                    <svg class="bi" width="1em" height="1em" fill="currentColor">
                                        <use v-show="!clipboardSuccess"
                                            xlink:href="~/bootstrap-icons/bootstrap-icons.svg#clipboard"></use>
                                        <use v-show="clipboardSuccess"
                                            xlink:href="~/bootstrap-icons/bootstrap-icons.svg#clipboard-check"></use>
                                    </svg>
                                </button>
                                <textarea class="form-control" rows="5" v-model="secret" v-show="!isFile"
                                    readonly></textarea>
                            </div>
                            <div class="d-flex align-items-center justify-content-between mt-4 mb-0">
                                <button class="btn btn-primary" @click="fetchAndDecrypt" v-show="!decryptSuccess">
                                    Decrypt
                                </button>
                                <button v-show="decryption_complete" class="btn btn-primary" @click="save">
                                    Save
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
@import "bootstrap-icons/font/bootstrap-icons.css";

.input-group>textarea {
    padding-right: 30px !important;
}

.btn-clipboard:hover {
    color: #0d6efd;
}

.btn-clipboard-success {
    position: absolute;
    top: 0.75em;
    right: 0.5em;
    z-index: 10;
    display: block;
    padding: 0.5em 0.75em 0.625em;
    line-height: 1;
    color: #0d6efd;
    background-color: rgba(255, 255, 255, 0);
    border: 0;
    border-radius: 0.25rem;
}

.btn-clipboard {
    position: absolute;
    top: 0.75em;
    right: 0.5em;
    z-index: 10;
    display: block;
    padding: 0.5em 0.75em 0.625em;
    line-height: 1;
    color: #212529;
    background-color: rgba(255, 255, 255, 0);
    border: 0;
    border-radius: 0.25rem;
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
            decryption_complete: false,
            decryptFailureMessage: "",
            clipboardSuccess: false,
            isFile: false,

            password: "",
            secret: null,

            file_name: "",
            get_url: "",
            delete_url: "",
            object_key: "",

            file_data: null,

            encryptedObj: {
                file_name: [],
                secret: [],
                salt: [],
                iv: [],
            },
        };
    },
    methods: {
        async copyToClipboard() {
            try {
                // Fallback to document.execCommand('copy') for better browser coverage
                if (!navigator.clipboard) {
                    const textArea = document.getElementsByName("secret");
                    textArea[0].focus();
                    textArea[0].select();
                    document.execCommand("copy");
                } else {
                    await navigator.clipboard.writeText(this.secret);
                }

                this.clipboardSuccess = true;

                setTimeout(() => {
                    this.clipboardSuccess = false;
                }, 1500);
            } catch (err) {
                alert("Failed to copy text: " + err);
            }
        },
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
        urlToBufferAsync(url) {
            return new Promise(function (resolve) {
                fetch(url)
                    .then((res) => res.arrayBuffer())
                    .then((buffer) => {
                        resolve(new Uint8Array(buffer));
                    });
            });
        },
        save() {
            const link = document.createElement("a");
            link.href = this.file_data;
            link.download = this.file_name;
            link.click();
        },
        async fetchAndDecrypt() {
            if (!this.encryptedObj || this.encryptedObj.secret.length == 0) {
                try {
                    const response = await axios.get(apiEndpoint + this.id);

                    this.encryptedObj.salt = response.data.secret.salt;
                    this.encryptedObj.iv = response.data.secret.iv;
                    if (response.data.secret.secret !== undefined) {
                        this.encryptedObj.secret = response.data.secret.secret;
                    }
                    if (response.data.secret.file_name !== undefined) {
                        this.get_url = response.data.secret.get_url;
                        this.encryptedObj.file_name = response.data.secret["file_name"];
                        this.delete_url = response.data.secret.delete_url;
                        this.isFile = true;
                    }
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

            if (this.isFile) {
                try {
                    let decryptedFileName = await window.crypto.subtle.decrypt(
                        {
                            name: "AES-GCM",
                            iv: iv,
                        },
                        key,
                        await this.base64ToBufferAsync(this.encryptedObj.file_name)
                    );

                    let decryptedFileData = await window.crypto.subtle.decrypt(
                        {
                            name: "AES-GCM",
                            iv: iv,
                        },
                        key,
                        await this.urlToBufferAsync(this.get_url),
                    );
                    axios.delete(this.delete_url)
                    this.file_data = dec.decode(decryptedFileData);
                    this.decryption_complete = true;
                    this.file_name = dec.decode(decryptedFileName);
                    this.decryptFailure = false;
                    this.decryptSuccess = true;
                } catch (e) {
                    console.error(e)
                    this.decryptFailure = true;
                    this.decryptFailureMessage =
                        "An incorrect decryption passphrase was provided, please check that it is correct.";
                }
            } else {
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
            }
        },
    },
};
</script>
