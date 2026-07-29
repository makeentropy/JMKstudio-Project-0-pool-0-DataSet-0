'use strict';

var CertificateASN1 = (function () {
    var OID_MAP = {
        '2.5.4.6': 'C',
        '2.5.4.10': 'O',
        '2.5.4.11': 'OU',
        '2.5.4.3': 'CN',
        '2.5.4.7': 'L',
        '2.5.4.8': 'ST',
        '2.5.4.12': 'T',
        '2.5.4.42': 'GN',
        '2.5.4.43': 'I',
        '2.5.4.4': 'SN',
        '1.2.840.113549.1.9.1': 'EMAIL',
        '1.2.840.113549.1.1.1': 'RSA Encryption',
        '1.2.840.113549.1.1.11': 'SHA256WithRSAEncryption',
        '1.2.840.113549.1.1.12': 'SHA384WithRSAEncryption',
        '1.2.840.113549.1.1.13': 'SHA512WithRSAEncryption',
        '1.2.840.10045.4.3.2': 'SHA256withECDSA',
        '1.2.840.10045.4.3.3': 'SHA384withECDSA',
        '1.2.840.10045.4.3.4': 'SHA512withECDSA'
    };

    function oidToName(oid) {
        return OID_MAP[oid] || oid;
    }

    function readASN1Length(bytes, offset) {
        if (offset >= bytes.length) {
            throw new Error('ASN.1解析错误：偏移超出范围');
        }
        var firstByte = bytes[offset];
        if (firstByte < 0x80) {
            return { length: firstByte, bytesRead: 1 };
        }
        var numBytes = firstByte & 0x7F;
        if (numBytes === 0) {
            throw new Error('ASN.1解析错误：不支持不定长度编码');
        }
        if (offset + numBytes >= bytes.length) {
            throw new Error('ASN.1解析错误：长度字段超出数据范围');
        }
        var length = 0;
        for (var i = 0; i < numBytes; i++) {
            length = (length * 256) + bytes[offset + 1 + i];
        }
        return { length: length, bytesRead: numBytes + 1 };
    }

    function parseOID(bytes, offset, length) {
        var oidParts = [];
        var firstByte = bytes[offset];
        oidParts.push(Math.floor(firstByte / 40));
        oidParts.push(firstByte % 40);
        var value = 0;
        for (var i = 1; i < length; i++) {
            var b = bytes[offset + i];
            value = (value << 7) | (b & 0x7F);
            if ((b & 0x80) === 0) {
                oidParts.push(value);
                value = 0;
            }
        }
        return oidParts.join('.');
    }

    function parseASN1String(bytes, offset, length, tag) {
        try {
            var result = '';
            if (tag === 0x13 || tag === 0x14) {
                for (var i = 0; i < length; i++) {
                    result += String.fromCharCode(bytes[offset + i]);
                }
            } else if (tag === 0x0C || tag === 0x1E) {
                    var data = new Uint8Array(length);
                    for (var j = 0; j < length; j++) {
                        data[j] = bytes[offset + j];
                    }
                    if (typeof TextDecoder !== 'undefined') {
                        result = new TextDecoder('utf-8').decode(data);
                    } else {
                        for (var k = 0; k < length; k++) {
                            result += String.fromCharCode(data[k]);
                        }
                    }
                } else if (tag === 0x16) {
                    for (var m = 0; m < length; m++) {
                        result += String.fromCharCode(bytes[offset + m]);
                    }
                } else if (tag === 0x1B) {
                    var data2 = new Uint8Array(length);
                    for (var n = 0; n < length; n++) {
                        data2[n] = bytes[offset + n];
                    }
                    if (typeof TextDecoder !== 'undefined') {
                        result = new TextDecoder('utf-8').decode(data2);
                    } else {
                        for (var p = 0; p < length; p++) {
                            result += String.fromCharCode(data2[p]);
                        }
                    }
                } else {
                    for (var q = 0; q < length; q++) {
                        result += String.fromCharCode(bytes[offset + q]);
                    }
                }
            return result;
        } catch (e) {
            return '[无法解析]';
        }
    }

    function parseDN(bytes, offset, length) {
        var endOffset = offset + length;
        var components = [];
        while (offset < endOffset) {
            if (offset + 2 > bytes.length) break;
            var setTag = bytes[offset];
            if (setTag !== 0x31) break;
            var setLenInfo = readASN1Length(bytes, offset + 1);
            var setDataOffset = offset + 1 + setLenInfo.bytesRead;
            var setDataEnd = setDataOffset + setLenInfo.length;
            var subOffset = setDataOffset;
            while (subOffset < setDataEnd) {
                if (subOffset + 2 > bytes.length) break;
                var seqTag = bytes[subOffset];
                if (seqTag !== 0x30) break;
                var seqLenInfo = readASN1Length(bytes, subOffset + 1);
                var seqDataOffset = subOffset + 1 + seqLenInfo.bytesRead;
                var seqDataEnd = seqDataOffset + seqLenInfo.length;
                if (seqDataOffset + 2 > bytes.length) {
                    subOffset = seqDataEnd;
                    continue;
                }
                var oidTag = bytes[seqDataOffset];
                var oidLenInfo = readASN1Length(bytes, seqDataOffset + 1);
                var oidOffset = seqDataOffset + 1 + oidLenInfo.bytesRead;
                var oid = parseOID(bytes, oidOffset, oidLenInfo.length);
                var oidName = oidToName(oid);
                var valueOffset = oidOffset + oidLenInfo.length;
                if (valueOffset >= seqDataEnd) {
                    subOffset = seqDataEnd;
                    continue;
                }
                var valueTag = bytes[valueOffset];
                var valueLenInfo = readASN1Length(bytes, valueOffset + 1);
                var valueDataOffset = valueOffset + 1 + valueLenInfo.bytesRead;
                var value = parseASN1String(bytes, valueDataOffset, valueLenInfo.length, valueTag);
                components.push({ key: oidName, value: value });
                subOffset = seqDataEnd;
            }
            offset = setDataEnd;
        }
        return components;
    }

    function dnComponentsToString(components) {
        var parts = [];
        for (var i = 0; i < components.length; i++) {
            var c = components[i];
            parts.push(c.key + '=' + c.value);
        }
        return parts.join(', ');
    }

    function parseUTCTime(bytes, offset, length) {
        var str = '';
        for (var i = 0; i < length; i++) {
            str += String.fromCharCode(bytes[offset + i]);
        }
        var year = 0, month = 0, day = 0, hour = 0, min = 0, sec = 0;
        if (/^(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})Z$/.test(str)) {
            year = parseInt(RegExp.$1, 10);
            month = parseInt(RegExp.$2, 10);
            day = parseInt(RegExp.$3, 10);
            hour = parseInt(RegExp.$4, 10);
            min = parseInt(RegExp.$5, 10);
            sec = parseInt(RegExp.$6, 10);
            year += year >= 50 ? 1900 : 2000;
        } else if (/^(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})Z$/.test(str)) {
            year = parseInt(RegExp.$1, 10);
            month = parseInt(RegExp.$2, 10);
            day = parseInt(RegExp.$3, 10);
            hour = parseInt(RegExp.$4, 10);
            min = parseInt(RegExp.$5, 10);
            year += year >= 50 ? 1900 : 2000;
        } else {
            return '无法解析';
        }
        var d = new Date(Date.UTC(year, month - 1, day, hour, min, sec));
        return d.toISOString().replace('T', ' ').replace(/\.\d+Z$/, ' UTC');
    }

    function parseGeneralizedTime(bytes, offset, length) {
        var str = '';
        for (var i = 0; i < length; i++) {
            str += String.fromCharCode(bytes[offset + i]);
        }
        var year = 0, month = 0, day = 0, hour = 0, min = 0, sec = 0;
        if (/^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})Z$/.test(str)) {
            year = parseInt(RegExp.$1, 10);
            month = parseInt(RegExp.$2, 10);
            day = parseInt(RegExp.$3, 10);
            hour = parseInt(RegExp.$4, 10);
            min = parseInt(RegExp.$5, 10);
            sec = parseInt(RegExp.$6, 10);
        } else if (/^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})Z$/.test(str)) {
            year = parseInt(RegExp.$1, 10);
            month = parseInt(RegExp.$2, 10);
            day = parseInt(RegExp.$3, 10);
            hour = parseInt(RegExp.$4, 10);
            min = parseInt(RegExp.$5, 10);
        } else {
            return '无法解析';
        }
        var d = new Date(Date.UTC(year, month - 1, day, hour, min, sec));
        return d.toISOString().replace('T', ' ').replace(/\.\d+Z$/, ' UTC');
    }

    function parseIntegerHex(bytes, offset, length) {
        var hexParts = [];
        var start = offset;
        if (length > 0 && bytes[offset] === 0x00 && length > 1) {
            start = offset + 1;
        }
        for (var i = start; i < offset + length; i++) {
            var hex = bytes[i].toString(16);
            if (hex.length === 1) hex = '0' + hex;
            hexParts.push(hex.toUpperCase());
        }
        return hexParts.join(':');
    }

    function pemToDer(pem) {
        if (!pem || typeof pem !== 'string') {
            throw new Error('PEM内容为空');
        }
        var cleaned = pem.trim();
        var lines = cleaned.split(/\r?\n/);
        var base64Lines = [];
        var inCert = false;
        for (var i = 0; i < lines.length; i++) {
            var line = lines[i].trim();
            if (line.indexOf('-----BEGIN CERTIFICATE-----') !== -1) {
                inCert = true;
                continue;
            }
            if (line.indexOf('-----END CERTIFICATE-----') !== -1) {
                inCert = false;
                break;
            }
            if (inCert && line.length > 0) {
                base64Lines.push(line);
            }
        }
        if (base64Lines.length === 0) {
            throw new Error('未找到有效的PEM证书内容，请确保包含 -----BEGIN CERTIFICATE----- 和 -----END CERTIFICATE----- 标记');
        }
        var base64Str = base64Lines.join('');
        base64Str = base64Str.replace(/\s+/g, '');
        if (!/^[A-Za-z0-9+/=]+$/.test(base64Str)) {
            throw new Error('PEM内容包含非法的Base64字符');
        }
        try {
            var binaryString = atob(base64Str);
            var len = binaryString.length;
            var bytes = new Uint8Array(len);
            for (var j = 0; j < len; j++) {
                bytes[j] = binaryString.charCodeAt(j);
            }
            return bytes;
        } catch (e) {
            throw new Error('Base64解码失败: ' + e.message);
        }
    }

    async function calculateSHA256Fingerprint(derBytes) {
        var buffer = derBytes.buffer;
        var hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
        var hashArray = new Uint8Array(hashBuffer);
        var hexParts = [];
        for (var i = 0; i < hashArray.length; i++) {
            var hex = hashArray[i].toString(16);
            if (hex.length === 1) hex = '0' + hex;
            hexParts.push(hex.toUpperCase());
        }
        return hexParts.join(':');
    }

    function parseCertificate(derBytes) {
        if (!derBytes || derBytes.length < 10) {
            throw new Error('证书数据太短，无法解析');
        }
        var offset = 0;
        if (derBytes[offset] !== 0x30) {
            throw new Error('证书格式错误：不是有效的SEQUENCE');
        }
        offset++;
        var certLenInfo = readASN1Length(derBytes, offset);
        offset += certLenInfo.bytesRead;
        if (derBytes[offset] !== 0x30) {
            throw new Error('证书格式错误：TBSCertificate缺失');
        }
        offset++;
        var tbsLenInfo = readASN1Length(derBytes, offset);
        offset += tbsLenInfo.bytesRead;
        var tbsEnd = offset + tbsLenInfo.length;
        var result = {
            subject: '',
            issuer: '',
            serialNumber: '',
            notBefore: '',
            notAfter: '',
            signatureAlgorithm: '',
            pubKeyAlgorithm: '',
            pubKeySize: ''
        };
        if (derBytes[offset] === 0xA0) {
            offset++;
            var verLenInfo = readASN1Length(derBytes, offset);
            offset += verLenInfo.bytesRead + verLenInfo.length;
        }
        if (offset < derBytes.length && derBytes[offset] === 0x02) {
            offset++;
            var serialLenInfo = readASN1Length(derBytes, offset);
            result.serialNumber = parseIntegerHex(derBytes, offset + serialLenInfo.bytesRead, serialLenInfo.length);
            offset += serialLenInfo.bytesRead + serialLenInfo.length;
        }
        if (offset < derBytes.length && derBytes[offset] === 0x30) {
            offset++;
            var sigAlgSeqLenInfo = readASN1Length(derBytes, offset);
            var sigAlgSeqEnd = offset + sigAlgSeqLenInfo.bytesRead + sigAlgSeqLenInfo.length;
            offset++;
            var sigAlgOidLenInfo = readASN1Length(derBytes, offset);
            var sigAlgOid = parseOID(derBytes, offset + sigAlgOidLenInfo.bytesRead, sigAlgOidLenInfo.length);
            result.signatureAlgorithm = oidToName(sigAlgOid);
            offset = sigAlgSeqEnd;
        }
        if (offset < derBytes.length && derBytes[offset] === 0x30) {
            offset++;
            var issuerLenInfo = readASN1Length(derBytes, offset);
            var issuerComponents = parseDN(derBytes, offset + issuerLenInfo.bytesRead, issuerLenInfo.length);
            result.issuer = dnComponentsToString(issuerComponents);
            offset += issuerLenInfo.bytesRead + issuerLenInfo.length;
        }
        if (offset < derBytes.length && derBytes[offset] === 0x30) {
            offset++;
            var validityLenInfo = readASN1Length(derBytes, offset);
            var validityEnd = offset + validityLenInfo.bytesRead + validityLenInfo.length;
            var timeTag = derBytes[offset + validityLenInfo.bytesRead];
            var timeLenInfo = readASN1Length(derBytes, offset + validityLenInfo.bytesRead + 1);
            var timeDataOffset = offset + validityLenInfo.bytesRead + 1 + timeLenInfo.bytesRead;
            if (timeTag === 0x17) {
                result.notBefore = parseUTCTime(derBytes, timeDataOffset, timeLenInfo.length);
            } else if (timeTag === 0x18) {
                result.notBefore = parseGeneralizedTime(derBytes, timeDataOffset, timeLenInfo.length);
            }
            var afterTagOffset = timeDataOffset + timeLenInfo.length;
            if (afterTagOffset < validityEnd) {
                var afterTag = derBytes[afterTagOffset];
                var afterLenInfo = readASN1Length(derBytes, afterTagOffset + 1);
                var afterDataOffset = afterTagOffset + 1 + afterLenInfo.bytesRead;
                if (afterTag === 0x17) {
                    result.notAfter = parseUTCTime(derBytes, afterDataOffset, afterLenInfo.length);
                } else if (afterTag === 0x18) {
                    result.notAfter = parseGeneralizedTime(derBytes, afterDataOffset, afterLenInfo.length);
                }
            }
            offset = validityEnd;
        }
        if (offset < derBytes.length && derBytes[offset] === 0x30) {
            offset++;
            var subjectLenInfo = readASN1Length(derBytes, offset);
            var subjectComponents = parseDN(derBytes, offset + subjectLenInfo.bytesRead, subjectLenInfo.length);
            result.subject = dnComponentsToString(subjectComponents);
            offset += subjectLenInfo.bytesRead + subjectLenInfo.length;
        }
        if (offset < derBytes.length && derBytes[offset] === 0x30) {
            offset++;
            var spkiLenInfo = readASN1Length(derBytes, offset);
            var spkiEnd = offset + spkiLenInfo.bytesRead + spkiLenInfo.length;
            var algSeqOffset = offset + spkiLenInfo.bytesRead;
            if (algSeqOffset < spkiEnd && derBytes[algSeqOffset] === 0x30) {
                algSeqOffset++;
                var algSeqLenInfo = readASN1Length(derBytes, algSeqOffset);
                var algSeqEnd = algSeqOffset + algSeqLenInfo.bytesRead + algSeqLenInfo.length;
                algSeqOffset++;
                var algOidLenInfo = readASN1Length(derBytes, algSeqOffset);
                var algOid = parseOID(derBytes, algSeqOffset + algOidLenInfo.bytesRead, algOidLenInfo.length);
                result.pubKeyAlgorithm = oidToName(algOid);
                var pubKeyBitOffset = algSeqEnd;
                if (derBytes[pubKeyBitOffset] === 0x03) {
                    pubKeyBitOffset++;
                    var bitStringLenInfo = readASN1Length(derBytes, pubKeyBitOffset);
                    var pubKeyDataLen = bitStringLenInfo.length - 1;
                    result.pubKeySize = (pubKeyDataLen * 8) + ' bits';
                }
            }
            offset = spkiEnd;
        }
        return result;
    }

    return {
        pemToDer: pemToDer,
        calculateSHA256Fingerprint: calculateSHA256Fingerprint,
        parseCertificate: parseCertificate,
        readASN1Length: readASN1Length,
        parseOID: parseOID,
        parseDN: parseDN,
        dnComponentsToString: dnComponentsToString,
        oidToName: oidToName
    };
})();
