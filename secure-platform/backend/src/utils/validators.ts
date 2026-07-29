export interface ValidationResult {
  valid: boolean;
  message?: string;
}

export const EMAIL_REGEX = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
export const AMOUNT_REGEX = /^\d+(\.\d{1,2})?$/;
export const ORDER_NO_REGEX = /^[A-Za-z0-9_-]{8,64}$/;
export const CERT_SN_REGEX = /^[A-Fa-f0-9]{16,64}$/;
export const PHONE_REGEX = /^1[3-9]\d{9}$/;
export const ALIPAY_TRADE_NO_REGEX = /^20\d{2}[01]\d[0-3]\d{13,}$/;
export const JWT_TOKEN_REGEX = /^[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+$/;
export const URL_SAFE_REGEX = /^[A-Za-z0-9_-]+$/;
export const HEX_COLOR_REGEX = /^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$/;
export const IPV4_REGEX = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
export const UUID_REGEX = /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$/;

export const MIN_AMOUNT = 0.01;
export const MAX_AMOUNT = 1000000;
export const MIN_ORDER_NO_LENGTH = 8;
export const MAX_ORDER_NO_LENGTH = 64;

export const validateEmail = (email: unknown): ValidationResult => {
  if (typeof email !== 'string') {
    return { valid: false, message: '邮箱必须为字符串类型' };
  }
  if (email.length === 0) {
    return { valid: false, message: '邮箱不能为空' };
  }
  if (email.length > 254) {
    return { valid: false, message: '邮箱长度不能超过254个字符' };
  }
  if (!EMAIL_REGEX.test(email)) {
    return { valid: false, message: '邮箱格式不正确' };
  }
  return { valid: true };
};

export const validateAmount = (amount: unknown): ValidationResult => {
  if (amount === null || amount === undefined || amount === '') {
    return { valid: false, message: '金额不能为空' };
  }
  const numAmount = typeof amount === 'string' ? parseFloat(amount) : Number(amount);
  if (isNaN(numAmount)) {
    return { valid: false, message: '金额必须为有效数字' };
  }
  const strAmount = typeof amount === 'string' ? amount : String(amount);
  if (!AMOUNT_REGEX.test(strAmount)) {
    return { valid: false, message: '金额格式不正确，最多保留2位小数' };
  }
  if (numAmount < MIN_AMOUNT) {
    return { valid: false, message: `金额不能小于${MIN_AMOUNT}` };
  }
  if (numAmount > MAX_AMOUNT) {
    return { valid: false, message: `金额不能大于${MAX_AMOUNT}` };
  }
  return { valid: true };
};

export const validateOrderNo = (orderNo: unknown): ValidationResult => {
  if (typeof orderNo !== 'string') {
    return { valid: false, message: '订单号必须为字符串类型' };
  }
  if (orderNo.length === 0) {
    return { valid: false, message: '订单号不能为空' };
  }
  if (orderNo.length < MIN_ORDER_NO_LENGTH) {
    return { valid: false, message: `订单号长度不能少于${MIN_ORDER_NO_LENGTH}个字符` };
  }
  if (orderNo.length > MAX_ORDER_NO_LENGTH) {
    return { valid: false, message: `订单号长度不能超过${MAX_ORDER_NO_LENGTH}个字符` };
  }
  if (!ORDER_NO_REGEX.test(orderNo)) {
    return { valid: false, message: '订单号格式不正确，只能包含字母、数字、下划线和短横线' };
  }
  return { valid: true };
};

export const validateCertSn = (certSn: unknown): ValidationResult => {
  if (typeof certSn !== 'string') {
    return { valid: false, message: '证书序列号必须为字符串类型' };
  }
  if (certSn.length === 0) {
    return { valid: false, message: '证书序列号不能为空' };
  }
  if (!CERT_SN_REGEX.test(certSn)) {
    return { valid: false, message: '证书序列号格式不正确，应为16-64位十六进制字符串' };
  }
  return { valid: true };
};

export const validatePhone = (phone: unknown): ValidationResult => {
  if (typeof phone !== 'string') {
    return { valid: false, message: '手机号必须为字符串类型' };
  }
  if (phone.length === 0) {
    return { valid: false, message: '手机号不能为空' };
  }
  if (!PHONE_REGEX.test(phone)) {
    return { valid: false, message: '手机号格式不正确' };
  }
  return { valid: true };
};

export const validateAlipayTradeNo = (tradeNo: unknown): ValidationResult => {
  if (typeof tradeNo !== 'string') {
    return { valid: false, message: '支付宝交易号必须为字符串类型' };
  }
  if (tradeNo.length === 0) {
    return { valid: false, message: '支付宝交易号不能为空' };
  }
  if (!ALIPAY_TRADE_NO_REGEX.test(tradeNo)) {
    return { valid: false, message: '支付宝交易号格式不正确' };
  }
  return { valid: true };
};

export const validateJwtToken = (token: unknown): ValidationResult => {
  if (typeof token !== 'string') {
    return { valid: false, message: 'JWT令牌必须为字符串类型' };
  }
  if (token.length === 0) {
    return { valid: false, message: 'JWT令牌不能为空' };
  }
  if (!JWT_TOKEN_REGEX.test(token)) {
    return { valid: false, message: 'JWT令牌格式不正确' };
  }
  return { valid: true };
};

export const validateStringLength = (
  value: unknown,
  min: number,
  max: number,
  fieldName: string = '字符串'
): ValidationResult => {
  if (typeof value !== 'string') {
    return { valid: false, message: `${fieldName}必须为字符串类型` };
  }
  if (value.length < min) {
    return { valid: false, message: `${fieldName}长度不能少于${min}个字符` };
  }
  if (value.length > max) {
    return { valid: false, message: `${fieldName}长度不能超过${max}个字符` };
  }
  return { valid: true };
};

export const validateUrlSafeString = (value: unknown, fieldName: string = '标识'): ValidationResult => {
  if (typeof value !== 'string') {
    return { valid: false, message: `${fieldName}必须为字符串类型` };
  }
  if (value.length === 0) {
    return { valid: false, message: `${fieldName}不能为空` };
  }
  if (!URL_SAFE_REGEX.test(value)) {
    return { valid: false, message: `${fieldName}只能包含字母、数字、下划线和短横线` };
  }
  return { valid: true };
};

export const validateUuid = (uuid: unknown): ValidationResult => {
  if (typeof uuid !== 'string') {
    return { valid: false, message: 'UUID必须为字符串类型' };
  }
  if (uuid.length === 0) {
    return { valid: false, message: 'UUID不能为空' };
  }
  if (!UUID_REGEX.test(uuid)) {
    return { valid: false, message: 'UUID格式不正确' };
  }
  return { valid: true };
};

export const validateIpv4 = (ip: unknown): ValidationResult => {
  if (typeof ip !== 'string') {
    return { valid: false, message: 'IP地址必须为字符串类型' };
  }
  if (ip.length === 0) {
    return { valid: false, message: 'IP地址不能为空' };
  }
  if (!IPV4_REGEX.test(ip)) {
    return { valid: false, message: 'IPv4地址格式不正确' };
  }
  return { valid: true };
};

export const sanitizeHtml = (input: string): string => {
  return input
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;')
    .replace(/\//g, '&#x2F;');
};

export const sanitizeSql = (input: string): string => {
  return input
    .replace(/(['";\\])/g, '\\$1')
    .replace(/\0/g, '\\0')
    .replace(/\n/g, '\\n')
    .replace(/\r/g, '\\r')
    .replace(/\x1a/g, '\\Z');
};

export const trimAndNormalize = (input: string): string => {
  return input.trim().replace(/\s+/g, ' ');
};

export const isValidEnum = <T extends string>(value: unknown, enumValues: readonly T[]): value is T => {
  return typeof value === 'string' && enumValues.includes(value as T);
};
