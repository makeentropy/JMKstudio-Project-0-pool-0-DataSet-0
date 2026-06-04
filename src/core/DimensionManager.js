export class DimensionManager {
    constructor(spatialPassword = 2) {
        this.spatialPassword = spatialPassword;
        this.hiddenDataLayer = new Map();
    }

    xorBoostKernel(text, data, password) {
        let result = '';
        const dataStr = JSON.stringify(data);
        const combined = text + '||' + dataStr;
        for (let i = 0; i < combined.length; i++) {
            result += String.fromCharCode(combined.charCodeAt(i) ^ password);
        }
        return result;
    }

    decodeXORBoost(cipherText, password) {
        let result = '';
        for (let i = 0; i < cipherText.length; i++) {
            result += String.fromCharCode(cipherText.charCodeAt(i) ^ password);
        }
        const parts = result.split('||');
        if (parts.length > 1) {
            return { plainText: parts[0], data: JSON.parse(parts[1]) };
        }
        return { plainText: result, data: null };
    }

    hideDataInPlainText(plainTextDNA, sensitiveData) {
        const cipherDNA = this.xorBoostKernel(plainTextDNA, sensitiveData, this.spatialPassword);
        this.hiddenDataLayer.set(cipherDNA, true);
        return cipherDNA;
    }

    retrieveTopology(cipherDNA) {
        if (!this.hiddenDataLayer.has(cipherDNA)) {
            throw new Error("因果畸变：空间密码不匹配");
        }
        return this.decodeXORBoost(cipherDNA, this.spatialPassword);
    }
}
