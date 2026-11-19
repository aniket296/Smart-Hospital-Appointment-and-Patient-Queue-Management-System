import { chromium } from 'playwright';
import AxeBuilder from '@axe-core/playwright';
import fs from 'fs';
import path from 'path';

const BASE_URL = 'http://127.0.0.1:5173';
const OUTPUT_DIR = path.resolve('qa_audit_results');
const SCREENSHOT_DIR = path.join(OUTPUT_DIR, 'screenshots');

if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

const VIEWPORTS = [
  { name: 'mobile_small', width: 320, height: 568 },
  { name: 'mobile_standard', width: 375, height: 667 },
  { name: 'mobile_large', width: 414, height: 896 },
  { name: 'tablet_portrait', width: 768, height: 1024 },
  { name: 'tablet_landscape', width: 1024, height: 768 },
  { name: 'desktop_standard', width: 1440, height: 900 },
  { name: 'full_hd', width: 1920, height: 1080 },
];

const CREDENTIALS = {
  admin: { email: 'admin@hospital.test', pass: 'Admin@123', role: 'ADMIN', home: '/admin' },
  doctor: { email: 'doctor1@hospital.test', pass: 'Doctor@123', role: 'DOCTOR', home: '/doctor' },
  patient: { email: 'patient1@hospital.test', pass: 'Patient@123', role: 'PATIENT', home: '/patient' },
};

