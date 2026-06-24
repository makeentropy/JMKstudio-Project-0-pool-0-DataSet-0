#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#define MAX_LEN 256

void print_binary(unsigned char byte) {
    for (int i = 7; i >= 0; i--) {
        printf("%d", (byte >> i) & 1);
    }
}

void print_hex(const unsigned char *data, int len) {
    for (int i = 0; i < len; i++) {
        printf("%02X ", data[i]);
    }
}

void xor_encrypt_decrypt(const unsigned char *input, unsigned char *output,
                         const unsigned char *key, int input_len, int key_len,
                         int verbose) {
    unsigned char stack_buffer[MAX_LEN];
    int stack_top = 0;

    if (verbose) {
        printf("\n");
        printf("╔══════════════════════════════════════════════════════════════╗\n");
        printf("║           XOR 加密/解密 - 堆栈处理过程                       ║\n");
        printf("╠══════════════════════════════════════════════════════════════╣\n");
        printf("║  输入数据压入堆栈 -> 逐位异或运算 -> 结果弹出堆栈             ║\n");
        printf("╚══════════════════════════════════════════════════════════════╝\n");
        printf("\n");
    }

    for (int i = 0; i < input_len; i++) {
        unsigned char plain_byte = input[i];
        unsigned char key_byte = key[i % key_len];
        unsigned char cipher_byte = plain_byte ^ key_byte;

        stack_buffer[stack_top] = cipher_byte;
        stack_top++;

        output[i] = cipher_byte;

        if (verbose) {
            printf("  [字节 %d] 堆栈位置: stack[%d]\n", i, i);
            printf("    明文 (%-3d): '%c'  →  ", plain_byte, (plain_byte >= 32 && plain_byte < 127) ? plain_byte : '.');
            print_binary(plain_byte);
            printf("  0x%02X\n", plain_byte);

            printf("    密钥 (%-3d): '%c'  →  ", key_byte, (key_byte >= 32 && key_byte < 127) ? key_byte : '.');
            print_binary(key_byte);
            printf("  0x%02X\n", key_byte);

            printf("              ────────────────────────────────────────  XOR\n");

            printf("    密文 (%-3d): '%c'  →  ", cipher_byte, (cipher_byte >= 32 && cipher_byte < 127) ? cipher_byte : '.');
            print_binary(cipher_byte);
            printf("  0x%02X\n", cipher_byte);

            printf("    运算: ");
            for (int b = 7; b >= 0; b--) {
                int pb = (plain_byte >> b) & 1;
                int kb = (key_byte >> b) & 1;
                int cb = pb ^ kb;
                printf("%d⊕%d=%d ", pb, kb, cb);
            }
            printf("\n\n");
        }
    }

    if (verbose) {
        printf("  ── 堆栈状态 (共 %d 字节) ──\n", stack_top);
        printf("  栈底 → ");
        for (int i = 0; i < stack_top; i++) {
            printf("0x%02X ", stack_buffer[i]);
        }
        printf("← 栈顶\n\n");
    }
}

void print_xor_matrix() {
    printf("\n");
    printf("╔══════════════════════════════════════════════════════════════╗\n");
    printf("║                    XOR 真值表 (异或运算)                      ║\n");
    printf("╠══════════════════════════════════════════════════════════════╣\n");
    printf("║  输入A | 输入B | 输出Q = A ⊕ B                               ║\n");
    printf("║  ──────┼───────┼──────────────                               ║\n");
    printf("║    0   |   0   |    0      (相同为0)                         ║\n");
    printf("║    0   |   1   |    1      (不同为1)                         ║\n");
    printf("║    1   |   0   |    1      (不同为1)                         ║\n");
    printf("║    1   |   1   |    0      (相同为0)                         ║\n");
    printf("╚══════════════════════════════════════════════════════════════╝\n");
}

