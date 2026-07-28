<template>
    <main>
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
                                <div class="mb-3" v-show="downloading">
                                    <label class="form-label">Decrypting…</label>
                                    <progress class="w-100" :value="progressPercent" max="100"></progress>
                                </div>
                                <div class="d-flex align-items-center justify-content-between mt-4 mb-0">
                                    <button class="btn btn-primary" @click="fetchAndDecrypt" v-show="!decryptSuccess"
                                        :disabled="downloading">
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
    </main>
</template>

<style>
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
const dec = new TextDecoder();
import axios from "axios";
import { CHUNK_SIZE, GCM_TAG_BYTES, buildChunkIv, getKey } from "@/utils/fileCrypto";
const apiEndpoint = [
    import.meta.env.VITE_WEBAPI_ENDPOINT.replace(/\/$/, ""),
    "/secret/",
].join("");

const ENCRYPTED_CHUNK_SIZE = CHUNK_SIZE + GCM_TAG_BYTES;

// Pulls exactly n bytes off the front of a queue of Uint8Array pieces,
// splitting the last piece as needed. Mutates `pieces` in place.
function takeBytes(pieces, n) {
    const out = new Uint8Array(n);
    let offset = 0;
    while (offset < n) {
        const piece = pieces[0];
        const remaining = n - offset;
        if (piece.length <= remaining) {
            out.set(piece, offset);
            offset += piece.length;
            pieces.shift();
        } else {
            out.set(piece.subarray(0, remaining), offset);
            pieces[0] = piece.subarray(remaining);
            offset += remaining;
        }
    }
    return out;
}

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
            downloading: false,
            progressPercent: 0,

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
                file_iv_prefix: [],
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
        // Streams the encrypted file from `url`, decrypting it chunk by chunk
        // so peak memory stays bounded instead of buffering the whole file.
        async streamDecryptFileToBlob(url, key, fileIvPrefix) {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`Failed to fetch file: ${response.status}`);
            }
            const contentLength = Number(response.headers.get("content-length")) || 0;
            const reader = response.body.getReader();

            const pieces = [];
            let queuedLength = 0;
            let received = 0;
            let chunkIndex = 0;
            const plaintextParts = [];

            const decryptAndPush = async (n) => {
                const bytes = takeBytes(pieces, n);
                queuedLength -= n;
                const plain = await window.crypto.subtle.decrypt(
                    { name: "AES-GCM", iv: buildChunkIv(fileIvPrefix, chunkIndex++), tagLength: 128 },
                    key,
                    bytes
                );
                plaintextParts.push(new Uint8Array(plain));
            };

            while (true) {
                const { done, value } = await reader.read();
                if (value) {
                    pieces.push(value);
                    queuedLength += value.length;
                    received += value.length;
                    if (contentLength) {
                        this.progressPercent = Math.round((received / contentLength) * 100);
                    }
                }
                while (queuedLength >= ENCRYPTED_CHUNK_SIZE) {
                    await decryptAndPush(ENCRYPTED_CHUNK_SIZE);
                }
                if (done) break;
            }

            if (queuedLength > 0) {
                await decryptAndPush(queuedLength);
            }

            return new Blob(plaintextParts);
        },
        save() {
            const link = document.createElement("a");
            link.href = this.file_data;
            link.download = this.file_name;
            link.click();
            setTimeout(() => {
                URL.revokeObjectURL(this.file_data);
            }, 1000);
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
                        this.encryptedObj.file_iv_prefix = response.data.secret["file_iv_prefix"];
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

            const key = await getKey(this.password, salt);

            if (this.isFile) {
                this.downloading = true;
                this.progressPercent = 0;
                try {
                    let decryptedFileName = await window.crypto.subtle.decrypt(
                        {
                            name: "AES-GCM",
                            iv: iv,
                        },
                        key,
                        await this.base64ToBufferAsync(this.encryptedObj.file_name)
                    );

                    const fileIvPrefix = await this.base64ToBufferAsync(this.encryptedObj.file_iv_prefix);
                    const decryptedBlob = await this.streamDecryptFileToBlob(this.get_url, key, fileIvPrefix);

                    axios.delete(this.delete_url)
                    this.file_data = URL.createObjectURL(decryptedBlob);
                    this.decryption_complete = true;
                    this.file_name = dec.decode(decryptedFileName);
                    this.decryptFailure = false;
                    this.decryptSuccess = true;
                } catch (e) {
                    console.error(e)
                    this.decryptFailure = true;
                    this.decryptFailureMessage =
                        "An incorrect decryption passphrase was provided, please check that it is correct.";
                } finally {
                    this.downloading = false;
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
