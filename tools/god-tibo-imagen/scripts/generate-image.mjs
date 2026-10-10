#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';

import { inspectPngFile } from './lib/image-validation.mjs';
import { enforceCodexModel } from '../vendor/god-tibo-imagen/src/config.js';

const DEFAULT_TIMEOUT_MS = 90_000;
const DEFAULT_RETRIES = 2;
const DEFAULT_MIN_BYTES = 200_000;
const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const defaultGtiCli = path.join(scriptDir, '..', 'vendor', 'god-tibo-imagen', 'src', 'cli', 'generate.js');

function usage() {
  console.log(`Usage: node generate-image.mjs --prompt <text> --output <image.png> [options]

Options:
  --image <path>         Optional style-reference image; repeatable
  --model <name>         Ignored; every request uses gpt-6-astra
  --size <value>         gti output size (default: 2048x1152)
  --timeout-ms <number>  Per-attempt timeout in milliseconds (default: ${DEFAULT_TIMEOUT_MS})
  --retries <number>     Retries after the first attempt (default: ${DEFAULT_RETRIES})
  --min-bytes <number>   Minimum verified PNG size (default: ${DEFAULT_MIN_BYTES})
  --ratio <value>        Required aspect ratio (default: 16:9)
  --tolerance <number>   Aspect-ratio tolerance as a fraction (default: 0.02)
  --dry-run              Validate the gti request without creating an image
  --help                 Show this message`);
}

function takeValue(argv, index, flag) {
  const value = argv[index + 1];
  if (!value || value.startsWith('--')) {
    throw new Error(`${flag} requires a value.`);
  }
  return value;
}

function parseArgs(argv) {
  const options = {
    prompt: null,
    images: [],
    model: null,
    output: null,
    size: '2048x1152',
    timeoutMs: DEFAULT_TIMEOUT_MS,
    retries: DEFAULT_RETRIES,
    minBytes: DEFAULT_MIN_BYTES,
    ratio: '16:9',
    tolerance: 0.02,
    dryRun: false,
    help: false
  };
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    switch (token) {
      case '--prompt':
        options.prompt = takeValue(argv, index, token);
        index += 1;
        break;
      case '--image':
        options.images.push(takeValue(argv, index, token));
        index += 1;
        break;
      case '--output':
        options.output = takeValue(argv, index, token);
        index += 1;
        break;
      case '--model':
        options.model = takeValue(argv, index, token);
        index += 1;
        break;
      case '--size':
        options.size = takeValue(argv, index, token);
        index += 1;
        break;
      case '--timeout-ms':
        options.timeoutMs = Number(takeValue(argv, index, token));
        index += 1;
        break;
      case '--retries':
        options.retries = Number(takeValue(argv, index, token));
        index += 1;
        break;
      case '--min-bytes':
        options.minBytes = Number(takeValue(argv, index, token));
        index += 1;
        break;
      case '--ratio':
        options.ratio = takeValue(argv, index, token);
        index += 1;
        break;
      case '--tolerance':
        options.tolerance = Number(takeValue(argv, index, token));
        index += 1;
        break;
      case '--dry-run':
        options.dryRun = true;
        break;
      case '--help':
      case '-h':
        options.help = true;
        break;
      default:
        throw new Error(`Unknown argument: ${token}`);
    }
  }
  for (const [key, value] of Object.entries({
    '--timeout-ms': options.timeoutMs,
    '--retries': options.retries,
    '--min-bytes': options.minBytes,
    '--tolerance': options.tolerance
  })) {
    if (!Number.isFinite(value) || value < 0 || (key !== '--retries' && value === 0)) {
      throw new Error(`${key} must be ${key === '--retries' ? 'zero or a positive' : 'a positive'} number.`);
    }
  }
  options.model = enforceCodexModel(options.model, '--model');
  return options;
}

