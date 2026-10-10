// @ts-nocheck
import os from 'node:os';
import path from 'node:path';

import { PRIVATE_CODEX_PROVIDER } from './providers/providerTypes.js';

const DEFAULT_CODEX_HOME = path.join(os.homedir(), '.codex');

// User policy (2026-09-27): every image request uses this Codex caller model, unconditionally.
export const REQUIRED_CODEX_MODEL = 'gpt-6-astra';

/**
 * Return the fixed Codex caller model. Any other requested value is ignored with a warning.
 *
 * @param {string | null | undefined} model - Requested model, if any.
 * @param {string} [source='model'] - Label used in the warning.
 * @param {(message: string) => void} [warn] - Warning sink; defaults to stderr.
 * @returns {string} Always REQUIRED_CODEX_MODEL.
 */
export function enforceCodexModel(model, source = 'model', warn = (message) => console.warn(message)) {
  if (model !== undefined && model !== null && model !== '' && model !== REQUIRED_CODEX_MODEL) {
    warn(`warning: ${source} "${model}" ignored; image generation always uses ${REQUIRED_CODEX_MODEL}.`);
  }
  return REQUIRED_CODEX_MODEL;
}

/**
 * Resolve the runtime configuration for the CLI/library.
 *
 * @param {{ codexHome?: string, baseUrl?: string, authFile?: string, installationIdFile?: string, generatedImagesDir?: string, provider?: string, defaultModel?: string, originator?: string, defaultOutputPath?: string }} [overrides={}] - Optional configuration overrides.
 * @returns {{ baseUrl: string, codexHome: string, authFile: string, installationIdFile: string, generatedImagesDir: string, provider: string, defaultModel: string, defaultOriginator: string, defaultOutputPath: string }} Fully resolved config.
 */
export function resolveConfig(overrides = {}) {
  const codexHome = overrides.codexHome || process.env.CODEX_HOME || DEFAULT_CODEX_HOME;
  const baseUrl = overrides.baseUrl || process.env.CODEX_IMAGEGEN_BASE_URL || 'https://chatgpt.com/backend-api/codex';
  const authFile = overrides.authFile || process.env.CODEX_IMAGEGEN_AUTH_FILE || path.join(codexHome, 'auth.json');
  const installationIdFile =
    overrides.installationIdFile ||
    process.env.CODEX_IMAGEGEN_INSTALLATION_ID_FILE ||
    path.join(codexHome, 'installation_id');
  const generatedImagesDir =
    overrides.generatedImagesDir ||
    process.env.CODEX_IMAGEGEN_GENERATED_IMAGES_DIR ||
    path.join(codexHome, 'generated_images');

  return {
    baseUrl,
    codexHome,
    authFile,
    installationIdFile,
    generatedImagesDir,
    provider: overrides.provider || process.env.CODEX_IMAGEGEN_PROVIDER || PRIVATE_CODEX_PROVIDER,
    // CODEX_IMAGEGEN_MODEL and CODEX_MODEL are intentionally ignored so the session model cannot leak in.
    defaultModel: enforceCodexModel(overrides.defaultModel, 'defaultModel'),
    defaultOriginator:
      overrides.originator || process.env.CODEX_IMAGEGEN_ORIGINATOR || process.env.CODEX_INTERNAL_ORIGINATOR_OVERRIDE || 'codex_cli_rs',
    defaultOutputPath:
      overrides.defaultOutputPath ||
      process.env.CODEX_IMAGEGEN_OUTPUT ||
      path.resolve(process.cwd(), `generated-${Date.now()}.png`)
  };
}

export const UNSUPPORTED_WARNING =
  'WARNING: This project calls an unsupported private Codex backend path. The contract may break without notice.';
