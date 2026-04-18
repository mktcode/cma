import { getConfigWarnings, loadConfig } from "./config.js";
import { GatewayService, type GatewayLogger } from "./service.js";

function createLogger(): GatewayLogger {
  const write = (level: string, message: string): void => {
    console.log(`${new Date().toISOString()} [${level}] ${message}`);
  };

  return {
    info(message) {
      write("info", message);
    },
    warn(message) {
      write("warn", message);
    },
    debug(message) {
      if (process.env.DEBUG) {
        write("debug", message);
      }
    },
    error(message) {
      console.error(`${new Date().toISOString()} [error] ${message}`);
    }
  };
}

export async function main(): Promise<void> {
  const logger = createLogger();
  const config = loadConfig();
  const warnings = getConfigWarnings(config);

  for (const warning of warnings) {
    logger.warn(warning);
  }

  const gateway = new GatewayService({ config, logger });
  let shuttingDown = false;

  const handleSignal = (signal: NodeJS.Signals): void => {
    if (shuttingDown) {
      return;
    }

    shuttingDown = true;

    gateway
      .stop(signal)
      .then(() => {
        process.exit(0);
      })
      .catch((error: unknown) => {
        const message = error instanceof Error ? error.stack || error.message : String(error);
        logger.error(message);
        process.exit(1);
      });
  };

  process.once("SIGINT", () => handleSignal("SIGINT"));
  process.once("SIGTERM", () => handleSignal("SIGTERM"));

  await gateway.start();
  logger.info("gateway bootstrap started");
}

main().catch((error: unknown) => {
  const message = error instanceof Error ? error.stack || error.message : String(error);
  console.error(`${new Date().toISOString()} [error] ${message}`);
  process.exit(1);
});