void print_encryption_map(const char *plaintext, const char *key) {
    int plain_len = strlen(plaintext);
    int key_len = strlen(key);

    printf("\n");
    printf("╔══════════════════════════════════════════════════════════════╗\n");
    printf("║              XOR 加密过程细节图谱 (字符级映射)                ║\n");
    printf("╠══════════════════════════════════════════════════════════════╣\n");

    printf("║ 明文字符序列:                                                 ║\n");
    printf("║  ");
    for (int i = 0; i < plain_len; i++) {
        printf(" %c ", plaintext[i]);
        if (i < plain_len - 1) printf("→");
    }
    printf("\n");

    printf("║ 明文索引:                                                     ║\n");
    printf("║  ");
    for (int i = 0; i < plain_len; i++) {
        printf("[%d]", i);
        if (i < plain_len - 1) printf(" ");
    }
    printf("\n");

    printf("╠══════════════════════════════════════════════════════════════╣\n");
    printf("║ 密钥循环:                                                     ║\n");
    printf("║  ");
    for (int i = 0; i < plain_len; i++) {
        printf(" %c ", key[i % key_len]);
        if (i < plain_len - 1) printf("→");
    }
    printf("\n");

    printf("║ 密钥索引:  (循环使用)                                         ║\n");
    printf("║  ");
    for (int i = 0; i < plain_len; i++) {
        printf("[%d]", i % key_len);
        if (i < plain_len - 1) printf(" ");
    }
    printf("\n");

    printf("╠══════════════════════════════════════════════════════════════╣\n");
    printf("║                        ↓ XOR 运算 ↓                          ║\n");
    printf("╠══════════════════════════════════════════════════════════════╣\n");

    printf("║ 密文字符序列: (可打印字符显示，否则显示'.')                    ║\n");
    printf("║  ");
    for (int i = 0; i < plain_len; i++) {
        unsigned char c = plaintext[i] ^ key[i % key_len];
        printf(" %c ", (c >= 32 && c < 127) ? c : '.');
        if (i < plain_len - 1) printf("→");
    }
    printf("\n");

    printf("║ 密文十六进制:                                                 ║\n");
    printf("║  ");
    for (int i = 0; i < plain_len; i++) {
        unsigned char c = plaintext[i] ^ key[i % key_len];
        printf("%02X", c);
        if (i < plain_len - 1) printf(" ");
    }
    printf("\n");
    printf("╚══════════════════════════════════════════════════════════════╝\n");
}

void print_bit_level_map(const char *plaintext, const char *key) {
    int plain_len = strlen(plaintext);
    int key_len = strlen(key);

    printf("\n");
    printf("╔══════════════════════════════════════════════════════════════╗\n");
    printf("║              XOR 加密过程细节图谱 (位级映射)                  ║\n");
    printf("╠══════════════════════════════════════════════════════════════╣\n");

    for (int i = 0; i < plain_len && i < 8; i++) {
        unsigned char p = plaintext[i];
        unsigned char k = key[i % key_len];
        unsigned char c = p ^ k;

        printf("║ 第 %d 字节:                                                    ║\n", i);
        printf("║  明文 '%c' (0x%02X): ", (p >= 32 && p < 127) ? p : '.', p);
        print_binary(p);
        printf("\n");

        printf("║  密钥 '%c' (0x%02X): ", (k >= 32 && k < 127) ? k : '.', k);
        print_binary(k);
        printf("\n");

        printf("║              ────────────────────────────────                 ║\n");

        printf("║  密文     (0x%02X): ", c);
        print_binary(c);
        printf("  '%c'\n", (c >= 32 && c < 127) ? c : '.');

        if (i < plain_len - 1 && i < 7) {
            printf("║                      ↓                                        ║\n");
        }
    }

    if (plain_len > 8) {
        printf("║                   ... (共 %d 字节) ...                        ║\n", plain_len);
    }
    printf("╚══════════════════════════════════════════════════════════════╝\n");
}

void print_principle() {
    printf("\n");
    printf("╔══════════════════════════════════════════════════════════════╗\n");
    printf("║                    XOR 加密原理                                ║\n");
    printf("╠══════════════════════════════════════════════════════════════╣\n");
    printf("║  1. 对称加密: 加密和解密使用相同的密钥                         ║\n");
    printf("║     明文 ⊕ 密钥 = 密文                                        ║\n");
    printf("║     密文 ⊕ 密钥 = 明文                                        ║\n");
    printf("║                                                              ║\n");
    printf("║  2. 位运算: 每一位独立进行异或操作                             ║\n");
    printf("║     相同为0，不同为1                                          ║\n");
    printf("║                                                              ║\n");
    printf("║  3. 流密码模式: 密钥循环使用 (简单实现)                       ║\n");
    printf("║     key[0], key[1], ..., key[n-1], key[0], key[1], ...       ║\n");
    printf("║                                                              ║\n");
    printf("║  4. 数学性质:                                                ║\n");
    printf("║     A ⊕ A = 0     (自身异或为0)                               ║\n");
    printf("║     A ⊕ 0 = A     (与0异或不变)                               ║\n");
    printf("║     A ⊕ B = B ⊕ A (交换律)                                   ║\n");
    printf("║    (A⊕B)⊕C = A⊕(B⊕C) (结合律)                                ║\n");
    printf("╚══════════════════════════════════════════════════════════════╝\n");
}

