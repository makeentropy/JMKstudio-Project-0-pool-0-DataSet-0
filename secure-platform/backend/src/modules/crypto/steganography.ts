import { validateString, validateBuffer, SteganographyError } from './errors';
import { encrypt as aesEncrypt, decrypt as aesDecrypt } from './aes-256-gcm';

const MESSAGE_LENGTH_BYTES = 4;
const MAGIC_NUMBER = 0x53544547;

function crc32(buf: Buffer): number {
  let crc = 0xffffffff;
  const table = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) {
      c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    }
    table[n] = c >>> 0;
  }
  for (let i = 0; i < buf.length; i++) {
    crc = table[(crc ^ buf[i]) & 0xff] ^ (crc >>> 8);
  }
  return (crc ^ 0xffffffff) >>> 0;
}

function getPixelDataOffset(buffer: Buffer): { offset: number; width: number; height: number; channels: number } {
  if (buffer.length < 2) {
    throw new SteganographyError('无效的图片数据');
  }

  if (buffer[0] === 0x89 && buffer.toString('ascii', 1, 4) === 'PNG') {
    return parsePNG(buffer);
  } else if (buffer[0] === 0x42 && buffer[1] === 0x4D) {
    return parseBMP(buffer);
  }

  throw new SteganographyError('不支持的图片格式，仅支持 PNG 和 BMP 格式');
}

function parsePNG(buffer: Buffer): { offset: number; width: number; height: number; channels: number } {
  try {
    let offset = 8;
    while (offset < buffer.length) {
      const length = buffer.readUInt32BE(offset);
      const type = buffer.toString('ascii', offset + 4, offset + 8);

      if (type === 'IHDR') {
        const width = buffer.readUInt32BE(offset + 8);
        const height = buffer.readUInt32BE(offset + 12);
        const bitDepth = buffer[offset + 16];
        const colorType = buffer[offset + 17];

        let channels: number;
        if (colorType === 0 || colorType === 3) {
          channels = 1;
        } else if (colorType === 2) {
          channels = 3;
        } else if (colorType === 4) {
          channels = 2;
        } else if (colorType === 6) {
          channels = 4;
        } else {
          throw new SteganographyError('不支持的 PNG 颜色类型');
        }

        if (bitDepth !== 8) {
          throw new SteganographyError('仅支持 8 位色深的 PNG 图片');
        }

        let idatOffset = -1;
        let searchOffset = offset + 8 + length;
        while (searchOffset < buffer.length) {
          const chunkLength = buffer.readUInt32BE(searchOffset);
          const chunkType = buffer.toString('ascii', searchOffset + 4, searchOffset + 8);
          if (chunkType === 'IDAT') {
            idatOffset = searchOffset + 8;
            break;
          }
          searchOffset += 8 + chunkLength + 4;
        }

        if (idatOffset === -1) {
          throw new SteganographyError('PNG 图片缺少 IDAT 数据块');
        }

        return {
          offset: idatOffset,
          width,
          height,
          channels,
        };
      }

      offset += 8 + length + 4;
    }

    throw new SteganographyError('PNG 图片缺少 IHDR 数据块');
  } catch (error) {
    if (error instanceof SteganographyError) {
      throw error;
    }
    throw new SteganographyError('PNG 图片解析失败', error);
  }
}

function parseBMP(buffer: Buffer): { offset: number; width: number; height: number; channels: number } {
  try {
    const pixelDataOffset = buffer.readUInt32LE(10);
    const width = Math.abs(buffer.readInt32LE(18));
    const height = Math.abs(buffer.readInt32LE(22));
    const bitsPerPixel = buffer.readUInt16LE(28);

    let channels: number;
    if (bitsPerPixel === 24) {
      channels = 3;
    } else if (bitsPerPixel === 32) {
      channels = 4;
    } else {
      throw new SteganographyError(`不支持的 BMP 位深度: ${bitsPerPixel}，仅支持 24 位和 32 位`);
    }

    return {
      offset: pixelDataOffset,
      width,
      height,
      channels,
    };
  } catch (error) {
    if (error instanceof SteganographyError) {
      throw error;
    }
    throw new SteganographyError('BMP 图片解析失败', error);
  }
}

function getRawPixelBuffer(buffer: Buffer): { pixels: Buffer; header: Buffer; footer: Buffer; isPNG: boolean } {
  if (buffer[0] === 0x89 && buffer.toString('ascii', 1, 4) === 'PNG') {
    return extractPNGPixels(buffer);
  } else if (buffer[0] === 0x42 && buffer[1] === 0x4D) {
    return extractBMPPixels(buffer);
  }
  throw new SteganographyError('不支持的图片格式');
}

