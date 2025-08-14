// Example using Playwright directly since MCP isn't showing in Claude Code
const { chromium } = require('playwright');

async function testAlertSystem() {
  const browser = await chromium.launch({ 
    headless: false,
    slowMo: 50 // Slow down for visibility
  });
  
  const context = await browser.newContext();
  const page = await context.newPage();
  
  // Navigate to the application
  await page.goto('http://localhost:5173');
  console.log('✅ Opened application');
  
  // Take a screenshot
  await page.screenshot({ path: 'alert-dashboard.png' });
  console.log('📸 Screenshot saved as alert-dashboard.png');
  
  // Check if real alerts are visible
  const alertCount = await page.locator('table tbody tr').count();
  console.log(`📊 Found ${alertCount} alerts in the table`);
  
  await browser.close();
}

testAlertSystem().catch(console.error);