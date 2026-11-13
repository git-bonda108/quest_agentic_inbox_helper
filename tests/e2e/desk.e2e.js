// End-to-end pass of the review desk in a real browser, on the unseen (adversarial) inbox.
const { chromium } = require('playwright');
const base = process.argv[2];
const shot = process.argv[3];
const results = [];
const check = (name, ok, detail = '') => { results.push({ name, ok: !!ok, detail }); };

(async () => {
  const browser = await chromium.launch();
  const errors = [];
  let dialogs = 0;
  const open = async (viewport, scale) => {
    const context = await browser.newContext({ viewport, deviceScaleFactor: scale });
    const page = await context.newPage();
    page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
    page.on('pageerror', e => errors.push(String(e)));
    page.on('dialog', async d => { dialogs += 1; await d.dismiss(); });
    return page;
  };
  const signIn = async (page, name) => {
    await page.goto(base + '/');
    await page.fill('input[name="name"]', name);
    await page.click('button.primary');
    await page.waitForSelector('p.summary');
  };
  const counts = async page => (await page.locator('p.summary').innerText());

  const rita = await open({ width: 1280, height: 900 }, 2);
  await rita.goto(base + '/');
  check('unsigned visitor is sent to sign-in', /login/.test(rita.url()));
  await signIn(rita, 'Rita');
  const before = await counts(rita);
  check('desk shows the counts line', /to review/.test(before), before.trim());
  const body = await rita.content();
  check('injected wrapper text is shown as text', body.includes('&lt;/candidate_message&gt;'));
  check('no message for a person has a reply box', await rita.locator('section:has(h2:has-text("Needs a person")) textarea').count() === 0);
  check('blocked message says why', body.includes('content filter blocked this message'));
  check('recorded source is stated on the page', /RECORDED model outputs/.test(body));
  const drafts = await rita.locator('textarea').count();
  check('one reply box per draft', drafts === 21, String(drafts));
  if (shot) await rita.screenshot({ path: shot, fullPage: false });

  // A second reviewer opens the same desk before Rita acts.
  const omar = await open({ width: 1280, height: 900 }, 1);
  await signIn(omar, 'Omar');

  // Rita edits the first draft and approves it.
  const first = rita.locator('form.reply').first();
  const edited = 'Hi Jamal,\n\nThank you for your patience. A member of the hiring team will follow up.\n\nLarkfield Labs Hiring Team';
  await first.locator('textarea').fill(edited);
  await first.locator('button.primary').click();
  await rita.waitForLoadState();
  const sentText = await rita.locator('section:has(h2:has-text("Sent"))').innerText();
  check('edited text is what appears as sent', sentText.includes('Thank you for your patience'));
  check('reply boxes drop by one after sending', await rita.locator('textarea').count() === 20);

  // Omar, on his stale page, approves the same draft with different text.
  const stale = omar.locator('form.reply').first();
  await stale.locator('textarea').fill('Hi Jamal,\n\nDifferent text from a stale page.\n\nLarkfield Labs Hiring Team');
  const [response] = await Promise.all([
    omar.waitForResponse(r => r.request().method() === 'POST'),
    stale.locator('button.primary').click(),
  ]);
  check('second reviewer on a stale page is refused', response.status() === 409, String(response.status()));

  // Rita rejects the next draft.
  await rita.goto(base + '/');
  await rita.locator('form.reply').first().locator('button.danger').click();
  await rita.waitForLoadState();
  check('rejected draft is listed as rejected', /1 rejected/.test(await counts(rita)), (await counts(rita)).trim());

  // Audit trail.
  await rita.goto(base + '/audit');
  const audit = await rita.locator('body').innerText();
  check('audit names Rita for the approval', /Rita[\s\S]*approved|approved[\s\S]*Rita/.test(audit));
  check('audit never names Omar as approving', !/Omar\s+approved/.test(audit));
  check('audit shows the stale text was never sent', !audit.includes('stale page'));

  // Phone width.
  const phone = await open({ width: 390, height: 844 }, 1);
  await signIn(phone, 'Mina');
  const overflow = await phone.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  check('no sideways scroll at phone width', overflow <= 0, String(overflow));

  // Sign out.
  await rita.goto(base + '/');
  const out = rita.locator('form[action="/logout"] button');
  if (await out.count()) { await out.first().click(); await rita.waitForLoadState(); await rita.goto(base + '/'); }
  check('after sign-out the desk asks for sign-in again', /login/.test(rita.url()));

  check('no script from a message ran', dialogs === 0, String(dialogs));
  const unexpected = errors.filter(e => !/409/.test(e));
  check('no console errors', unexpected.length === 0, unexpected.join(' | ').slice(0, 300));
  await browser.close();
  const failed = results.filter(r => !r.ok);
  for (const r of results) console.log(`${r.ok ? 'PASS' : 'FAIL'}  ${r.name}${r.detail ? '  [' + r.detail + ']' : ''}`);
  console.log(`${results.length - failed.length}/${results.length} passed`);
  process.exit(failed.length ? 1 : 0);
})().catch(e => { console.error('CRASH', e); process.exit(2); });
