import './style.css';

const API_TOKEN = 'baseXOR_jmk_api_token_2026';
const CARD_PRICE = '29.90';

function xorCrypt(data: string, key: string): string {
  const encoder = new TextEncoder();
  const dataBytes = encoder.encode(data);
  const keyBytes = encoder.encode(key);
  const result = new Uint8Array(dataBytes.length);

  for (let i = 0; i < dataBytes.length; i++) {
    result[i] = dataBytes[i] ^ keyBytes[i % keyBytes.length];
  }

  return btoa(String.fromCharCode(...result));
}

function jmkXorSign(tagId: string): string {
  const expireTs = Math.floor(Date.now() / 1000) + 3600;
  const rawPayload = `${tagId}|${expireTs}|${API_TOKEN}`;
  return xorCrypt(rawPayload, API_TOKEN);
}

function showStatus(msg: string, type: 'success' | 'error') {
  const statusEl = document.getElementById('statusMsg');
  if (!statusEl) return;
  statusEl.textContent = msg;
  statusEl.className = `status-message ${type}`;
  setTimeout(() => {
    statusEl.className = 'status-message';
  }, 5000);
}

async function createOrder() {
  const payBtn = document.getElementById('payBtn') as HTMLButtonElement;
  if (!payBtn) return;

  payBtn.disabled = true;
  payBtn.textContent = '创建订单中...';

  try {
    const sign = jmkXorSign('create_order');
    const response = await fetch('/shop-api/order/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        price: CARD_PRICE,
        subject: 'theme_premium',
        sign: sign,
      }),
    });

    const data = await response.json();

    if (response.ok && data.order_id) {
      showStatus(`订单创建成功！订单号: ${data.order_id}`, 'success');

      setTimeout(async () => {
        try {
          const callbackSign = jmkXorSign(data.order_id);
          const callbackRes = await fetch('/shop-api/order/callback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              order_id: data.order_id,
              trade_no: 'sim_' + Date.now(),
              sign: callbackSign,
            }),
          });

          const callbackData = await callbackRes.json();
          if (callbackData.code === 0) {
            const cardInput = document.getElementById('cardInput') as HTMLInputElement;
            if (cardInput) {
              cardInput.value = callbackData.card_key;
            }
            showStatus(`支付成功！卡密: ${callbackData.card_key}`, 'success');
          }
        } catch {
          console.error('Callback failed');
        }
      }, 1500);
    } else {
      showStatus(data.msg || '订单创建失败', 'error');
    }
  } catch {
    showStatus('网络错误，请稍后重试', 'error');
  } finally {
    payBtn.disabled = false;
    payBtn.textContent = '立即购买';
  }
}

async function activateTag() {
  const cardInput = document.getElementById('cardInput') as HTMLInputElement;
  const activeBtn = document.getElementById('activeBtn') as HTMLButtonElement;

  if (!cardInput || !activeBtn) return;

  const cardKey = cardInput.value.trim();
  if (!cardKey) {
    showStatus('请输入卡密', 'error');
    return;
  }

  activeBtn.disabled = true;
  activeBtn.textContent = '激活中...';

  try {
    const response = await fetch('/server-bin/tag/active', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ card_key: cardKey }),
    });

    const data = await response.json();

    if (data.code === 0) {
      showStatus(`标签激活成功！有效期至: ${new Date(data.expire_at * 1000).toLocaleDateString()}`, 'success');
    } else {
      showStatus(data.msg || '激活失败', 'error');
    }
  } catch {
    showStatus('网络错误，请稍后重试', 'error');
  } finally {
    activeBtn.disabled = false;
    activeBtn.textContent = '激活标签';
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const payBtn = document.getElementById('payBtn');
  const activeBtn = document.getElementById('activeBtn');
  const cardInput = document.getElementById('cardInput');

  if (payBtn) {
    payBtn.addEventListener('click', createOrder);
  }

  if (activeBtn) {
    activeBtn.addEventListener('click', activateTag);
  }

  if (cardInput) {
    cardInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        activateTag();
      }
    });
  }
});