function extractPNGPixels(buffer: Buffer): { pixels: Buffer; header: Buffer; footer: Buffer; isPNG: boolean } {
  const { inflateSync } = require('node:zlib');

  try {
    let idatData: Buffer = Buffer.alloc(0) as Buffer;
    let beforeIdat: Buffer = Buffer.alloc(0) as Buffer;
    let afterIdatStart = -1;

    let offset = 8;
    let foundIdat = false;

    while (offset < buffer.length) {
      const length = buffer.readUInt32BE(offset);
      const type = buffer.toString('ascii', offset + 4, offset + 8);

      if (type === 'IDAT') {
        if (!foundIdat) {
          beforeIdat = buffer.subarray(0, offset) as Buffer;
          foundIdat = true;
        }
        idatData = Buffer.concat([idatData, buffer.subarray(offset + 8, offset + 8 + length) as Buffer]) as Buffer;
      } else if (foundIdat && afterIdatStart === -1) {
        afterIdatStart = offset;
      }

      offset += 8 + length + 4;
    }

    if (!foundIdat) {
      throw new SteganographyError('PNG 图片缺少 IDAT 数据块');
    }

    const footer: Buffer = (afterIdatStart !== -1 ? buffer.subarray(afterIdatStart) : Buffer.alloc(0)) as Buffer;
    const decompressed = inflateSync(idatData);
    const width = buffer.readUInt32BE(16);
    const height = Math.abs(buffer.readUInt32BE(20));
    const bitDepth = buffer[24];
    const colorType = buffer[25];

    let channels: number;
    if (colorType === 0 || colorType === 3) channels = 1;
    else if (colorType === 2) channels = 3;
    else if (colorType === 4) channels = 2;
    else channels = 4;

    const bytesPerPixel = (bitDepth / 8) * channels;
    const stride = width * bytesPerPixel + 1;
    const pixels = Buffer.alloc(width * height * bytesPerPixel);

    for (let y = 0; y < height; y++) {
      const srcStart = y * stride + 1;
      const dstStart = y * width * bytesPerPixel;
      decompressed.copy(pixels, dstStart, srcStart, srcStart + width * bytesPerPixel);
    }

    return {
      pixels,
      header: beforeIdat,
      footer,
      isPNG: true,
    };
  } catch (error) {
    if (error instanceof SteganographyError) {
      throw error;
    }
    throw new SteganographyError('PNG 像素数据提取失败', error);
  }
}

function extractBMPPixels(buffer: Buffer): { pixels: Buffer; header: Buffer; footer: Buffer; isPNG: boolean } {
  try {
    const pixelDataOffset = buffer.readUInt32LE(10);
    const width = buffer.readInt32LE(18);
    const height = buffer.readInt32LE(22);
    const bitsPerPixel = buffer.readUInt16LE(28);
    const channels = bitsPerPixel / 8;

    const rowSize = Math.ceil((width * channels) / 4) * 4;
    const pixelCount = Math.abs(width) * Math.abs(height) * channels;

    const pixels = Buffer.alloc(pixelCount);
    const header = buffer.subarray(0, pixelDataOffset);
    const actualHeight = Math.abs(height);
    const actualWidth = Math.abs(width);

    for (let y = 0; y < actualHeight; y++) {
      const srcY = height > 0 ? actualHeight - 1 - y : y;
      const srcStart = pixelDataOffset + srcY * rowSize;
      const dstStart = y * actualWidth * channels;

      for (let x = 0; x < actualWidth; x++) {
        const s = srcStart + x * channels;
        const d = dstStart + x * channels;
        pixels[d] = buffer[s + 2];
        pixels[d + 1] = buffer[s + 1];
        pixels[d + 2] = buffer[s];
        if (channels === 4) {
          pixels[d + 3] = buffer[s + 3];
        }
      }
    }

    return {
      pixels,
      header,
      footer: Buffer.alloc(0),
      isPNG: false,
    };
  } catch (error) {
    if (error instanceof SteganographyError) {
      throw error;
    }
    throw new SteganographyError('BMP 像素数据提取失败', error);
  }
}

function reconstructImage(
  pixels: Buffer,
  header: Buffer,
  footer: Buffer,
  isPNG: boolean,
  originalBuffer: Buffer,
): Buffer {
  if (isPNG) {
    return reconstructPNG(pixels, header, footer, originalBuffer);
  } else {
    return reconstructBMP(pixels, header, originalBuffer);
  }
}

