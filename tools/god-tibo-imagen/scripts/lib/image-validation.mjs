import fs from 'node:fs/promises';
import zlib from 'node:zlib';

const PNG_SIGNATURE = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);

function crc32(buffer) {
  let crc = 0xffffffff;
  for (const byte of buffer) {
    crc ^= byte;
    for (let bit = 0; bit < 8; bit += 1) {
      crc = (crc >>> 1) ^ (crc & 1 ? 0xedb88320 : 0);
    }
  }
  return (crc ^ 0xffffffff) >>> 0;
}

function fail(message) {
  throw new Error(message);
}

export function parseRatio(value) {
  const match = /^(\d+(?:\.\d+)?):(\d+(?:\.\d+)?)$/.exec(String(value));
  if (!match || Number(match[1]) <= 0 || Number(match[2]) <= 0) {
    fail(`Invalid ratio "${value}". Use a positive value such as 16:9.`);
  }
  return Number(match[1]) / Number(match[2]);
}

export function inspectPngBuffer(buffer, { minBytes = 200_000, ratio = '16:9', tolerance = 0.02 } = {}) {
  if (!Buffer.isBuffer(buffer)) {
    buffer = Buffer.from(buffer);
  }
  if (buffer.length < minBytes) {
    fail(`Image is ${buffer.length} bytes; expected at least ${minBytes} bytes.`);
  }
  if (buffer.length < PNG_SIGNATURE.length || !buffer.subarray(0, PNG_SIGNATURE.length).equals(PNG_SIGNATURE)) {
    fail('Image is not a PNG file.');
  }

  let offset = PNG_SIGNATURE.length;
  let width;
  let height;
  let sawIhdr = false;
  let sawIend = false;
  const idat = [];

  while (offset < buffer.length) {
    if (offset + 12 > buffer.length) {
      fail('PNG has a truncated chunk header.');
    }
    const length = buffer.readUInt32BE(offset);
    const type = buffer.subarray(offset + 4, offset + 8).toString('ascii');
    const dataStart = offset + 8;
    const dataEnd = dataStart + length;
    const crcEnd = dataEnd + 4;
    if (crcEnd > buffer.length) {
      fail(`PNG chunk ${type} is truncated.`);
    }
    const expectedCrc = buffer.readUInt32BE(dataEnd);
    const actualCrc = crc32(buffer.subarray(offset + 4, dataEnd));
    if (expectedCrc !== actualCrc) {
      fail(`PNG chunk ${type} has an invalid CRC.`);
    }
    const data = buffer.subarray(dataStart, dataEnd);

    if (!sawIhdr) {
      if (type !== 'IHDR' || length !== 13) {
        fail('PNG must begin with a 13-byte IHDR chunk.');
      }
      width = data.readUInt32BE(0);
      height = data.readUInt32BE(4);
      if (!width || !height) {
        fail('PNG dimensions must be positive.');
      }
      if (data[10] !== 0 || data[11] !== 0 || ![0, 1].includes(data[12])) {
        fail('PNG uses an unsupported compression, filter, or interlace method.');
      }
      sawIhdr = true;
    } else if (type === 'IDAT') {
      idat.push(data);
    } else if (type === 'IEND') {
      if (length !== 0) {
        fail('PNG IEND chunk must be empty.');
      }
      sawIend = true;
      if (crcEnd !== buffer.length) {
        fail('PNG contains trailing bytes after IEND.');
      }
      break;
    }

    offset = crcEnd;
  }

  if (!sawIhdr || !sawIend || idat.length === 0) {
    fail('PNG is missing a required IHDR, IDAT, or IEND chunk.');
  }
  try {
    zlib.inflateSync(Buffer.concat(idat));
  } catch {
    fail('PNG image data cannot be decompressed.');
  }

  const expectedRatio = parseRatio(ratio);
  const actualRatio = width / height;
  if (Math.abs(actualRatio - expectedRatio) / expectedRatio > tolerance) {
    fail(`Image ratio ${width}:${height} is not within ${tolerance * 100}% of ${ratio}.`);
  }

  return {
    format: 'png',
    width,
    height,
    bytes: buffer.length,
    ratio: actualRatio
  };
}

export async function inspectPngFile(filePath, options) {
  const buffer = await fs.readFile(filePath);
  return inspectPngBuffer(buffer, options);
}
