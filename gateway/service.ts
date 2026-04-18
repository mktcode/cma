import fs from "node:fs/promises";

import type { GatewayConfig } from "./config.js";

export interface GatewayLogger {
  info(message: string): void;
  warn(message: string): void;
  debug(message: string): void;
  error(message: string): void;
}

export class GatewayService {
  private readonly config: GatewayConfig;
  private readonly logger: GatewayLogger;
  private interval: NodeJS.Timeout | null;

  constructor({ config, logger }: { config: GatewayConfig; logger: GatewayLogger }) {
    this.config = config;
    this.logger = logger;
    this.interval = null;
  }

  async start(): Promise<void> {
    await fs.mkdir(this.config.sessionsDir, { recursive: true });

    this.logger.info(`state directory ready at ${this.config.dataDir}`);
    this.logger.info(`session storage ready at ${this.config.sessionsDir}`);
    this.logger.info(`sqlite path reserved at ${this.config.dbPath}`);
    this.logger.info(`telegram bootstrap ${this.config.telegram.enabled ? "enabled" : "disabled"}`);
    this.logger.info(`email bootstrap ${this.config.email.enabled ? "enabled" : "disabled"}`);
    this.logger.info(`poll interval set to ${this.config.pollSeconds}s`);

    // Keep the first MVP alive so later channel adapters can plug into a stable host.
    this.interval = setInterval(() => {
      this.tick();
    }, this.config.pollSeconds * 1000);
  }

  tick(): void {
    this.logger.debug("poll tick");
  }

  async stop(reason = "shutdown"): Promise<void> {
    if (this.interval) {
      clearInterval(this.interval);
      this.interval = null;
    }

    this.logger.info(`gateway stopped (${reason})`);
  }
}