function reconstructPNG(
  pixels: Buffer,
  header: Buffer,
  footer: Buffer,
  originalBuffer: Buffer,
): Buffer {
  const { deflateSync } = require('node:zlib');

  try {
    const width = originalBuffer.readUInt32BE(16);
    const height = Math.abs(originalBuffer.readUInt32BE(20));
    const colorType = originalBuffer[25];

    let channels: number;
    if (colorType === 0 || colorType === 3) channels = 1;
    else if (colorType === 2) channels = 3;
    else if (colorType === 4) channels = 2;
    else channels = 4;

    const bytesPerRow = width * channels;
    const rawData = Buffer.alloc(height * (bytesPerRow + 1));

    for (let y = 0; y < height; y++) {
      rawData[y * (bytesPerRow + 1)] = 0;
      pixels.copy(rawData, y * (bytesPerRow + 1) + 1, y * bytesPerRow, y * bytesPerRow + bytesPerRow);
    }

    const compressed = deflateSync(rawData);
    const idatChunkType = Buffer.from('IDAT', 'ascii');
    const idatLength = Buffer.alloc(4);
    idatLength.writeUInt32BE(compressed.length, 0);

    const idatCrcData = Buffer.concat([idatChunkType, compressed]);
    const idatCrcValue = crc32(idatCrcData);
    const idatCrcBuffer = Buffer.alloc(4);
    idatCrcBuffer.writeUInt32BE(idatCrcValue, 0);

    const idatChunk = Buffer.concat([idatLength, idatChunkType, compressed, idatCrcBuffer]);

    return Buffer.concat([header, idatChunk, footer]);
  } catch (error) {
    throw new SteganographyError('PNG 图片重构失败', error);
  }
}

function reconstructBMP(pixels: Buffer, header: Buffer, originalBuffer: Buffer): Buffer {
  try {
    const width = originalBuffer.readInt32LE(18);
    const height = originalBuffer.readInt32LE(22);
    const bitsPerPixel = originalBuffer.readUInt16LE(28);
    const channels = bitsPerPixel / 8;
    const pixelDataOffset = header.length;
    const actualWidth = Math.abs(width);
    const actualHeight = Math.abs(height);
    const rowSize = Math.ceil((actualWidth * channels) / 4) * 4;

    const totalSize = pixelDataOffset + actualHeight * rowSize;
    const result = Buffer.alloc(totalSize);
    header.copy(result, 0);

    result.writeUInt32LE(totalSize, 2);

    for (let y = 0; y < actualHeight; y++) {
      const dstY = height > 0 ? actualHeight - 1 - y : y;
      const dstStart = pixelDataOffset + dstY * rowSize;
      const srcStart = y * actualWidth * channels;

      for (let x = 0; x < actualWidth; x++) {
        const s = srcStart + x * channels;
        const d = dstStart + x * channels;
        result[d] = pixels[s + 2];
        result[d + 1] = pixels[s + 1];
        result[d + 2] = pixels[s];
        if (channels === 4) {
          result[d + 3] = pixels[s + 3];
        }
      }
    }

    return result;
  } catch (error) {
    if (error instanceof SteganographyError) {
      throw error;
    }
    throw new SteganographyError('BMP 图片重构失败', error);
  }
}

export function encodeMessageIntoImage(imageBuffer: Buffer, message: string, password?: string): Buffer {
  validateBuffer(imageBuffer, 'imageBuffer');
  validateString(message, 'message');

  try {
    let processedMessage = message;
    if (password !== undefined) {
      validateString(password, 'password');
      processedMessage = aesEncrypt(message, password);
    }

    const messageBuffer = Buffer.from(processedMessage, 'utf-8');
    const messageLength = messageBuffer.length;
    const totalBytes = MESSAGE_LENGTH_BYTES + messageLength;
    const totalBits = totalBytes * 8;

    const { pixels, header, footer, isPNG } = getRawPixelBuffer(imageBuffer);
    const usablePixels = Math.floor(pixels.length / 3) * 3;
    const maxBits = usablePixels;

    if (totalBits > maxBits) {
      throw new SteganographyError(
        `图片容量不足，需要至少 ${Math.ceil(totalBits / 8)} 字节存储空间，` +
        `但图片仅支持 ${Math.floor(maxBits / 8)} 字节`
      );
    }

    const headerData = Buffer.alloc(MESSAGE_LENGTH_BYTES);
    headerData.writeUInt32BE(messageLength, 0);

    const payload = Buffer.concat([headerData, messageBuffer]);

    const newPixels = Buffer.from(pixels);

    for (let i = 0; i < payload.length; i++) {
      for (let bit = 0; bit < 8; bit++) {
        const pixelIndex = i * 8 + bit;
        if (pixelIndex >= newPixels.length) break;

        const bitValue = (payload[i] >> (7 - bit)) & 1;
        newPixels[pixelIndex] = (newPixels[pixelIndex] & 0xFE) | bitValue;
      }
    }

    return reconstructImage(newPixels, header, footer, isPNG, imageBuffer);
  } catch (error) {
    if (error instanceof SteganographyError) {
      throw error;
    }
    throw new SteganographyError('消息编码到图片失败', error);
  }
}

