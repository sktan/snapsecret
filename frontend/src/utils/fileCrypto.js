// Shared chunked AES-GCM file encryption helpers.
//
// Encrypt and decrypt sides must derive per-chunk IVs identically, so these
// constants/helpers are kept in one place rather than duplicated per view.

const enc = new TextEncoder();

export const CHUNK_SIZE = 16 * 1024 * 1024; // 16 MiB
export const GCM_TAG_BYTES = 16; // WebCrypto AES-GCM default 128-bit tag
export const PBKDF2_ITERATIONS = 600000; // OWASP-recommended floor for PBKDF2-HMAC-SHA256

// chunkIv = fileIvPrefix (8 bytes) || big-endian uint32 chunk index (4 bytes)
// Never stored: both sides derive it from fileIvPrefix + loop counter.
export function buildChunkIv(fileIvPrefix, index) {
    const iv = new Uint8Array(12);
    iv.set(fileIvPrefix, 0);
    new DataView(iv.buffer).setUint32(8, index, false);
    return iv;
}

export async function getKey(passphrase, salt) {
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
            iterations: PBKDF2_ITERATIONS,
            hash: "SHA-256",
        },
        keyMaterial,
        { name: "AES-GCM", length: 256 },
        true,
        ["encrypt", "decrypt"]
    );
}
