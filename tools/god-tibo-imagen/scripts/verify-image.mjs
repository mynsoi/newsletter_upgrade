#!/usr/bin/env node
import { inspectPngFile } from './lib/image-validation.mjs';

function usage() {
  console.log('Usage: node verify-image.mjs <image.png> [--min-bytes 200000] [--ratio 16:9]');
}

function parseArgs(argv) {
  const options = { minBytes: 200_000, ratio: '16:9', tolerance: 0.02, image: null };
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    const next = argv[index + 1];
    if (token === '--min-bytes') {
      options.minBytes = Number(next);
      index += 1;
    } else if (token === '--ratio') {
      options.ratio = next;
      index += 1;
    } else if (token === '--tolerance') {
      options.tolerance = Number(next);
      index += 1;
    } else if (token === '--help' || token === '-h') {
      options.help = true;
    } else if (!token.startsWith('-') && !options.image) {
      options.image = token;
    } else {
      throw new Error(`Unknown argument: ${token}`);
    }
  }
  if (!Number.isInteger(options.minBytes) || options.minBytes < 1) {
    throw new Error('--min-bytes must be a positive integer.');
  }
  if (!Number.isFinite(options.tolerance) || options.tolerance <= 0) {
    throw new Error('--tolerance must be a positive number.');
  }
  return options;
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.help) {
    usage();
    return;
  }
  if (!options.image) {
    usage();
    process.exitCode = 1;
    return;
  }
  const report = await inspectPngFile(options.image, options);
  console.log(JSON.stringify({ valid: true, path: options.image, ...report }));
}

main().catch((error) => {
  console.error(`Invalid image: ${error.message}`);
  process.exitCode = 1;
});
