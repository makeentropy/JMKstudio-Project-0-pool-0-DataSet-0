import type { Config } from 'jest';

const config: Config = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  roots: ['<rootDir>/tests', '<rootDir>/backend/src'],
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json'],
  transform: {
    '^.+\\.tsx?$': [
      'ts-jest',
      {
        tsconfig: {
          target: 'ES2020',
          module: 'commonjs',
          strict: true,
          esModuleInterop: true,
          skipLibCheck: true,
          resolveJsonModule: true,
          declaration: false,
          sourceMap: true,
          outDir: './dist',
        },
      },
    ],
  },
  collectCoverageFrom: [
    'backend/src/**/*.ts',
    '!backend/src/**/*.d.ts',
    '!backend/src/**/index.ts',
  ],
  coverageThreshold: {
    global: {
      lines: 80,
      branches: 70,
    },
  },
  coverageReporters: ['text-summary', 'lcov', 'json'],
  testMatch: [
    '**/tests/**/*.test.ts',
    '**/tests/**/*.spec.ts',
  ],
  setupFilesAfterEnv: [],
  verbose: true,
  forceExit: true,
  detectOpenHandles: false,
  maxWorkers: '50%',
  moduleNameMapper: {
    '^@config/(.*)$': '<rootDir>/backend/src/config/$1',
    '^@utils/(.*)$': '<rootDir>/backend/src/utils/$1',
    '^@middleware/(.*)$': '<rootDir>/backend/src/middleware/$1',
  },
};

export default config;
