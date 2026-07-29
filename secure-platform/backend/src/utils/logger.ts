import winston from 'winston';
import path from 'path';
import fs from 'fs';
import { config, isProduction } from '../config';

export type LogLevel = 'error' | 'warn' | 'info' | 'http' | 'verbose' | 'debug' | 'silly';

export interface LoggerMeta {
  requestId?: string;
  userId?: string;
  traceId?: string;
  [key: string]: unknown;
}

const logDir = path.resolve(config.log.dir);

if (!fs.existsSync(logDir)) {
  fs.mkdirSync(logDir, { recursive: true });
}

const logFormats = {
  timestamp: winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss.SSS' }),
  errors: winston.format.errors({ stack: true }),
  json: winston.format.json({ space: isProduction ? 0 : 2 }),
  prettyPrint: winston.format.prettyPrint(),
};

const consoleFormat = winston.format.combine(
  logFormats.timestamp,
  logFormats.errors,
  winston.format.colorize({ all: true }),
  winston.format.printf(({ level, message, timestamp, stack, ...meta }) => {
    const metaStr = Object.keys(meta).length ? ` ${JSON.stringify(meta)}` : '';
    const stackStr = stack ? `\n${stack}` : '';
    return `[${timestamp}] ${level}: ${message}${metaStr}${stackStr}`;
  })
);

const fileFormat = winston.format.combine(
  logFormats.timestamp,
  logFormats.errors,
  logFormats.json
);

const fileTransports = [
  new winston.transports.File({
    filename: path.join(logDir, 'error.log'),
    level: 'error',
    maxsize: 10 * 1024 * 1024,
    maxFiles: 14,
    format: fileFormat,
    handleExceptions: true,
    handleRejections: true,
  }),
  new winston.transports.File({
    filename: path.join(logDir, 'combined.log'),
    maxsize: 10 * 1024 * 1024,
    maxFiles: 14,
    format: fileFormat,
    handleExceptions: true,
    handleRejections: true,
  }),
];

const consoleTransport = new winston.transports.Console({
  level: config.log.level,
  format: consoleFormat,
  handleExceptions: true,
  handleRejections: true,
});

const createTransports = (): winston.transport[] => {
  const transports: winston.transport[] = [...fileTransports];
  if (!isProduction) {
    transports.push(consoleTransport);
  } else {
    transports.push(consoleTransport);
  }
  return transports;
};

const logger = winston.createLogger({
  level: config.log.level,
  levels: winston.config.npm.levels,
  transports: createTransports(),
  exitOnError: false,
  defaultMeta: {
    service: config.app.name,
    environment: config.app.nodeEnv,
  },
});

export const createChildLogger = (meta: LoggerMeta): winston.Logger => {
  return logger.child(meta);
};

export const stream = {
  write: (message: string): void => {
    logger.http(message.trimEnd());
  },
};

process.on('uncaughtException', (error: Error) => {
  logger.error('Uncaught Exception', { error: error.message, stack: error.stack });
  if (isProduction) {
    setTimeout(() => process.exit(1), 1000);
  }
});

process.on('unhandledRejection', (reason: unknown) => {
  if (reason instanceof Error) {
    logger.error('Unhandled Rejection', { error: reason.message, stack: reason.stack });
  } else {
    logger.error('Unhandled Rejection', { reason });
  }
  if (isProduction) {
    setTimeout(() => process.exit(1), 1000);
  }
});

export default logger;
export { logger };
