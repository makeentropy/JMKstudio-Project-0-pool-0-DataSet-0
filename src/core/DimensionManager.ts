export class DimensionManager {
  spatialPassword: string;
  private hiddenDataLayer: Map<string, { data: any; timestamp: number }>;

  constructor(spatialPassword: string) {
    this.spatialPassword = spatialPassword;
    this.hiddenDataLayer = new Map();
  }

  hideDataInPlainText(plainTextDNA: string, sensitiveData: any): string {
    const cipherDNA = this.xorBoostKernel(plainTextDNA, sensitiveData, this.spatialPassword);
    this.hiddenDataLayer.set(cipherDNA, {
      data: sensitiveData,
      timestamp: Date.now()
    });
    return cipherDNA;
  }

  retrieveTopology(cipherDNA: string): any {
    const stored = this.hiddenDataLayer.get(cipherDNA);
    if (!stored) {
      throw new Error('因果畸变：空间密码不匹配');
    }
    return stored.data;
  }

  xorBoostKernel(plain: string, data: any, password: string): string {
    const dataStr = JSON.stringify(data);
    const combined = plain + dataStr;
    let result = '';
    for (let i = 0; i < combined.length; i++) {
      const charCode = combined.charCodeAt(i);
      const passwordChar = password.charCodeAt(i % password.length);
      const xor = charCode ^ passwordChar;
      result += String.fromCharCode((xor % 26) + 65);
    }
    const bases = ['A', 'T', 'C', 'G'];
    return result
      .split('')
      .map((c) => bases[c.charCodeAt(0) % 4])
      .join('');
  }

  decodeSingularityData(cipherDNA: string): any {
    return this.retrieveTopology(cipherDNA);
  }

  getAllHiddenData(): Array<{ cipher: string; data: any; timestamp: number }> {
    const result: Array<{ cipher: string; data: any; timestamp: number }> = [];
    this.hiddenDataLayer.forEach((value, key) => {
      result.push({
        cipher: key,
        data: value.data,
        timestamp: value.timestamp
      });
    });
    return result;
  }

  clearHiddenData(): void {
    this.hiddenDataLayer.clear();
  }

  updatePassword(newPassword: string): void {
    this.spatialPassword = newPassword;
  }
}