function sleep(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

async function fileExists(filePath) {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}

function runGti(gtiCli, args, timeoutMs) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [gtiCli, ...args], { stdio: ['ignore', 'pipe', 'pipe'] });
    let stdout = '';
    let stderr = '';
    let timedOut = false;
    const timer = setTimeout(() => {
      timedOut = true;
      child.kill('SIGTERM');
      setTimeout(() => child.kill('SIGKILL'), 500).unref();
    }, timeoutMs);
    child.stdout.on('data', (chunk) => { stdout += chunk; });
    child.stderr.on('data', (chunk) => { stderr += chunk; });
    child.on('error', (error) => {
      clearTimeout(timer);
      reject(error);
    });
    child.on('close', (code, signal) => {
      clearTimeout(timer);
      resolve({ code, signal, stdout, stderr, timedOut });
    });
  });
}

function temporaryPath(outputPath, attempt) {
  const extension = path.extname(outputPath) || '.png';
  const base = path.basename(outputPath, extension);
  return path.join(path.dirname(outputPath), `.${base}.tmp.${process.pid}.${attempt}${extension}`);
}

function compactError(result) {
  const lines = result.stderr.trim().split('\n').map((line) => line.trim()).filter(Boolean);
  const message = lines.find((line) => /HTTP \d{3}|usage_limit_reached|^Error:|Unauthorized/.test(line))
    || lines.find((line) => !line.startsWith('WARNING:') && !line.startsWith('at '));
  if (result.timedOut) return 'generation timed out';
  return message || `gti exited with code ${result.code ?? 'unknown'}`;
}

function buildGtiArgs(options, outputPath) {
  return [
    '--provider', 'private-codex',
    '--model', options.model,
    '--size', options.size,
    ...options.images.flatMap((image) => ['--image', image]),
    '--output', outputPath,
    '--prompt', options.prompt.trim(),
    ...(options.dryRun ? ['--dry-run'] : [])
  ];
}

async function generate(options) {
  if (!options.prompt || !options.output) {
    throw new Error('--prompt and --output are required.');
  }
  const outputPath = path.resolve(options.output);
  if (path.extname(outputPath).toLowerCase() !== '.png') {
    throw new Error('--output must end in .png.');
  }
  for (const image of options.images) {
    if (!(await fileExists(image))) {
      throw new Error(`Input image does not exist: ${image}`);
    }
  }

  const gtiCli = process.env.GTI_CLI || defaultGtiCli;
  if (!(await fileExists(gtiCli))) {
    throw new Error(`god-tibo-imagen CLI was not found: ${gtiCli}`);
  }
  if (options.dryRun) {
    const result = await runGti(gtiCli, buildGtiArgs(options, outputPath), options.timeoutMs);
    if (result.code !== 0 || result.timedOut) {
      throw new Error(`gti dry-run failed: ${compactError(result)}`);
    }
    return { status: 'dry-run', output: outputPath, model: options.model };
  }

  try {
    await inspectPngFile(outputPath, options);
    return { status: 'skipped', output: outputPath };
  } catch {
    // Missing or invalid files are regenerated below.
  }

  await fs.mkdir(path.dirname(outputPath), { recursive: true });
  const failures = [];
  for (let attempt = 0; attempt <= options.retries; attempt += 1) {
    const tempPath = temporaryPath(outputPath, attempt);
    try {
      await fs.rm(tempPath, { force: true });
      const result = await runGti(gtiCli, buildGtiArgs(options, tempPath), options.timeoutMs);
      if (result.code !== 0 || result.timedOut) {
        throw new Error(compactError(result));
      }
      await inspectPngFile(tempPath, options);
      await fs.rename(tempPath, outputPath);
      return { status: 'generated', output: outputPath, model: options.model, attempts: attempt + 1 };
    } catch (error) {
      failures.push(error.message);
      await fs.rm(tempPath, { force: true });
      if (/HTTP (?:400|401|403|429)\b|usage_limit_reached|Unauthorized/i.test(error.message)) {
        throw new Error(`Image generation stopped after ${attempt + 1} attempt(s): ${error.message}`);
      }
      if (attempt < options.retries) {
        await sleep(Math.min(2_000, 250 * (2 ** attempt)));
      }
    }
  }
  throw new Error(`Image generation failed after ${options.retries + 1} attempt(s): ${failures.join(' | ')}`);
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.help) {
    usage();
    return;
  }
  console.log(JSON.stringify(await generate(options)));
}

main().catch((error) => {
  console.error(`god-tibo-imagen: ${error.message}`);
  process.exitCode = 1;
});
