import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

export interface ChannelConfig {
  enabled: boolean;
}

export interface TelegramConfig extends ChannelConfig {
  token: string;
  allowedIds: string[];
}

export interface EmailConfig extends ChannelConfig {
  allowed: string[];
  from: string;
}

export interface GatewayConfig {
  projectDir: string;
  envFilePath: string;
  dataDir: string;
  dbPath: string;
  sessionsDir: string;
  pollSeconds: number;
  telegram: TelegramConfig;
  email: EmailConfig;
}

function loadEnvFile(filePath: string): void {
  if (!fs.existsSync(filePath)) {
    return;
  }

  const content = fs.readFileSync(filePath, "utf8");

  for (const line of content.split(/\r?\n/)) {
    const trimmed = line.trim();

    if (!trimmed || trimmed.startsWith("#")) {
      continue;
    }

    const separatorIndex = trimmed.indexOf("=");

    if (separatorIndex === -1) {
      continue;
    }

    const key = trimmed.slice(0, separatorIndex).trim();
    let value = trimmed.slice(separatorIndex + 1).trim();

    if (!key || Object.prototype.hasOwnProperty.call(process.env, key)) {
      continue;
    }

    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }

    process.env[key] = value;
  }
}

function parseCsv(value: string | undefined): string[] {
  if (!value) {
    return [];
  }

  return value
    .split(",")
    .map((entry) => entry.trim())
    .filter(Boolean);
}

function parsePositiveInteger(value: string | undefined, fallback: number, name: string): number {
  if (!value) {
    return fallback;
  }

  const parsed = Number.parseInt(value, 10);

  if (Number.isNaN(parsed) || parsed <= 0) {
    throw new Error(`${name} must be a positive integer.`);
  }

  return parsed;
}

function resolveProjectDir(): string {
  const currentFilePath = fileURLToPath(import.meta.url);
  const currentDir = path.dirname(currentFilePath);

  return path.resolve(currentDir, "..");
}

export function loadConfig(): GatewayConfig {
  const projectDir = resolveProjectDir();
  const envFilePath = process.env.CMA_ENV_FILE || path.join(projectDir, ".env");
  loadEnvFile(envFilePath);

  const dataDir = process.env.CMA_DATA_DIR || path.join(projectDir, ".cma");
  const telegramToken = process.env.TELEGRAM_TOKEN || "";
  const telegramAllowedIds = parseCsv(process.env.TELEGRAM_ALLOWED_IDS);
  const emailAllowed = parseCsv(process.env.EMAIL_ALLOWED);
  const mailFrom = process.env.MAIL_FROM || "";

  return {
    projectDir,
    envFilePath,
    dataDir,
    dbPath: path.join(dataDir, "gateway.db"),
    sessionsDir: path.join(dataDir, "sessions"),
    pollSeconds: parsePositiveInteger(process.env.POLL_SECONDS, 60, "POLL_SECONDS"),
    telegram: {
      token: telegramToken,
      allowedIds: telegramAllowedIds,
      enabled: Boolean(telegramToken && telegramAllowedIds.length > 0)
    },
    email: {
      allowed: emailAllowed,
      from: mailFrom,
      enabled: Boolean(mailFrom && emailAllowed.length > 0)
    }
  };
}

export function getConfigWarnings(config: GatewayConfig): string[] {
  const warnings: string[] = [];

  if (config.telegram.token && !config.telegram.allowedIds.length) {
    warnings.push("TELEGRAM_TOKEN is set but TELEGRAM_ALLOWED_IDS is empty. Telegram bootstrapping stays disabled.");
  }

  if (!config.telegram.token && config.telegram.allowedIds.length) {
    warnings.push("TELEGRAM_ALLOWED_IDS is set but TELEGRAM_TOKEN is missing. Telegram bootstrapping stays disabled.");
  }

  if (config.email.from && !config.email.allowed.length) {
    warnings.push("MAIL_FROM is set but EMAIL_ALLOWED is empty. Email bootstrapping stays disabled.");
  }

  if (!config.email.from && config.email.allowed.length) {
    warnings.push("EMAIL_ALLOWED is set but MAIL_FROM is missing. Email bootstrapping stays disabled.");
  }

  return warnings;
}