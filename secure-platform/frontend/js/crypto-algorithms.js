'use strict';

var CryptoAlgorithms = (function () {
    function stringToBytes(str) {
        if (typeof TextEncoder !== 'undefined') {
            return new TextEncoder('utf-8').encode(str);
        }
        var bytes = [];
        for (var i = 0; i < str.length; i++) {
            var c = str.charCodeAt(i);
            if (c < 0x80) {
                bytes.push(c);
            } else if (c < 0x800) {
                bytes.push(0xc0 | (c >> 6));
                bytes.push(0x80 | (c & 0x3f));
            } else if (c < 0xd800 || c >= 0xe000) {
                bytes.push(0xe0 | (c >> 12));
                bytes.push(0x80 | ((c >> 6) & 0x3f));
                bytes.push(0x80 | (c & 0x3f));
            } else {
                i++;
                var c2 = str.charCodeAt(i);
                var code = 0x10000 + (((c & 0x3ff) << 10) | (c2 & 0x3ff));
                bytes.push(0xf0 | (code >> 18));
                bytes.push(0x80 | ((code >> 12) & 0x3f));
                bytes.push(0x80 | ((code >> 6) & 0x3f));
                bytes.push(0x80 | (code & 0x3f));
            }
        }
        return new Uint8Array(bytes);
    }

    function bytesToString(bytes) {
        if (typeof TextDecoder !== 'undefined') {
            try {
                return new TextDecoder('utf-8').decode(bytes);
            } catch (e) {
            }
        }
        var str = '';
        var i = 0;
        while (i < bytes.length) {
            var b = bytes[i];
            if (b < 0x80) {
                str += String.fromCharCode(b);
                i++;
            } else if (b < 0xe0) {
                str += String.fromCharCode(((b & 0x1f) << 6) | (bytes[i + 1] & 0x3f));
                i += 2;
            } else if (b < 0xf0) {
                str += String.fromCharCode(((b & 0x0f) << 12) | ((bytes[i + 1] & 0x3f) << 6) | (bytes[i + 2] & 0x3f));
                i += 3;
            } else {
                var code = ((b & 0x07) << 18) | ((bytes[i + 1] & 0x3f) << 12) | ((bytes[i + 2] & 0x3f) << 6) | (bytes[i + 3] & 0x3f);
                code -= 0x10000;
                str += String.fromCharCode(0xd800 + (code >> 10));
                str += String.fromCharCode(0xdc00 + (code & 0x3ff));
                i += 4;
            }
        }
        return str;
    }

    function bytesToBase64(bytes) {
        var binary = '';
        for (var i = 0; i < bytes.length; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return btoa(binary);
    }

    function base64ToBytes(base64Str) {
        var cleaned = base64Str.replace(/\s+/g, '');
        cleaned = cleaned.replace(/-/g, '+').replace(/_/g, '/');
        var padLen = (4 - (cleaned.length % 4)) % 4;
        for (var i = 0; i < padLen; i++) {
            cleaned += '=';
        }
        if (!/^[A-Za-z0-9+/=]+$/.test(cleaned)) {
            throw new Error('Base64字符串包含非法字符');
        }
        var binary = atob(cleaned);
        var bytes = new Uint8Array(binary.length);
        for (var j = 0; j < binary.length; j++) {
            bytes[j] = binary.charCodeAt(j);
        }
        return bytes;
    }

    function xorEncryptDecrypt(inputBytes, keyStr) {
        if (!keyStr || keyStr.length === 0) {
            throw new Error('XOR密钥不能为空');
        }
        var keyParts = keyStr.split('|').filter(function (p) { return p.length > 0; });
        if (keyParts.length === 0) {
            keyParts = [keyStr];
        }
        var result = new Uint8Array(inputBytes);
        for (var k = 0; k < keyParts.length; k++) {
            var keyBytes = stringToBytes(keyParts[k]);
            if (keyBytes.length === 0) continue;
            for (var i = 0; i < result.length; i++) {
                result[i] = result[i] ^ keyBytes[i % keyBytes.length];
            }
        }
        return result;
    }

    function base64Encode(str) {
        var bytes = stringToBytes(str);
        return bytesToBase64(bytes);
    }

    function base64Decode(encoded) {
        var bytes = base64ToBytes(encoded);
        return bytesToString(bytes);
    }

    function urlEncode(str) {
        return encodeURIComponent(str);
    }

    function urlDecode(encoded) {
        return decodeURIComponent(encoded);
    }

    function deriveKeyFromPassword(password, salt, iterations) {
        if (iterations === undefined) iterations = 100000;
        var passwordBytes = stringToBytes(password);
        return crypto.subtle.importKey(
            'raw',
            passwordBytes,
            { name: 'PBKDF2' },
            false,
            ['deriveBits', 'deriveKey']
        ).then(function (key) {
            return crypto.subtle.deriveKey(
                {
                    name: 'PBKDF2',
                    salt: salt,
                    iterations: iterations,
                    hash: 'SHA-256'
                },
                key,
                { name: 'AES-GCM', length: 256 },
                false,
                ['encrypt', 'decrypt']
            );
        });
    }

    async function aesGcmEncrypt(plaintext, password, ivInput) {
        if (!password || password.length === 0) {
            throw new Error('AES-GCM密码不能为空');
        }
        var plaintextBytes = stringToBytes(plaintext);
        var salt = crypto.getRandomValues(new Uint8Array(16));
        var iv;
        if (ivInput && ivInput.length > 0) {
            var ivBytes = stringToBytes(ivInput);
            if (ivBytes.length >= 12) {
                iv = ivBytes.slice(0, 12);
            } else {
                iv = new Uint8Array(12);
                iv.set(ivBytes);
            }
        } else {
            iv = crypto.getRandomValues(new Uint8Array(12));
        }
        var iterations = 100000;
        var key = await deriveKeyFromPassword(password, salt, iterations);
        var encrypted = await crypto.subtle.encrypt(
            { name: 'AES-GCM', iv: iv },
            key,
            plaintextBytes
        );
        var encBytes = new Uint8Array(encrypted);
        var result = new Uint8Array(2 + salt.length + iv.length + encBytes.length);
        var offset = 0;
        result[offset] = 0x01;
        result[offset + 1] = iterations >> 8;
        offset += 2;
        result.set(salt, offset);
        offset += salt.length;
        result.set(iv, offset);
        offset += iv.length;
        result.set(encBytes, offset);
        return bytesToBase64(result);
    }

    async function aesGcmDecrypt(ciphertextB64, password) {
        if (!password || password.length === 0) {
            throw new Error('AES-GCM密码不能为空');
        }
        var data = base64ToBytes(ciphertextB64);
        if (data.length < 2 + 16 + 12 + 16) {
            throw new Error('密文数据格式错误或太短');
        }
        var offset = 0;
        var version = data[offset];
        if (version !== 0x01) {
            throw new Error('不支持的密文版本');
        }
        var iterations = (data[offset + 1] << 8) | 100000;
        if (iterations < 1000) iterations = 100000;
        offset += 2;
        var salt = data.slice(offset, offset + 16);
        offset += 16;
        var iv = data.slice(offset, offset + 12);
        offset += 12;
        var encBytes = data.slice(offset);
        var key = await deriveKeyFromPassword(password, salt, iterations);
        try {
            var decrypted = await crypto.subtle.decrypt(
                { name: 'AES-GCM', iv: iv },
                key,
                encBytes
            );
            return bytesToString(new Uint8Array(decrypted));
        } catch (e) {
            throw new Error('解密失败：密码错误或密文已损坏');
        }
    }

    async function hybridEncrypt(plaintext, key, password) {
        if (!key || key.length === 0) {
            throw new Error('XOR密钥不能为空（混合加密需要XOR密钥）');
        }
        if (!password || password.length === 0) {
            throw new Error('AES密码不能为空（混合加密需要AES密码）');
        }
        var step1 = stringToBytes(plaintext);
        var step2 = xorEncryptDecrypt(step1, key);
        var step3 = bytesToBase64(step2);
        var step4 = await aesGcmEncrypt(step3, password, null);
        return step4;
    }

    async function hybridDecrypt(ciphertext, key, password) {
        if (!key || key.length === 0) {
            throw new Error('XOR密钥不能为空（混合加密需要XOR密钥）');
        }
        if (!password || password.length === 0) {
            throw new Error('AES密码不能为空（混合加密需要AES密码）');
        }
        var step1 = await aesGcmDecrypt(ciphertext, password);
        var step2 = base64ToBytes(step1);
        var step3 = xorEncryptDecrypt(step2, key);
        var step4 = bytesToString(step3);
        return step4;
    }

    return {
        stringToBytes: stringToBytes,
        bytesToString: bytesToString,
        bytesToBase64: bytesToBase64,
        base64ToBytes: base64ToBytes,
        xorEncryptDecrypt: xorEncryptDecrypt,
        base64Encode: base64Encode,
        base64Decode: base64Decode,
        urlEncode: urlEncode,
        urlDecode: urlDecode,
        aesGcmEncrypt: aesGcmEncrypt,
        aesGcmDecrypt: aesGcmDecrypt,
        hybridEncrypt: hybridEncrypt,
        hybridDecrypt: hybridDecrypt
    };
})();
