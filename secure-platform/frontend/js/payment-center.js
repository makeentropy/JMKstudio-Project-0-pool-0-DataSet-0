'use strict';

var PaymentCenter = (function () {
    var PAYMENT_PRODUCTS = {
        alipay: [
            { value: 'face-to-face', label: '当面付 (alipay.trade.pay) - 线下扫码枪扫码' },
            { value: 'precreate', label: '订单码支付 (alipay.trade.precreate) - 商家出示二维码' },
            { value: 'wap', label: '手机网站支付 (alipay.trade.wap.pay) - H5支付' },
            { value: 'page', label: '电脑网站支付 (alipay.trade.page.pay) - PC网页' },
            { value: 'jsapi', label: 'JSAPI支付 (小程序内) - 支付宝小程序' },
            { value: 'app', label: 'App支付 (alipay.trade.app.pay) - 原生App' },
            { value: 'pre-auth', label: '预授权支付 - 押金/资金冻结' },
            { value: 'deduct', label: '商家扣款 - 周期扣款/自动续费' }
        ],
        douyinpay: [
            { value: 'app', label: 'APP支付 - 原生App内唤起抖音' },
            { value: 'jsapi', label: 'JSAPI支付 - 抖音端内H5页面' },
            { value: 'h5', label: 'H5支付 - 手机浏览器网页' },
            { value: 'native', label: 'Native支付 - PC端扫码支付' }
        ]
    };

    function generateOrderNo() {
        var ts = Date.now();
        var rand = '';
        for (var i = 0; i < 6; i++) {
            rand += Math.floor(Math.random() * 10);
        }
        return 'SP' + ts + rand;
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

    function validatePaymentUrls() {
        var notifyEl = document.getElementById('payment-notifyurl');
        var returnEl = document.getElementById('payment-returnurl');
        var errors = [];
        if (notifyEl && notifyEl.value && notifyEl.value.trim()) {
            if (!validateUrl(notifyEl.value.trim())) {
                errors.push('异步通知地址格式不合法');
            }
            if (!/^https?:\/\//i.test(notifyEl.value.trim())) {
                errors.push('异步通知地址必须使用http://或https://协议');
            }
        }
        if (returnEl && returnEl.value && returnEl.value.trim()) {
            if (!validateUrl(returnEl.value.trim())) {
                errors.push('同步跳转地址格式不合法');
            }
            if (!/^https?:\/\//i.test(returnEl.value.trim())) {
                errors.push('同步跳转地址必须使用http://或https://协议');
            }
        }
        return errors;
    }

    function handlePaymentProviderChange() {
        var providerEl = document.getElementById('payment-provider');
        var productEl = document.getElementById('payment-product');
        if (!providerEl || !productEl) return;
        var provider = providerEl.value;
        while (productEl.firstChild) {
            productEl.removeChild(productEl.firstChild);
        }
        if (!provider) {
            var optNone = document.createElement('option');
            optNone.value = '';
            optNone.textContent = '请先选择支付渠道';
            productEl.appendChild(optNone);
            productEl.disabled = true;
            return;
        }
        productEl.disabled = false;
        var products = PAYMENT_PRODUCTS[provider] || [];
        var firstOption = document.createElement('option');
        firstOption.value = '';
        firstOption.textContent = '请选择支付产品';
        productEl.appendChild(firstOption);
        for (var i = 0; i < products.length; i++) {
            var opt = document.createElement('option');
            opt.value = products[i].value;
            opt.textContent = products[i].label;
            productEl.appendChild(opt);
        }
    }

    function showPaymentResult(success, title, details) {
        var panel = document.getElementById('payment-result');
        var content = document.getElementById('payment-result-content');
        if (!panel || !content) return;
        while (content.firstChild) {
            content.removeChild(content.firstChild);
        }
        var box = document.createElement('div');
        box.className = success ? 'success-box' : 'error-box';
        var boxTitle = document.createElement('p');
        boxTitle.style.fontWeight = '600';
        boxTitle.style.marginBottom = '12px';
        boxTitle.textContent = (success ? '\u2713 ' : '\u2717 ') + title;
        box.appendChild(boxTitle);
        if (details && typeof details === 'object') {
            var ul = document.createElement('ul');
            ul.className = 'result-list';
            var keys = Object.keys(details);
            for (var i = 0; i < keys.length; i++) {
                var li = document.createElement('li');
                var spanK = document.createElement('span');
                spanK.textContent = keys[i];
                var spanV = document.createElement('span');
                spanV.textContent = String(details[keys[i]]);
                li.appendChild(spanK);
                li.appendChild(spanV);
                ul.appendChild(li);
            }
            box.appendChild(ul);
        }
        content.appendChild(box);
        panel.classList.remove('hidden');
    }

    function getFieldValue(id) {
        var el = document.getElementById(id);
        return el ? el.value : '';
    }

    async function handlePaymentCreateOrder() {
        var provider = getFieldValue('payment-provider');
        var product = getFieldValue('payment-product');
        var subject = getFieldValue('payment-subject').trim();
        var amount = getFieldValue('payment-amount').trim();
        var outTradeNo = getFieldValue('payment-outtradeno').trim();
        var showToast = (typeof App !== 'undefined' && App.showToast) ? App.showToast : function () {};
        var apiFetch = (typeof App !== 'undefined' && App.apiFetch) ? App.apiFetch : null;

        if (!provider) {
            showToast('error', '参数错误', '请选择支付渠道');
            return;
        }
        if (!product) {
            showToast('error', '参数错误', '请选择支付产品');
            return;
        }
        if (!subject) {
            showToast('error', '参数错误', '请输入订单标题');
            return;
        }
        if (!amount || parseFloat(amount) <= 0) {
            showToast('error', '参数错误', '请输入有效的订单金额');
            return;
        }
        var urlErrors = validatePaymentUrls();
        if (urlErrors.length > 0) {
            showToast('error', '地址格式错误', urlErrors[0]);
            return;
        }
        if (!outTradeNo) {
            outTradeNo = generateOrderNo();
            var outEl = document.getElementById('payment-outtradeno');
            if (outEl) outEl.value = outTradeNo;
        }
        showToast('info', '创建订单中', '正在提交订单创建请求...');

        var payload = {
            provider: provider,
            product: product,
            env: getFieldValue('payment-env'),
            appid: getFieldValue('payment-appid').trim(),
            signType: getFieldValue('payment-signtype'),
            outTradeNo: outTradeNo,
            subject: subject,
            amount: amount,
            notifyUrl: getFieldValue('payment-notifyurl').trim(),
            returnUrl: getFieldValue('payment-returnurl').trim()
        };

        try {
            var response = null;
            if (apiFetch) {
                response = await apiFetch('/api/payment/create', {
                    method: 'POST',
                    body: payload
                });
            } else {
                throw new Error('API调用工具不可用');
            }
            var result = null;
            var contentType = response.headers.get('Content-Type');
            if (contentType && contentType.indexOf('application/json') !== -1) {
                result = await response.json();
            }
            if (response.ok && result && result.success) {
                showPaymentResult(true, '订单创建成功', {
                    '商户订单号': outTradeNo,
                    '支付渠道': provider,
                    '支付产品': product,
                    '订单金额': '¥' + amount,
                    '平台单号': result.tradeNo || '-',
                    '支付状态': '待支付'
                });
                showToast('success', '订单创建成功', '商户订单号: ' + outTradeNo);
            } else {
                var msg = (result && result.message) ? result.message : ('HTTP ' + response.status);
                showPaymentResult(false, '订单创建失败', {
                    '错误信息': msg,
                    '订单号': outTradeNo,
                    '建议': '签名必须在服务端完成，请确保后端服务正常运行'
                });
                showToast('warning', '创建请求已提交', '离线模式：请确保后端API服务运行');
            }
        } catch (e) {
            showPaymentResult(false, '请求失败', {
                '错误信息': e.message || '网络连接失败',
                '商户订单号': outTradeNo,
                '提示': '请检查后端API服务是否启动'
            });
            showToast('warning', '请求已准备', '离线模式：订单数据已准备，需后端实际处理');
        }
    }

    async function handlePaymentQuery() {
        var outTradeNo = getFieldValue('payment-outtradeno').trim();
        var provider = getFieldValue('payment-provider');
        var showToast = (typeof App !== 'undefined' && App.showToast) ? App.showToast : function () {};
        var apiFetch = (typeof App !== 'undefined' && App.apiFetch) ? App.apiFetch : null;

        if (!outTradeNo) {
            showToast('error', '参数错误', '请输入商户订单号');
            return;
        }
        if (!provider) {
            showToast('error', '参数错误', '请选择支付渠道');
            return;
        }
        showToast('info', '查询中', '正在查询订单状态...');
        try {
            var response = null;
            if (apiFetch) {
                response = await apiFetch('/api/payment/query', {
                    method: 'POST',
                    body: {
                        provider: provider,
                        outTradeNo: outTradeNo
                    }
                });
            } else {
                throw new Error('API调用工具不可用');
            }
            var result = null;
            var contentType = response.headers.get('Content-Type');
            if (contentType && contentType.indexOf('application/json') !== -1) {
                result = await response.json();
            }
            if (response.ok) {
                var tradeStatus = (result && result.tradeStatus) || '未知';
                showPaymentResult(true, '查询完成', {
                    '商户订单号': outTradeNo,
                    '支付渠道': provider,
                    '交易状态': tradeStatus,
                    '平台单号': (result && result.tradeNo) || '-',
                    '支付金额': (result && result.amount) ? '¥' + result.amount : '-'
                });
                showToast('success', '查询完成', '订单状态: ' + tradeStatus);
            } else {
                showPaymentResult(false, '查询失败', {
                    '订单号': outTradeNo,
                    '错误': 'HTTP ' + response.status,
                    '建议': '请使用后端查询接口或异步通知确认最终状态'
                });
                showToast('warning', '查询请求已提交', '前台结果不可信，需以后端查询或异步通知为准');
            }
        } catch (e) {
            showPaymentResult(false, '查询失败', {
                '错误信息': e.message || '网络连接失败',
                '安全提示': '前台结果不可信，必须以异步通知或服务端查询结果为准'
            });
            showToast('warning', '查询失败', e.message || '无法连接后端服务');
        }
    }

    function initPaymentEvents() {
        var providerEl = document.getElementById('payment-provider');
        if (providerEl) {
            providerEl.addEventListener('change', handlePaymentProviderChange);
        }
        var createBtn = document.getElementById('payment-create-order-btn');
        if (createBtn) {
            createBtn.addEventListener('click', handlePaymentCreateOrder);
        }
        var queryBtn = document.getElementById('payment-query-btn');
        if (queryBtn) {
            queryBtn.addEventListener('click', handlePaymentQuery);
        }
        var orderNoEl = document.getElementById('payment-outtradeno');
        if (orderNoEl && !orderNoEl.value) {
            orderNoEl.setAttribute('placeholder', '留空则自动生成: ' + generateOrderNo());
        }
    }

    return {
        init: initPaymentEvents,
        generateOrderNo: generateOrderNo,
        validatePaymentUrls: validatePaymentUrls,
        handlePaymentProviderChange: handlePaymentProviderChange,
        showPaymentResult: showPaymentResult,
        handlePaymentCreateOrder: handlePaymentCreateOrder,
        handlePaymentQuery: handlePaymentQuery
    };
})();
