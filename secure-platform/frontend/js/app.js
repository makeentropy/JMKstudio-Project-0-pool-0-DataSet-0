'use strict';

var App = (function () {
    var csrfToken = '';
    var currentTab = 'certificate';
    var certVerified = false;
    var toastTimerIds = [];

    function getMetaCSRFToken() {
        var metas = document.getElementsByTagName('meta');
        for (var i = 0; i < metas.length; i++) {
            var name = metas[i].getAttribute('name');
            if (name && name.toLowerCase() === 'csrf-token') {
                return metas[i].getAttribute('content') || '';
            }
        }
        return '';
    }

    function getCookie(name) {
        if (!document.cookie || document.cookie.length === 0) {
            return '';
        }
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var c = cookies[i].trim();
            if (c.indexOf(name + '=') === 0) {
                try {
                    return decodeURIComponent(c.substring(name.length + 1));
                } catch (e) {
                    return c.substring(name.length + 1);
                }
            }
        }
        return '';
    }

    function initCsrfToken() {
        var metaToken = getMetaCSRFToken();
        if (metaToken) {
            csrfToken = metaToken;
            return;
        }
        var cookieToken = getCookie('XSRF-TOKEN') || getCookie('csrf_token') || getCookie('csrftoken');
        if (cookieToken) {
            csrfToken = cookieToken;
        }
    }

    function getCsrfToken() {
        return csrfToken;
    }

    function validateUrl(url) {
        if (!url || typeof url !== 'string') {
            return false;
        }
        if (url.indexOf('javascript:') === 0) {
            return false;
        }
        if (url.indexOf('data:') === 0) {
            return false;
        }
        if (url.indexOf('vbscript:') === 0) {
            return false;
        }
        if (/^\s*javascript\s*:/i.test(url)) {
            return false;
        }
        return true;
    }

    async function apiFetch(url, options) {
        if (!validateUrl(url)) {
            throw new Error('非法的URL地址');
        }
        if (!options) options = {};
        if (!options.headers) options.headers = {};
        var headers = {};
        var headerKeys = Object.keys(options.headers);
        for (var i = 0; i < headerKeys.length; i++) {
            var k = headerKeys[i];
            headers[k] = options.headers[k];
        }
        if (!headers['Content-Type'] && options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
            headers['Content-Type'] = 'application/json';
        }
        if (csrfToken) {
            headers['X-CSRF-Token'] = csrfToken;
            headers['X-Requested-With'] = 'XMLHttpRequest';
        }
        var fetchOptions = {
            method: options.method || 'GET',
            headers: headers,
            credentials: 'same-origin',
            cache: 'no-store'
        };
        if (options.body) {
            if (options.body instanceof FormData || typeof options.body === 'string') {
                fetchOptions.body = options.body;
            } else {
                try {
                    fetchOptions.body = JSON.stringify(options.body);
                } catch (e) {
                    throw new Error('请求体序列化失败: ' + e.message);
                }
            }
        }
        var response = await fetch(url, fetchOptions);
        return response;
    }

    function showToast(type, title, message, duration) {
        if (!duration) duration = 4000;
        var container = document.getElementById('toast-container');
        if (!container) return;
        var toast = document.createElement('div');
        toast.className = 'toast ' + type;
        toast.setAttribute('role', 'alert');
        var icon = document.createElement('span');
        icon.className = 'toast-icon';
        var iconMap = {
            success: '\u2713',
            error: '\u2717',
            warning: '\u26A0',
            info: '\u2139'
        };
        icon.textContent = iconMap[type] || iconMap.info;
        toast.appendChild(icon);
        var content = document.createElement('div');
        content.className = 'toast-content';
        var titleEl = document.createElement('div');
        titleEl.className = 'toast-title';
        titleEl.textContent = title || '';
        content.appendChild(titleEl);
        if (message) {
            var msgEl = document.createElement('div');
            msgEl.className = 'toast-message';
            msgEl.textContent = message;
            content.appendChild(msgEl);
        }
        toast.appendChild(content);
        container.appendChild(toast);
        var toastId = Date.now() + Math.random();
        toastTimerIds.push(toastId);
        var removeFunc = function () {
            if (!toast.parentNode) return;
            toast.classList.add('leave');
            var removeAfterAnim = function () {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
                var idx = toastTimerIds.indexOf(toastId);
                if (idx !== -1) {
                    toastTimerIds.splice(idx, 1);
                }
            };
            setTimeout(removeAfterAnim, 300);
        };
        if (duration > 0) {
            setTimeout(removeFunc, duration);
        }
        toast.addEventListener('click', removeFunc);
        return { dismiss: removeFunc };
    }

    function switchTab(tabName) {
        if (!tabName || typeof tabName !== 'string') return;
        var validTabs = ['certificate', 'crypto', 'spectrum', 'payment'];
        if (validTabs.indexOf(tabName) === -1) return;
        currentTab = tabName;
        var tabBtns = document.querySelectorAll('.tab-btn');
        for (var i = 0; i < tabBtns.length; i++) {
            var btn = tabBtns[i];
            var btnTab = btn.getAttribute('data-tab');
            if (btnTab === tabName) {
                btn.classList.add('active');
                btn.setAttribute('aria-selected', 'true');
            } else {
                btn.classList.remove('active');
                btn.setAttribute('aria-selected', 'false');
            }
        }
        var panels = document.querySelectorAll('.tab-panel');
        for (var j = 0; j < panels.length; j++) {
            var panel = panels[j];
            var panelId = panel.id;
            var expectedId = 'tab-' + tabName;
            if (panelId === expectedId) {
                panel.classList.add('active');
            } else {
                panel.classList.remove('active');
            }
        }
        if (tabName === 'spectrum') {
            if (typeof Spectrum !== 'undefined' && Spectrum.refresh) {
                Spectrum.refresh();
            }
        }
    }

    function updateCertStatus(verified) {
        certVerified = !!verified;
        var indicator = document.getElementById('cert-status-indicator');
        var statusText = document.getElementById('cert-status-text');
        if (indicator) {
            if (certVerified) {
                indicator.classList.remove('status-disconnected');
                indicator.classList.add('status-connected');
            } else {
                indicator.classList.remove('status-connected');
                indicator.classList.add('status-disconnected');
            }
        }
        if (statusText) {
            statusText.textContent = certVerified ? '已认证' : '未认证';
        }
        applyAccessControl();
    }

    function applyAccessControl() {
        var gates = [
            { tab: 'crypto', gateId: 'crypto-gate', contentId: 'crypto-main-content' },
            { tab: 'spectrum', gateId: 'spectrum-gate', contentId: 'spectrum-main-content' },
            { tab: 'payment', gateId: 'payment-gate', contentId: 'payment-main-content' }
        ];
        for (var i = 0; i < gates.length; i++) {
            var cfg = gates[i];
            var gate = document.getElementById(cfg.gateId);
            var content = document.getElementById(cfg.contentId);
            if (!gate || !content) continue;
            if (certVerified) {
                gate.classList.add('hidden');
                content.classList.remove('hidden');
            } else {
                gate.classList.remove('hidden');
                content.classList.add('hidden');
            }
        }
    }

    function initTabEvents() {
        var tabBtns = document.querySelectorAll('.tab-btn');
        for (var i = 0; i < tabBtns.length; i++) {
            (function (btn) {
                btn.addEventListener('click', function () {
                    var tabName = btn.getAttribute('data-tab');
                    if (!tabName) return;
                    if (!certVerified && tabName !== 'certificate') {
                        showToast('warning', '访问受限', '请先在【证书校验】Tab上传并验证证书后访问其他模块');
                        switchTab('certificate');
                        return;
                    }
                    switchTab(tabName);
                });
            })(tabBtns[i]);
        }
    }

    function initGlobalErrorHandlers() {
        window.addEventListener('error', function (event) {
            var msg = event.message || '未知错误';
            var source = event.filename || '';
            var line = event.lineno || 0;
            var col = event.colno || 0;
            var errorLog = '[Error] ' + msg + ' (' + source + ':' + line + ':' + col + ')';
            try {
                if (typeof console !== 'undefined' && console.error) {
                    console.error(errorLog);
                }
            } catch (e) {
            }
        }, true);

        window.addEventListener('unhandledrejection', function (event) {
            var reason = '';
            try {
                if (event.reason) {
                    if (typeof event.reason === 'string') {
                        reason = event.reason;
                    } else if (event.reason.message) {
                        reason = event.reason.message;
                    } else {
                        reason = 'Promise rejection';
                    }
                }
            } catch (e) {
                reason = 'Unhandled promise rejection';
            }
            try {
                if (typeof console !== 'undefined' && console.warn) {
                    console.warn('[UnhandledRejection] ' + reason);
                }
            } catch (e2) {
            }
        });
    }

    function init() {
        initCsrfToken();
        initGlobalErrorHandlers();
        initTabEvents();

        if (typeof PaymentCenter !== 'undefined' && PaymentCenter.init) {
            PaymentCenter.init();
        }

        switchTab('certificate');

        if (typeof CertificateVerify !== 'undefined' && CertificateVerify.init) {
            CertificateVerify.init();
        }
        if (typeof CryptoTools !== 'undefined' && CryptoTools.init) {
            CryptoTools.init();
        }
        if (typeof Spectrum !== 'undefined' && Spectrum.init) {
            Spectrum.init();
        }

        var hasValid = false;
        if (typeof CertificateVerify !== 'undefined' && CertificateVerify.hasValidCertificate) {
            hasValid = CertificateVerify.hasValidCertificate();
        }

        updateCertStatus(hasValid);
        applyAccessControl();

        if (hasValid) {
            showToast('success', '认证状态已恢复', '检测到已验证证书，可访问所有模块');
        } else {
            showToast('info', '欢迎使用', '请先在【证书校验】模块上传并验证证书');
        }
    }

    return {
        init: init,
        switchTab: switchTab,
        updateCertStatus: updateCertStatus,
        getCsrfToken: getCsrfToken,
        showToast: showToast,
        apiFetch: apiFetch,
        validateUrl: validateUrl,
        hasValidCert: function () {
            return certVerified;
        }
    };
})();

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', App.init);
} else {
    App.init();
}
