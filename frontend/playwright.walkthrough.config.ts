import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir:'./tests/walkthrough',
  outputDir:'../docs/audit/evidence/walkthrough/test-results',
  timeout:45000,
  workers:1,
  reporter:[['list']],
  use:{
    baseURL:process.env.FINSIGHT_TEST_URL || 'http://localhost:4000',
    viewport:{width:1440,height:1000},
    launchOptions:{
      executablePath:process.env.CHROME_EXECUTABLE || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
      args:process.env.FINSIGHT_SOFTWARE_GL === '1' ? ['--use-angle=swiftshader','--enable-unsafe-swiftshader'] : [],
    },
    screenshot:'only-on-failure',
  },
})