async function runAudit() {
  const browser = await chromium.launch({ headless: true });
  const auditLog = {
    pagesCovered: [],
    consoleErrors: [],
    failedRequests: [],
    a11yViolations: [],
    visualDefects: [],
    layoutIssues: [],
  };

  console.log('--- Starting Comprehensive Visual & A11y Audit ---');

  // Helper to log console & network
  function attachListeners(page, pageName) {
    page.on('console', (msg) => {
      if (msg.type() === 'error' || msg.type() === 'warning') {
        auditLog.consoleErrors.push({
          page: pageName,
          type: msg.type(),
          text: msg.text(),
        });
      }
    });
    page.on('requestfailed', (req) => {
      auditLog.failedRequests.push({
        page: pageName,
        url: req.url(),
        failure: req.failure()?.errorText,
      });
    });
  }

  // 1. Audit Public Pages: /login, /register, /queue
  const publicRoutes = [
    { path: '/login', name: 'login_page' },
    { path: '/register', name: 'register_page' },
    { path: '/queue', name: 'queue_board' },
  ];

  for (const route of publicRoutes) {
    for (const vp of VIEWPORTS) {
      const context = await browser.newContext({ viewport: { width: vp.width, height: vp.height } });
      const page = await context.newPage();
      attachListeners(page, `${route.name}_${vp.name}`);

      await page.goto(`${BASE_URL}${route.path}`, { waitUntil: 'networkidle' });
      await page.waitForTimeout(500);

      // Check horizontal scroll
      const hasHorizontalScroll = await page.evaluate(() => {
        return document.documentElement.scrollWidth > document.documentElement.clientWidth;
      });
      if (hasHorizontalScroll) {
        auditLog.layoutIssues.push({
          route: route.path,
          viewport: vp.name,
          issue: 'Horizontal overflow / scrollbar detected',
        });
      }

      const ssPath = path.join(SCREENSHOT_DIR, `${route.name}_${vp.name}.png`);
      await page.screenshot({ path: ssPath, fullPage: true });

      // Run Axe accessibility scan on desktop standard & mobile standard
      if (vp.name === 'desktop_standard' || vp.name === 'mobile_standard') {
        try {
          const axeResults = await new AxeBuilder({ page }).analyze();
          if (axeResults.violations.length > 0) {
            auditLog.a11yViolations.push({
              route: route.path,
              viewport: vp.name,
              violations: axeResults.violations.map((v) => ({
                id: v.id,
                impact: v.impact,
                description: v.description,
                helpUrl: v.helpUrl,
                nodes: v.nodes.length,
              })),
            });
          }
        } catch (e) {
          console.error(`Axe scan failed on ${route.path}:`, e.message);
        }
      }

      await context.close();
    }
    auditLog.pagesCovered.push(route.path);
  }

  // 2. Audit Role-Protected Pages: Patient Dashboard, Doctor Dashboard, Admin Dashboard, Notifications, Reports
  const roleScenarios = [
    {
      roleName: 'patient',
      creds: CREDENTIALS.patient,
      routes: [
        { path: '/patient', name: 'patient_dashboard' },
        { path: '/notifications', name: 'patient_notifications' },
      ],
    },
    {
      roleName: 'doctor',
      creds: CREDENTIALS.doctor,
      routes: [
        { path: '/doctor', name: 'doctor_dashboard' },
      ],
    },
    {
      roleName: 'admin',
      creds: CREDENTIALS.admin,
      routes: [
        { path: '/admin', name: 'admin_dashboard' },
        { path: '/reports', name: 'admin_reports' },
      ],
    },
  ];

  for (const scenario of roleScenarios) {
    for (const vp of VIEWPORTS) {
      const context = await browser.newContext({ viewport: { width: vp.width, height: vp.height } });
      const page = await context.newPage();
      attachListeners(page, `${scenario.roleName}_${vp.name}`);

      // Perform login
      await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle' });
      await page.fill('#login-email', scenario.creds.email);
      await page.fill('#login-password', scenario.creds.pass);
      await page.click('button[type="submit"]');
      await page.waitForURL(`**${scenario.creds.home}`, { timeout: 10000 });
      await page.waitForTimeout(500);

      for (const r of scenario.routes) {
        await page.goto(`${BASE_URL}${r.path}`, { waitUntil: 'networkidle' });
        await page.waitForTimeout(800);

        const hasHorizontalScroll = await page.evaluate(() => {
          return document.documentElement.scrollWidth > document.documentElement.clientWidth;
        });
        if (hasHorizontalScroll) {
          auditLog.layoutIssues.push({
            route: r.path,
            role: scenario.roleName,
            viewport: vp.name,
            issue: 'Horizontal overflow / scrollbar detected',
          });
        }

        const ssPath = path.join(SCREENSHOT_DIR, `${r.name}_${vp.name}.png`);
        await page.screenshot({ path: ssPath, fullPage: true });

        // Run Axe accessibility scan
        if (vp.name === 'desktop_standard' || vp.name === 'mobile_standard') {
          try {
            const axeResults = await new AxeBuilder({ page }).analyze();
            if (axeResults.violations.length > 0) {
              auditLog.a11yViolations.push({
                route: r.path,
                role: scenario.roleName,
                viewport: vp.name,
                violations: axeResults.violations.map((v) => ({
                  id: v.id,
                  impact: v.impact,
                  description: v.description,
                  helpUrl: v.helpUrl,
                  nodes: v.nodes.length,
                })),
              });
            }
          } catch (e) {
            console.error(`Axe scan failed on ${r.path}:`, e.message);
          }
        }
      }

      await context.close();
    }
  }

  // 3. Test End-to-End Visual User Flows:
  // Flow A: Patient self-registration with QA_TEST_ prefix -> patient dashboard booking -> token appearance
  {
    console.log('Testing Flow A: Registration & Online Booking...');
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();
    attachListeners(page, 'flow_a_registration');

    await page.goto(`${BASE_URL}/register`, { waitUntil: 'networkidle' });
    const testEmail = `qa_test_${Date.now()}@hospital.test`;
    await page.fill('#reg-name', 'QA_TEST_Patient One');
    await page.fill('#reg-email', testEmail);
    await page.fill('#reg-phone', '9898001122');
    await page.fill('#reg-password', 'QaTestPass@123');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'flow_a_1_register_form.png') });
    await page.click('button[type="submit"]');

    await page.waitForURL(`**/patient`, { timeout: 10000 });
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'flow_a_2_patient_landing.png') });

    // Select tomorrow's date so slots are active
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const tomorrowStr = tomorrow.toISOString().split('T')[0];
    await page.fill('#appointment-date', tomorrowStr);
    await page.waitForTimeout(600);

    // Select doctor & open slot
    await page.waitForSelector('.slot-btn:not(.slot-disabled)');
    const firstOpenSlot = await page.locator('.slot-btn:not(.slot-disabled)').first();
    const slotTimeText = await firstOpenSlot.innerText();
    await firstOpenSlot.click();
    await page.fill('#booking-reason', 'QA_TEST_Routine Checkup');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'flow_a_3_slot_selected.png') });
    await page.click('button:has-text("Confirm Online Booking")');

    await page.waitForSelector('.alert-success', { timeout: 8000 });
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'flow_a_4_booking_confirmed.png') });
    await context.close();
  }

  // Flow B: Admin Walk-In Booking -> Doctor Call -> Complete
  {
    console.log('Testing Flow B: Admin Walk-In & Doctor Consultation...');
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();
    attachListeners(page, 'flow_b_admin');

    await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle' });
    await page.fill('#login-email', CREDENTIALS.admin.email);
    await page.fill('#login-password', CREDENTIALS.admin.pass);
    await page.click('button[type="submit"]');
    await page.waitForURL(`**/admin`, { timeout: 10000 });

    await page.fill('#walkin-name', 'QA_TEST_Walkin Patient');
    await page.fill('#walkin-phone', '9898989898');
    await page.fill('#walkin-reason', 'QA_TEST_High fever walkin');
    // Specify tomorrow so daytime slots are available
    await page.evaluate(() => {
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      const tomorrowStr = tomorrow.toISOString().split('T')[0];
      const dateInput = document.querySelector('input[type="date"]');
      if (dateInput) {
        dateInput.value = tomorrowStr;
        dateInput.dispatchEvent(new Event('change', { bubbles: true }));
      }
    });
    // Specify a valid morning slot
    await page.fill('#walkin-slot', '11:00');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'flow_b_1_admin_walkin_form.png') });
    await page.click('button:has-text("Confirm Walk-in & Issue Token")');
    await page.waitForSelector('.alert-success', { timeout: 8000 });
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'flow_b_2_admin_walkin_confirmed.png') });

    // Switch to doctor
    await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle' });
    // Click logout if navbar present
    if (await page.$('button:has-text("Logout")')) {
      await page.click('button:has-text("Logout")');
    }
    await page.fill('#login-email', CREDENTIALS.doctor.email);
    await page.fill('#login-password', CREDENTIALS.doctor.pass);
    await page.click('button[type="submit"]');
    await page.waitForURL(`**/doctor`, { timeout: 10000 });
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'flow_b_3_doctor_queue.png') });

    await context.close();
  }

  await browser.close();

  fs.writeFileSync(path.join(OUTPUT_DIR, 'audit_summary.json'), JSON.stringify(auditLog, null, 2));
  console.log('--- Visual & A11y Audit Complete. Summary saved to qa_audit_results/ ---');
}

runAudit().catch((err) => {
  console.error('Audit run error:', err);
  process.exit(1);
});
