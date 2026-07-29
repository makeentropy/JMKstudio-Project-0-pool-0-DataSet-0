'use strict';

var CertificateVerify = (function () {
    var STORAGE_KEY = 'secure_platform_verified_fingerprints';
    var currentCertData = null;
    var currentFingerprint = null;

    function getStoredFingerprints() {
        try {
            var raw = sessionStorage.getItem(STORAGE_KEY);
            if (!raw) return [];
            var arr = JSON.parse(raw);
            if (!Array.isArray(arr)) return [];
            return arr.filter(function (item) {
                return typeof item === 'string' && item.length > 0;
            });
        } catch (e) {
            return [];
        }
    }

    function saveFingerprint(fingerprint) {
        if (!fingerprint || typeof fingerprint !== 'string') return false;
        var prints = getStoredFingerprints();
        if (prints.indexOf(fingerprint) === -1) {
            prints.unshift(fingerprint);
            if (prints.length > 10) {
                prints = prints.slice(0, 10);
            }
        }
        try {
            sessionStorage.setItem(STORAGE_KEY, JSON.stringify(prints));
            return true;
        } catch (e) {
            return false;
        }
    }

    function hasValidCertificate() {
        var prints = getStoredFingerprints();
        return prints.length > 0;
    }

    function clearStoredFingerprints() {
        try {
            sessionStorage.removeItem(STORAGE_KEY);
            return true;
        } catch (e) {
            return false;
        }
    }

    function setTextContent(elementId, text) {
        var el = document.getElementById(elementId);
        if (el) {
            el.textContent = text;
        }
    }

    function showElement(elementId) {
        var el = document.getElementById(elementId);
        if (el) {
            el.classList.remove('hidden');
        }
    }

    function hideElement(elementId) {
        var el = document.getElementById(elementId);
        if (el) {
            el.classList.add('hidden');
        }
    }

    function updateCertInfoDisplay(certInfo, fingerprint) {
        if (!certInfo) return;
        setTextContent('cert-subject', certInfo.subject || '-');
        setTextContent('cert-issuer', certInfo.issuer || '-');
        setTextContent('cert-serial', certInfo.serialNumber || '-');
        setTextContent('cert-not-before', certInfo.notBefore || '-');
        setTextContent('cert-not-after', certInfo.notAfter || '-');
        setTextContent('cert-sig-alg', certInfo.signatureAlgorithm || '-');
        setTextContent('cert-pubkey-alg', certInfo.pubKeyAlgorithm || '-');
        setTextContent('cert-pubkey-size', certInfo.pubKeySize || '-');
        setTextContent('cert-fingerprint', fingerprint || '-');
        hideElement('cert-info-empty');
        showElement('cert-info-table');
    }

    function clearCertInfoDisplay() {
        var fields = ['cert-subject', 'cert-issuer', 'cert-serial', 'cert-not-before',
            'cert-not-after', 'cert-sig-alg', 'cert-fingerprint', 'cert-pubkey-alg', 'cert-pubkey-size'];
        for (var i = 0; i < fields.length; i++) {
            setTextContent(fields[i], '-');
        }
        showElement('cert-info-empty');
        hideElement('cert-info-table');
    }

    function updateFingerprintHistory() {
        var prints = getStoredFingerprints();
        var historyEl = document.getElementById('cert-history');
        var listEl = document.getElementById('cert-fingerprint-list');
        if (!historyEl || !listEl) return;
        if (prints.length === 0) {
            historyEl.classList.add('hidden');
            return;
        }
        while (listEl.firstChild) {
            listEl.removeChild(listEl.firstChild);
        }
        for (var i = 0; i < prints.length; i++) {
            var li = document.createElement('li');
            li.textContent = prints[i];
            listEl.appendChild(li);
        }
        historyEl.classList.remove('hidden');
    }

    async function parsePEMContent(pemContent) {
        if (!pemContent || !pemContent.trim()) {
            throw new Error('请输入PEM证书内容');
        }
        var derBytes = CertificateASN1.pemToDer(pemContent);
        var fingerprint = await CertificateASN1.calculateSHA256Fingerprint(derBytes);
        var certInfo = CertificateASN1.parseCertificate(derBytes);
        currentCertData = pemContent;
        currentFingerprint = fingerprint;
        updateCertInfoDisplay(certInfo, fingerprint);
        return { certInfo: certInfo, fingerprint: fingerprint, derBytes: derBytes };
    }

    async function verifyCertificateOnline() {
        if (!currentCertData) {
            throw new Error('请先上传并解析证书');
        }
        var payload = {
            certificate: currentCertData,
            fingerprint: currentFingerprint
        };
        try {
            var fetchFn = (typeof App !== 'undefined' && App.apiFetch) ? App.apiFetch : fetch;
            var opts = {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify(payload)
            };
            if (typeof App !== 'undefined' && App.getCsrfToken) {
                opts.headers['X-CSRF-Token'] = App.getCsrfToken() || '';
            }
            var response = await fetchFn('/api/certificate/verify', opts);
            var result = null;
            var contentType = response.headers.get('Content-Type');
            if (contentType && contentType.indexOf('application/json') !== -1) {
                result = await response.json();
            } else {
                result = {
                    success: response.ok,
                    message: response.ok ? '证书校验请求已发送' : '请求失败: HTTP ' + response.status
                };
            }
            return result;
        } catch (e) {
            return {
                success: false,
                message: '网络请求失败: ' + e.message,
                offline: true
            };
        }
    }

    function showVerifyResult(result) {
        var container = document.getElementById('cert-verify-result');
        var content = document.getElementById('cert-verify-content');
        if (!container || !content) return;
        while (content.firstChild) {
            content.removeChild(content.firstChild);
        }
        if (result.success) {
            if (currentFingerprint) {
                saveFingerprint(currentFingerprint);
            }
            if (typeof App !== 'undefined' && App.updateCertStatus) {
                App.updateCertStatus(true);
            }
            var successBox = document.createElement('div');
            successBox.className = 'success-box';
            var title = document.createElement('p');
            title.style.fontWeight = '600';
            title.style.marginBottom = '12px';
            title.textContent = result.offline ? '\u2713 证书解析成功（离线模式）' : '\u2713 证书校验通过';
            successBox.appendChild(title);
            if (result.message) {
                var msg = document.createElement('p');
                msg.style.fontSize = '13px';
                msg.textContent = result.message;
                successBox.appendChild(msg);
            }
            if (result.details) {
                var detailsList = document.createElement('ul');
                detailsList.className = 'result-list';
                detailsList.style.marginTop = '12px';
                for (var key in result.details) {
                    if (Object.prototype.hasOwnProperty.call(result.details, key)) {
                        var li = document.createElement('li');
                        var span1 = document.createElement('span');
                        span1.textContent = key;
                        var span2 = document.createElement('span');
                        span2.textContent = String(result.details[key]);
                        li.appendChild(span1);
                        li.appendChild(span2);
                        detailsList.appendChild(li);
                    }
                }
                successBox.appendChild(detailsList);
            }
            content.appendChild(successBox);
        } else {
            var errorBox = document.createElement('div');
            errorBox.className = 'error-box';
            var errTitle = document.createElement('p');
            errTitle.style.fontWeight = '600';
            errTitle.style.marginBottom = '12px';
            errTitle.textContent = '\u2717 校验失败';
            errorBox.appendChild(errTitle);
            if (result.message) {
                var errMsg = document.createElement('p');
                errMsg.style.fontSize = '13px';
                errMsg.textContent = result.message;
                errorBox.appendChild(errMsg);
            }
            if (result.errorCode) {
                var code = document.createElement('p');
                code.style.fontSize = '12px';
                code.style.marginTop = '8px';
                code.style.fontFamily = 'var(--font-mono)';
                code.textContent = '错误码: ' + result.errorCode;
                errorBox.appendChild(code);
            }
            content.appendChild(errorBox);
        }
        container.classList.remove('hidden');
        updateFingerprintHistory();
    }

    function handleFileSelect(evt) {
        var files = evt.target.files;
        if (!files || files.length === 0) return;
        var file = files[0];
        var showToastFn = (typeof App !== 'undefined' && App.showToast) ? App.showToast : function(){};
        if (file.size > 10 * 1024 * 1024) {
            showToastFn('error', '文件过大', '证书文件不能超过10MB');
            return;
        }
        var reader = new FileReader();
        reader.onload = function (e) {
            var content = e.target.result;
            var pasteArea = document.getElementById('cert-paste-area');
            if (pasteArea) {
                pasteArea.value = content;
            }
            showToastFn('info', '文件已加载', '文件 "' + file.name + '" 已加载，请点击"解析证书"');
        };
        reader.onerror = function () {
            showToastFn('error', '读取失败', '无法读取文件');
        };
        reader.readAsText(file);
    }

    async function handleParseClick() {
        var pasteArea = document.getElementById('cert-paste-area');
        var content = pasteArea ? pasteArea.value : '';
        var showToastFn = (typeof App !== 'undefined' && App.showToast) ? App.showToast : function(){};
        try {
            hideElement('cert-verify-result');
            var result = await parsePEMContent(content);
            showToastFn('success', '解析成功', '证书解析完成，SHA-256指纹: ' + result.fingerprint.substring(0, 24) + '...');
        } catch (e) {
            clearCertInfoDisplay();
            showToastFn('error', '解析失败', e.message);
        }
    }

    async function handleVerifyClick() {
        var showToastFn = (typeof App !== 'undefined' && App.showToast) ? App.showToast : function(){};
        try {
            if (!currentCertData) {
                var pasteArea = document.getElementById('cert-paste-area');
                var content = pasteArea ? pasteArea.value : '';
                if (!content.trim()) {
                    throw new Error('请先上传或粘贴证书内容并解析');
                }
                await parsePEMContent(content);
            }
            showToastFn('info', '校验中', '正在向服务器提交证书校验请求...');
            var result = await verifyCertificateOnline();
            if (result.offline && currentFingerprint) {
                saveFingerprint(currentFingerprint);
                if (typeof App !== 'undefined' && App.updateCertStatus) {
                    App.updateCertStatus(true);
                }
                updateFingerprintHistory();
            }
            showVerifyResult(result);
            if (result.success) {
                showToastFn('success', '校验完成', '证书验证通过，已授予访问权限');
            }
        } catch (e) {
            showToastFn('error', '校验失败', e.message);
        }
    }

    function handleClearClick() {
        var pasteArea = document.getElementById('cert-paste-area');
        var fileInput = document.getElementById('cert-file-input');
        if (pasteArea) pasteArea.value = '';
        if (fileInput) fileInput.value = '';
        currentCertData = null;
        currentFingerprint = null;
        clearCertInfoDisplay();
        hideElement('cert-verify-result');
        var showToastFn = (typeof App !== 'undefined' && App.showToast) ? App.showToast : function(){};
        showToastFn('info', '已清除', '证书输入区域已清空');
    }

    function initEvents() {
        var fileInput = document.getElementById('cert-file-input');
        if (fileInput) {
            fileInput.addEventListener('change', handleFileSelect);
        }
        var parseBtn = document.getElementById('cert-parse-btn');
        if (parseBtn) {
            parseBtn.addEventListener('click', handleParseClick);
        }
        var verifyBtn = document.getElementById('cert-verify-btn');
        if (verifyBtn) {
            verifyBtn.addEventListener('click', handleVerifyClick);
        }
        var clearBtn = document.getElementById('cert-clear-btn');
        if (clearBtn) {
            clearBtn.addEventListener('click', handleClearClick);
        }
    }

    function checkAndApplyAccessControl() {
        var valid = hasValidCertificate();
        if (typeof App !== 'undefined' && App.updateCertStatus) {
            App.updateCertStatus(valid);
        }
        updateFingerprintHistory();
        return valid;
    }

    return {
        init: function () {
            initEvents();
            checkAndApplyAccessControl();
        },
        hasValidCertificate: hasValidCertificate,
        getStoredFingerprints: getStoredFingerprints,
        saveFingerprint: saveFingerprint,
        clearStoredFingerprints: clearStoredFingerprints,
        checkAndApplyAccessControl: checkAndApplyAccessControl,
        updateFingerprintHistory: updateFingerprintHistory
    };
})();
