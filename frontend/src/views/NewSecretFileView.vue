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
                                <div class="d-flex align-items-center justify-content-between mt-4 mb-0">
                                    <button class="btn btn-primary" @click="encryptAndStore" v-show="!encryptSuccess">
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
const apiEndpoint = import.meta.env.VITE_WEBAPI_ENDPOINT.replace(/\/$/, "")

export default {
    data() {
        return {
            encryptFailureMessage: "",
            encryptFailure: false,
            encryptSuccess: false,
            decryptSecretId: "",
            decryptSecretUrl: "",

            password: "",
            attachment: {},
            encrypted_file: null,
            put_url: "",
            object_key: "",
            salt: window.crypto.getRandomValues(new Uint8Array(16)),
            iv: window.crypto.getRandomValues(new Uint8Array(12)),
            key: {},
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
        async onFileChanged($event) {
            const file = $event.target.files[0];
            this.attachment = file;
            if (file.size > 50 * 1024 * 1024) {
                this.encryptFailure = true;
                this.encryptFailureMessage =
                    "File size is too big. Encryption will likely fail.";
                return
            } else {
                this.encryptFailure = false;
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
        async encryptAndStore() {
            if (this.password.length < 8) {
                this.encryptFailureMessage =
                    "Your encryption passphrase must be at least 8 characters long.";
                this.encryptFailure = true;
                return;
            }
            if (!this.attachment) {
                this.encryptFailureMessage = "Please choose a file.";
                this.encryptFailure = true;
                return;
            }
            if (!this.put_url || !this.object_key) {
                const response = await axios.get(`${apiEndpoint}/file/new`);
                this.put_url = response.data.put_url
                this.object_key = response.data.object_key
            }

            this.key = await this.getKey(this.password, this.salt);

            const encryptedAttachmentName = await window.crypto.subtle.encrypt(
                {
                    name: "AES-GCM",
                    iv: this.iv,
                },
                this.key,
                enc.encode(this.attachment.name)
            );

            const encryptedObj = {
                salt: await this.bufferToBase64Async(this.salt),
                iv: await this.bufferToBase64Async(this.iv),
                file_name: await this.bufferToBase64Async(new Uint8Array(encryptedAttachmentName)),
                object_key: this.object_key,
            };

            try {
                const reader = new FileReader();

                var that = this

                reader.onload = function (e) {
                    var data = e.target.result

                    window.crypto.subtle.encrypt({ name: 'AES-GCM', iv: that.iv }, that.key, enc.encode(data))
                        .then(encrypted => {
                            that.encrypted_file = encrypted
                        })
                        .catch(console.error);
                }


                reader.readAsDataURL(this.attachment);



                const config = {
                    transformRequest: [function (data, headers) {
                        delete headers.put['Content-Type'];
                        delete headers.common['Content-Type'];
                        return data;
                    }],
                };

                while (!this.encrypted_file) {
                    await new Promise(r => setTimeout(r, 100));

                }

                await axios.put(this.put_url, this.encrypted_file, config);

            } catch (err) {
                console.error(err)
                if (err.response.status == 400) {
                    this.encryptFailure = true;
                    this.encryptFailureMessage =
                        "Invalid object upload.";
                } else {
                    this.encryptFailure = true;
                    this.encryptFailureMessage =
                        "An unknown error occurred, unable to upload object.";
                }
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
