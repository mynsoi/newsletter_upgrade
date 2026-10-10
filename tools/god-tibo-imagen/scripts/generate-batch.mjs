#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';

import { enforceCodexModel } from '../vendor/god-tibo-imagen/src/config.js';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const generateScript = path.join(scriptDir, 'generate-image.mjs');

function usage() {
  console.log(`Usage: node generate-batch.mjs --manifest <batch.json> [options]

Manifest:
  { "variants": [{ "output": "out.png", "prompt": "..." }] }
  Optional per-variant "images": ["ref.png", ...]
  Optional top-level "size"; a top-level "model" is ignored (always gpt-6-astra)

Options:
  --jobs <number>        Parallel jobs (default: 8)
  --model <name>         Ignored; every request uses gpt-6-astra
  --size <value>         gti output size (default: 2048x1152)
  --timeout-ms <number>  Per-attempt timeout (default: 90000)
  --retries <number>     Retries after the first attempt (default: 2)
  --min-bytes <number>   Minimum verified PNG size (default: 200000)
  --ratio <value>        Required aspect ratio (default: 16:9)
  --tolerance <number>   Aspect-ratio tolerance as a fraction (default: 0.02)
  --dry-run              Validate requests without creating images
  --help                 Show this message`);
}

function parseArgs(argv) {
  const options = {
    manifest: null,
    jobs: 8,
    size: null,
    model: null,
    timeoutMs: 90_000,
    retries: 2,
    minBytes: 200_000,
    ratio: '16:9',
    tolerance: 0.02,
    dryRun: false,
    help: false
  };
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    const value = argv[index + 1];
    if (token === '--dry-run') {
      options.dryRun = true;
    } else if (token === '--help' || token === '-h') {
      options.help = true;
    } else if (['--manifest', '--jobs', '--model', '--size', '--timeout-ms', '--retries', '--min-bytes', '--ratio', '--tolerance'].includes(token)) {
      if (!value || value.startsWith('--')) throw new Error(`${token} requires a value.`);
      const key = {
        '--manifest': 'manifest', '--jobs': 'jobs', '--model': 'model', '--size': 'size', '--timeout-ms': 'timeoutMs',
        '--retries': 'retries', '--min-bytes': 'minBytes', '--ratio': 'ratio', '--tolerance': 'tolerance'
      }[token];
      options[key] = ['jobs', 'timeoutMs', 'retries', 'minBytes', 'tolerance'].includes(key) ? Number(value) : value;
      index += 1;
    } else {
      throw new Error(`Unknown argument: ${token}`);
    }
  }
  for (const key of ['jobs', 'timeoutMs', 'retries', 'minBytes', 'tolerance']) {
    const value = options[key];
    if (!Number.isFinite(value) || value < 0 || (key !== 'retries' && value === 0)) {
      throw new Error(`--${key.replace(/[A-Z]/g, (letter) => `-${letter.toLowerCase()}`)} must be ${key === 'retries' ? 'zero or a positive' : 'a positive'} number.`);
    }
  }
  return options;
}

function runGenerator(args) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [generateScript, ...args], { stdio: ['ignore', 'pipe', 'pipe'], env: process.env });
    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (chunk) => { stdout += chunk; });
    child.stderr.on('data', (chunk) => { stderr += chunk; });
    child.on('error', reject);
    child.on('close', (code) => resolve({ code, stdout, stderr }));
  });
}

function resolveManifestPath(manifestDir, value) {
  return path.isAbsolute(value) ? value : path.resolve(manifestDir, value);
}

async function loadVariants(manifestPath) {
  const manifestDir = path.dirname(manifestPath);
  const manifest = JSON.parse(await fs.readFile(manifestPath, 'utf8'));
  if (!manifest || typeof manifest !== 'object' || !Array.isArray(manifest.variants) || manifest.variants.length === 0) {
    throw new Error('Manifest must contain a non-empty variants array.');
  }
  const outputs = new Set();
  const variants = manifest.variants.map((variant, index) => {
    if (!variant || typeof variant.prompt !== 'string' || !variant.prompt.trim() || typeof variant.output !== 'string' || !variant.output.trim()) {
      throw new Error(`Variant ${index + 1} must contain non-empty prompt and output fields.`);
    }
    const output = resolveManifestPath(manifestDir, variant.output);
    if (outputs.has(output)) throw new Error(`Manifest has a duplicate output: ${output}`);
    outputs.add(output);
    const images = Array.isArray(variant.images) ? variant.images.map((image) => resolveManifestPath(manifestDir, image)) : [];
    return { name: variant.name || path.basename(output, '.png'), prompt: variant.prompt, output, images };
  });
  for (const key of ['size', 'model']) {
    if (manifest[key] != null && (typeof manifest[key] !== 'string' || !manifest[key].trim())) {
      throw new Error(`Manifest ${key} must be a non-empty string.`);
    }
  }
  return { variants, size: manifest.size, model: manifest.model };
}

function parseOutcome(stdout) {
  const line = stdout.trim().split('\n').filter(Boolean).at(-1);
  return line ? JSON.parse(line) : null;
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.help) {
    usage();
    return;
  }
  if (!options.manifest) throw new Error('--manifest is required.');
  const manifest = await loadVariants(path.resolve(options.manifest));
  const { variants } = manifest;
  options.size = options.size || manifest.size || '2048x1152';
  enforceCodexModel(manifest.model, 'Manifest model');
  options.model = enforceCodexModel(options.model, '--model');
  let nextIndex = 0;
  let stoppedReason = null;
  const results = new Array(variants.length);
  const worker = async () => {
    while (true) {
      if (stoppedReason) return;
      const index = nextIndex;
      nextIndex += 1;
      if (index >= variants.length) return;
      const variant = variants[index];
      const args = [
        '--prompt', variant.prompt,
        '--output', variant.output,
        '--size', options.size,
        '--model', options.model,
        '--timeout-ms', String(options.timeoutMs),
        '--retries', String(options.retries),
        '--min-bytes', String(options.minBytes),
        '--ratio', options.ratio,
        '--tolerance', String(options.tolerance),
        ...variant.images.flatMap((image) => ['--image', image]),
        ...(options.dryRun ? ['--dry-run'] : [])
      ];
      const result = await runGenerator(args);
      if (result.code === 0) {
        results[index] = { name: variant.name, ...parseOutcome(result.stdout) };
      } else {
        results[index] = { name: variant.name, status: 'failed', error: result.stderr.trim() || 'generator failed' };
        if (/HTTP (?:400|401|403|429)\b|usage_limit_reached|Unauthorized/i.test(result.stderr)) {
          stoppedReason = results[index].error;
        }
      }
    }
  };
  await Promise.all(Array.from({ length: Math.min(options.jobs, variants.length) }, worker));
  for (let index = 0; index < variants.length; index += 1) {
    results[index] ??= { name: variants[index].name, status: 'not-started', error: stoppedReason };
  }
  const summary = {
    model: options.model,
    generated: results.filter((result) => result.status === 'generated').length,
    skipped: results.filter((result) => result.status === 'skipped').length,
    dryRun: results.filter((result) => result.status === 'dry-run').length,
    failed: results.filter((result) => result.status === 'failed').length,
    notStarted: results.filter((result) => result.status === 'not-started').length,
    results
  };
  console.log(JSON.stringify(summary));
  if (summary.failed > 0) process.exitCode = 1;
}

main().catch((error) => {
  console.error(`god-tibo-imagen batch: ${error.message}`);
  process.exitCode = 1;
});