void print_stack_diagram() {
    printf("\n");
    printf("╔══════════════════════════════════════════════════════════════╗\n");
    printf("║                 XOR 加密堆栈结构图                            ║\n");
    printf("╠══════════════════════════════════════════════════════════════╣\n");
    printf("║                         栈顶 (TOP)                            ║\n");
    printf("║                       ┌───────────┐                           ║\n");
    printf("║                       │  密文[n-1]│ ← 最后压入                ║\n");
    printf("║                       ├───────────┤                           ║\n");
    printf("║                       │  密文[n-2]│                           ║\n");
    printf("║                       ├───────────┤                           ║\n");
    printf("║                       │    ...    │                           ║\n");
    printf("║                       ├───────────┤                           ║\n");
    printf("║                       │  密文[1]  │                           ║\n");
    printf("║                       ├───────────┤                           ║\n");
    printf("║                       │  密文[0]  │ ← 最先压入                ║\n");
    printf("║                       └───────────┘                           ║\n");
    printf("║                         栈底 (BOTTOM)                         ║\n");
    printf("║                                                              ║\n");
    printf("║  PUSH: 明文[i] ⊕ 密钥[i%keylen] → 栈顶                        ║\n");
    printf("║  POP:  栈顶 → 输出数组                                        ║\n");
    printf("╚══════════════════════════════════════════════════════════════╝\n");
}

int main() {
    char plaintext[MAX_LEN];
    char key[MAX_LEN];
    unsigned char encrypted[MAX_LEN];
    unsigned char decrypted[MAX_LEN];

    printf("\n");
    printf("╔══════════════════════════════════════════════════════════════╗\n");
    printf("║                    XOR 加密演示程序                           ║\n");
    printf("║              C 语言实现 - 原理/过程/堆栈/图谱                 ║\n");
    printf("╚══════════════════════════════════════════════════════════════╝\n");

    printf("\n请输入明文: ");
    fgets(plaintext, MAX_LEN, stdin);
    plaintext[strcspn(plaintext, "\n")] = '\0';

    printf("请输入密钥: ");
    fgets(key, MAX_LEN, stdin);
    key[strcspn(key, "\n")] = '\0';

    if (strlen(plaintext) == 0 || strlen(key) == 0) {
        printf("错误: 明文和密钥不能为空！\n");
        return 1;
    }

    int plain_len = strlen(plaintext);
    int key_len = strlen(key);

    print_principle();
    print_xor_matrix();
    print_stack_diagram();
    print_encryption_map(plaintext, key);
    print_bit_level_map(plaintext, key);

    printf("\n");
    printf("╔══════════════════════════════════════════════════════════════╗\n");
    printf("║                  第一阶段: 加密过程 (详细)                     ║\n");
    printf("╚══════════════════════════════════════════════════════════════╝\n");

    xor_encrypt_decrypt((unsigned char *)plaintext, encrypted,
                        (unsigned char *)key, plain_len, key_len, 1);

    printf("\n");
    printf("╔══════════════════════════════════════════════════════════════╗\n");
    printf("║                  第二阶段: 解密过程 (详细)                     ║\n");
    printf("╚══════════════════════════════════════════════════════════════╝\n");

    xor_encrypt_decrypt(encrypted, decrypted,
                        (unsigned char *)key, plain_len, key_len, 1);

    printf("\n");
    printf("╔══════════════════════════════════════════════════════════════╗\n");
    printf("║                       最终结果汇总                             ║\n");
    printf("╠══════════════════════════════════════════════════════════════╣\n");
    printf("║  原明文:   %s\n", plaintext);
    printf("║  密文(HEX): ");
    print_hex(encrypted, plain_len);
    printf("\n");
    printf("║  解密结果: %s\n", decrypted);
    printf("╠══════════════════════════════════════════════════════════════╣\n");

    if (memcmp(plaintext, decrypted, plain_len) == 0) {
        printf("║  ✓ 验证成功: 解密结果与原明文一致！                           ║\n");
    } else {
        printf("║  ✗ 验证失败: 解密结果与原明文不一致！                         ║\n");
    }
    printf("╚══════════════════════════════════════════════════════════════╝\n");
    printf("\n");

    return 0;
}
