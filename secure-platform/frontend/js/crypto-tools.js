'use strict';

var CryptoTools = (function () {
    var currentAlgorithm = 'xor';
    var currentMode = 'encrypt';

    function setOutput(text, isError) {
        var outputEl = document.getElementById('crypto-output');
        var statusEl = document.getElementById('crypto-status');
        var outputLenEl = document.getElementById('crypto-output-length');
        if (outputEl) {
            outputEl.value = text;
        }
        if (outputLenEl) {
            outputLenEl.textContent = '字符数: ' + (text ? text.length : 0);
        }
        if (statusEl) {
            if (isError) {
                statusEl.textContent = '\u2717 处理失败';
                statusEl.className = 'crypto-status error';
            } else {
                statusEl.textContent = '\u2713 处理成功';
                statusEl.className = 'crypto-status success';
            }
        }
    }

    function updateInputLength() {
        var inputEl = document.getElementById('crypto-input');
        var lenEl = document.getElementById('crypto-input-length');
        if (inputEl && lenEl) {
            lenEl.textContent = '字符数: ' + (inputEl.value ? inputEl.value.length : 0);
        }
    }

    function getFieldValue(id) {
        var el = document.getElementById(id);
        return el ? el.value : '';
    }

    function validateAlgorithmNeeds(algorithm, mode) {
        var key = getFieldValue('crypto-key');
        var password = getFieldValue('crypto-password');
        var errors = [];
        switch (algorithm) {
            case 'xor':
                if (!key || key.length === 0) {
                    errors.push('XOR算法需要填写"密钥"字段');
                }
                break;
            case 'aes-gcm':
                if (!password || password.length === 0) {
                    errors.push('AES-GCM算法需要填写"密码"字段');
                }
                break;
            case 'hybrid':
                if (!key || key.length === 0) {
                    errors.push('混合加密需要填写"密钥"字段（XOR层）');
                }
                if (!password || password.length === 0) {
                    errors.push('混合加密需要填写"密码"字段（AES层）');
                }
                break;
            default:
                break;
        }
        return errors;
    }

    async function processData() {
        var algorithm = getFieldValue('crypto-algorithm');
        var mode = getFieldValue('crypto-mode');
        var input = getFieldValue('crypto-input');
        var key = getFieldValue('crypto-key');
        var password = getFieldValue('crypto-password');
        var iv = getFieldValue('crypto-iv');
        var showToastFn = (typeof App !== 'undefined' && App.showToast) ? App.showToast : function(){};

        currentAlgorithm = algorithm;
        currentMode = mode;

        if (!input || input.length === 0) {
            setOutput('', false);
            showToastFn('warning', '无输入', '请先输入需要处理的文本');
            return;
        }

        var errors = validateAlgorithmNeeds(algorithm, mode);
        if (errors.length > 0) {
            setOutput('', true);
            var statusEl = document.getElementById('crypto-status');
            if (statusEl) {
                statusEl.textContent = '\u2717 ' + errors[0];
                statusEl.className = 'crypto-status error';
            }
            showToastFn('error', '参数错误', errors[0]);
            return;
        }

        try {
            var result = '';
            switch (algorithm) {
                case 'xor':
                    var inputBytes = CryptoAlgorithms.stringToBytes(input);
                    var outputBytes = CryptoAlgorithms.xorEncryptDecrypt(inputBytes, key);
                    if (mode === 'encrypt') {
                        result = CryptoAlgorithms.bytesToBase64(outputBytes);
                    } else {
                        var xorInputBytes;
                        try {
                            xorInputBytes = CryptoAlgorithms.base64ToBytes(input);
                            var decryptedBytes = CryptoAlgorithms.xorEncryptDecrypt(xorInputBytes, key);
                            result = CryptoAlgorithms.bytesToString(decryptedBytes);
                        } catch (e) {
                            var decryptedBytes2 = CryptoAlgorithms.xorEncryptDecrypt(inputBytes, key);
                            result = CryptoAlgorithms.bytesToBase64(decryptedBytes2);
                            showToastFn('info', '提示', '输入不是有效的Base64，已按原始文本进行XOR处理并输出Base64');
                        }
                    }
                    break;
                case 'base64':
                    if (mode === 'encrypt') {
                        result = CryptoAlgorithms.base64Encode(input);
                    } else {
                        result = CryptoAlgorithms.base64Decode(input);
                    }
                    break;
                case 'url':
                    if (mode === 'encrypt') {
                        result = CryptoAlgorithms.urlEncode(input);
                    } else {
                        result = CryptoAlgorithms.urlDecode(input);
                    }
                    break;
                case 'aes-gcm':
                    if (mode === 'encrypt') {
                        result = await CryptoAlgorithms.aesGcmEncrypt(input, password, iv);
                    } else {
                        result = await CryptoAlgorithms.aesGcmDecrypt(input, password);
                    }
                    break;
                case 'hybrid':
                    if (mode === 'encrypt') {
                        result = await CryptoAlgorithms.hybridEncrypt(input, key, password);
                    } else {
                        result = await CryptoAlgorithms.hybridDecrypt(input, key, password);
                    }
                    break;
                default:
                    throw new Error('不支持的算法: ' + algorithm);
            }
            setOutput(result, false);
        } catch (e) {
            setOutput('', true);
            var statusEl2 = document.getElementById('crypto-status');
            if (statusEl2) {
                statusEl2.textContent = '\u2717 ' + (e.message || '处理失败');
                statusEl2.className = 'crypto-status error';
            }
            showToastFn('error', '处理失败', e.message || '未知错误');
        }
    }

    function handleAlgorithmChange() {
        var algorithm = getFieldValue('crypto-algorithm');
        var keyInput = document.getElementById('crypto-key');
        var passwordInput = document.getElementById('crypto-password');
        var ivInput = document.getElementById('crypto-iv');
        if (!keyInput || !passwordInput || !ivInput) return;
        keyInput.disabled = false;
        passwordInput.disabled = false;
        ivInput.disabled = false;
        switch (algorithm) {
            case 'base64':
            case 'url':
                keyInput.disabled = true;
                passwordInput.disabled = true;
                ivInput.disabled = true;
                break;
            case 'xor':
                passwordInput.disabled = true;
                ivInput.disabled = true;
                break;
            case 'aes-gcm':
                keyInput.disabled = true;
                break;
            default:
                break;
        }
    }

    function handleModeChange() {
        var mode = getFieldValue('crypto-mode');
        var processBtn = document.getElementById('crypto-process-btn');
        if (processBtn) {
            processBtn.textContent = mode === 'encrypt' ? '执行加密 / 编码' : '执行解密 / 解码';
        }
    }

    function handleClearInput() {
        var inputEl = document.getElementById('crypto-input');
        if (inputEl) {
            inputEl.value = '';
        }
        updateInputLength();
        setOutput('', false);
        var statusEl = document.getElementById('crypto-status');
        if (statusEl) {
            statusEl.textContent = '';
            statusEl.className = 'crypto-status';
        }
    }

    async function handleCopyOutput() {
        var outputEl = document.getElementById('crypto-output');
        var showToastFn = (typeof App !== 'undefined' && App.showToast) ? App.showToast : function(){};
        if (!outputEl || !outputEl.value) {
            showToastFn('warning', '无内容', '输出区为空，没有可复制的内容');
            return;
        }
        try {
            if (navigator.clipboard && navigator.clipboard.writeText) {
                await navigator.clipboard.writeText(outputEl.value);
            } else {
                outputEl.select();
                document.execCommand('copy');
                window.getSelection().removeAllRanges();
            }
            showToastFn('success', '复制成功', '结果已复制到剪贴板');
        } catch (e) {
            showToastFn('error', '复制失败', e.message || '请手动复制');
        }
    }

    function initEvents() {
        var algSelect = document.getElementById('crypto-algorithm');
        if (algSelect) {
            algSelect.addEventListener('change', handleAlgorithmChange);
        }
        var modeSelect = document.getElementById('crypto-mode');
        if (modeSelect) {
            modeSelect.addEventListener('change', handleModeChange);
        }
        var processBtn = document.getElementById('crypto-process-btn');
        if (processBtn) {
            processBtn.addEventListener('click', processData);
        }
        var clearBtn = document.getElementById('crypto-clear-input');
        if (clearBtn) {
            clearBtn.addEventListener('click', handleClearInput);
        }
        var copyBtn = document.getElementById('crypto-copy-output');
        if (copyBtn) {
            copyBtn.addEventListener('click', handleCopyOutput);
        }
        var inputEl = document.getElementById('crypto-input');
        if (inputEl) {
            inputEl.addEventListener('input', updateInputLength);
        }
        handleAlgorithmChange();
        handleModeChange();
    }

    return {
        init: function () {
            initEvents();
        },
        processData: processData
    };
})();
