export declare class BaseXORPool {
    private apiToken;
    constructor(apiToken: string);
    xorCrypt(data: string, key: string): string;
    xorDecrypt(encrypted: string, key: string): string;
    signTag(tagId: string, expireTs: number): string;
    verifyTag(signedStr: string): {
        valid: boolean;
        tagId: string;
        expire: number;
    };
    genRandomStr(length: number): string;
    genUuid(): string;
    timestamp(): number;
}
export declare const createBaseXORPool: (apiToken: string) => BaseXORPool;
