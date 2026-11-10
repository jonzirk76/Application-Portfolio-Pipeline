import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './tests', workers: 1, timeout: 90000,
  use: { baseURL: 'http://127.0.0.1:8000', viewport: { width: 1440, height: 1100 },
    launchOptions: { args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] },
    screenshot: 'only-on-failure', trace: 'retain-on-failure' },
});