export function decodeMessageFromImage(imageBuffer: Buffer, password?: string): string {
  validateBuffer(imageBuffer, 'imageBuffer');

  try {
    const { pixels } = getRawPixelBuffer(imageBuffer);

    if (pixels.length < MESSAGE_LENGTH_BYTES * 8) {
      throw new SteganographyError('图片中没有找到隐藏的消息');
    }

    const messageLengthBuffer = Buffer.alloc(MESSAGE_LENGTH_BYTES);
    for (let i = 0; i < MESSAGE_LENGTH_BYTES; i++) {
      let byte = 0;
      for (let bit = 0; bit < 8; bit++) {
        const pixelIndex = i * 8 + bit;
        byte = (byte << 1) | (pixels[pixelIndex] & 1);
      }
      messageLengthBuffer[i] = byte;
    }

    const messageLength = messageLengthBuffer.readUInt32BE(0);

    if (messageLength <= 0) {
      throw new SteganographyError('图片中没有找到隐藏的消息');
    }

    const totalBits = (MESSAGE_LENGTH_BYTES + messageLength) * 8;
    if (totalBits > pixels.length) {
      throw new SteganographyError('图片数据损坏，消息长度超出图片容量');
    }

    const messageBuffer = Buffer.alloc(messageLength);
    for (let i = 0; i < messageLength; i++) {
      let byte = 0;
      for (let bit = 0; bit < 8; bit++) {
        const pixelIndex = (MESSAGE_LENGTH_BYTES + i) * 8 + bit;
        byte = (byte << 1) | (pixels[pixelIndex] & 1);
      }
      messageBuffer[i] = byte;
    }

    let message = messageBuffer.toString('utf-8');

    if (password !== undefined) {
      validateString(password, 'password');
      try {
        message = aesDecrypt(message, password);
      } catch (error) {
        throw new SteganographyError('消息解密失败，请检查密码是否正确', error);
      }
    }

    return message;
  } catch (error) {
    if (error instanceof SteganographyError) {
      throw error;
    }
    throw new SteganographyError('从图片中解码消息失败', error);
  }
}

export function getImageCapacity(imageBuffer: Buffer): number {
  validateBuffer(imageBuffer, 'imageBuffer');

  try {
    const { pixels } = getRawPixelBuffer(imageBuffer);
    const usablePixels = Math.floor(pixels.length / 3) * 3;
    const totalBytes = Math.floor(usablePixels / 8);
    return Math.max(0, totalBytes - MESSAGE_LENGTH_BYTES);
  } catch (error) {
    if (error instanceof SteganographyError) {
      throw error;
    }
    throw new SteganographyError('获取图片容量失败', error);
  }
}

export function hasHiddenMessage(imageBuffer: Buffer): boolean {
  validateBuffer(imageBuffer, 'imageBuffer');

  try {
    const { pixels } = getRawPixelBuffer(imageBuffer);

    if (pixels.length < MESSAGE_LENGTH_BYTES * 8) {
      return false;
    }

    const messageLengthBuffer = Buffer.alloc(MESSAGE_LENGTH_BYTES);
    for (let i = 0; i < MESSAGE_LENGTH_BYTES; i++) {
      let byte = 0;
      for (let bit = 0; bit < 8; bit++) {
        const pixelIndex = i * 8 + bit;
        byte = (byte << 1) | (pixels[pixelIndex] & 1);
      }
      messageLengthBuffer[i] = byte;
    }

    const messageLength = messageLengthBuffer.readUInt32BE(0);
    return messageLength > 0 && (MESSAGE_LENGTH_BYTES + messageLength) * 8 <= pixels.length;
  } catch {
    return false;
  }
}
