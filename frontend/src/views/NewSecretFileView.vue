<template>
    <main>
        <div class="container">
            <div class="row justify-content-center">
                <div class="col-lg-12">
                    <div class="card shadow-lg border-0 rounded-lg mt-12">
                        <div class="card-header">
                            <h3 class="text-center font-weight-light my-3">
                                Upload a New Secret
                            </h3>
                        </div>
                        <div class="card-body">
                            <div v-show="encryptSuccess" class="alert alert-success" role="alert">
                                Your secret was successfully encrypted stored,
                                please send this URL to your recipient. <br />
                                <router-link :to="'/secret/' + decryptSecretId">
                                    {{ decryptSecretUrl }}
                                </router-link>
                            </div>
                            <div v-show="encryptFailure" class="alert alert-danger" role="alert">
                                {{ encryptFailureMessage }}
                            </div>

                            <form @submit.prevent="">
                                <div class="form-floating mb-3">
                                    <input class="form-control" id="encryption_passphrase" v-model="password" required
                                        minlength="8" />
                                    <label for="encryption_passphrase">Encryption Passphrase</label>
                                </div>
                                <div class="mb-3" v-show="!encryptSuccess">
                                    <input type="file" class="form-control" name="attachment" required
                                        @change="onFileChanged($event)" />
                                </div>
                                <div class="mb-3" v-show="uploading">
                                    <label class="form-label">{{ progressPhase }}</label>
                                    <progress class="w-100" :value="progressPercent" max="100"></progress>
                                </div>
                                <div class="d-flex align-items-center justify-content-between mt-4 mb-0">
                                    <button class="btn btn-primary" @click="encryptAndStore" v-show="!encryptSuccess"
                                        :disabled="!fileValid || uploading">
                                        Upload
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </main>
</template>

<style>
.form-floating>textarea {
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
import { CHUNK_SIZE, buildChunkIv, getKey } from "@/utils/fileCrypto";
const apiEndpoint = import.meta.env.VITE_WEBAPI_ENDPOINT.replace(/\/$/, "")

const MAX_FILE_SIZE_BYTES = 1024 * 1024 * 1024; // 1 GiB

export default {
    data() {
        return {
            encryptFailureMessage: "",
            encryptFailure: false,
            encryptSuccess: false,
            decryptSecretId: "",
            decryptSecretUrl: "",

            password: "",
            attachment: null,
            fileValid: false,
            uploading: false,
            progressPercent: 0,
            progressPhase: "",
            put_url: "",
            object_key: "",
            salt: window.crypto.getRandomValues(new Uint8Array(16)),
            iv: window.crypto.getRandomValues(new Uint8Array(12)),
            key: {},
        };
    },
    methods: {
        async onFileChanged($event) {
            const file = $event.target.files[0];
            this.attachment = file;
            if (file.size > MAX_FILE_SIZE_BYTES) {
                this.encryptFailure = true;
                this.encryptFailureMessage =
                    "File size is too big. Maximum supported file size is 1GB.";
                this.fileValid = false;
                return
            } else {
                this.encryptFailure = false;
                this.fileValid = true;
            }
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
        async encryptFileInChunks(fileIvPrefix) {
            const file = this.attachment;
            const totalChunks = Math.max(1, Math.ceil(file.size / CHUNK_SIZE));
            const parts = [];

            for (let i = 0; i < totalChunks; i++) {
                const start = i * CHUNK_SIZE;
                const end = Math.min(start + CHUNK_SIZE, file.size);
                const chunkBuf = await file.slice(start, end).arrayBuffer();

                const encChunk = await window.crypto.subtle.encrypt(
                    { name: "AES-GCM", iv: buildChunkIv(fileIvPrefix, i), tagLength: 128 },
                    this.key,
                    chunkBuf
                );

                parts.push(new Uint8Array(encChunk));
                this.progressPercent = Math.round(((i + 1) / totalChunks) * 100);
            }

            return new Blob(parts, { type: "application/octet-stream" });
        },
        async encryptAndStore() {
            if (this.password.length < 8) {
                this.encryptFailureMessage =
                    "Your encryption passphrase must be at least 8 characters long.";
                this.encryptFailure = true;
                return;
            }
            if (!this.attachment || !this.fileValid) {
                this.encryptFailureMessage = this.attachment
                    ? "File size is too big. Maximum supported file size is 1GB."
                    : "Please choose a file.";
                this.encryptFailure = true;
                return;
            }
            if (this.attachment.size > MAX_FILE_SIZE_BYTES) {
                this.encryptFailureMessage = "File size is too big. Maximum supported file size is 1GB.";
                this.encryptFailure = true;
                this.fileValid = false;
                return;
            }
            if (!this.put_url || !this.object_key) {
                const response = await axios.get(`${apiEndpoint}/file/new`);
                this.put_url = response.data.put_url
                this.object_key = response.data.object_key
            }

            this.key = await getKey(this.password, this.salt);

            const encryptedAttachmentName = await window.crypto.subtle.encrypt(
                {
                    name: "AES-GCM",
                    iv: this.iv,
                },
                this.key,
                enc.encode(this.attachment.name)
            );

            const fileIvPrefix = window.crypto.getRandomValues(new Uint8Array(8));

            const encryptedObj = {
                salt: await this.bufferToBase64Async(this.salt),
                iv: await this.bufferToBase64Async(this.iv),
                file_name: await this.bufferToBase64Async(new Uint8Array(encryptedAttachmentName)),
                file_iv_prefix: await this.bufferToBase64Async(fileIvPrefix),
                object_key: this.object_key,
            };

            this.uploading = true;
            this.progressPercent = 0;
            this.progressPhase = "Encrypting…";

            try {
                const encryptedBlob = await this.encryptFileInChunks(fileIvPrefix);

                this.progressPhase = "Uploading…";
                this.progressPercent = 0;

                const config = {
                    transformRequest: [function (data, headers) {
                        delete headers['Content-Type'];
                        return data;
                    }],
                    onUploadProgress: (e) => {
                        this.progressPercent = Math.round((e.loaded / e.total) * 100);
                    },
                };

                await axios.put(this.put_url, encryptedBlob, config);

            } catch (err) {
                console.error(err)
                if (err.response && err.response.status == 400) {
                    this.encryptFailure = true;
                    this.encryptFailureMessage =
                        "Invalid object upload.";
                } else {
                    this.encryptFailure = true;
                    this.encryptFailureMessage =
                        "An unknown error occurred, unable to upload object.";
                }
                this.uploading = false;
                return;
            }

            try {
                const response = await axios.put(`${apiEndpoint}/secret`, {
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
                this.uploading = false;
            } catch (err) {
                if (err.response && err.response.status == 400) {
                    this.encryptFailure = true;
                    this.encryptFailureMessage =
                        "Invalid data was sent to the API, please change your input and try again.";
                } else {
                    this.encryptFailure = true;
                    this.encryptFailureMessage =
                        "An unknown error occurred, please try again soon.";
                }
                this.uploading = false;
                return;
            }
        },
    },
};
</script>
