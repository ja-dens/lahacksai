'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {spawnSync} = require('node:child_process');
const {validatePlan, replaceManaged, syncPlan, writeReport} = require('./sync-planning.cjs');

const readText = file => fs.readFileSync(file, 'utf8');
const loadPlan = () => JSON.parse(readText('planning/backlog.json'));

function fakeGitHub() {
  const state = {labels: [{name: 'human-label', color: 'ffffff'}], milestones: [], issues: [], pulls: [], calls: [], failOnceForTask: null, forbidPulls: false};
  const reply = value => structuredClone(value);
  const failure = (message, status) => Object.assign(new Error(message), {status});
  const api = async (method, endpoint, body) => {
    state.calls.push({method, endpoint, body: reply(body)});
    const pathname = endpoint.split('?')[0];
    if (method === 'GET' && endpoint === '') return {default_branch: 'main'};
    if (method === 'GET' && pathname === '/issues') return reply(state.issues);
    if (method === 'GET' && pathname === '/labels') return reply(state.labels);
    if (method === 'GET' && pathname === '/milestones') return reply(state.milestones);
    if (method === 'GET' && pathname === '/pulls') return reply(state.pulls);
    if (method === 'POST' && pathname === '/labels') {
      state.labels.push(reply(body));
      return reply(body);
    }
    if (method === 'POST' && pathname === '/milestones') {
      const number = state.milestones.length + 1;
      const milestone = {...reply(body), number, state: 'open', html_url: `https://github.com/ja-dens/lahacksai/milestone/${number}`};
      state.milestones.push(milestone);
      return reply(milestone);
    }
    if (method === 'POST' && pathname === '/issues') {
      const number = Math.max(0, ...state.issues.map(issue => issue.number)) + 1;
      const issue = {...reply(body), number, state: 'open', assignees: (body.assignees || []).map(login => ({login})), html_url: `https://github.com/ja-dens/lahacksai/issues/${number}`};
      state.issues.push(issue);
      if (state.failOnceForTask && body.body.includes(`<!-- sticker-plan:${state.failOnceForTask} -->`)) {
        state.failOnceForTask = null;
        throw failure('Simulated lost response after issue creation', 503);
      }
      return reply(issue);
    }
    if (method === 'PATCH' && /^\/issues\/\d+$/.test(pathname)) {
      const issue = state.issues.find(item => item.number === Number(pathname.split('/').pop()));
      assert.ok(issue);
      const patch = reply(body);
      if (patch.assignees) patch.assignees = patch.assignees.map(login => ({login}));
      Object.assign(issue, patch);
      return reply(issue);
    }
    if (method === 'POST' && pathname === '/pulls') {
      if (state.forbidPulls) throw failure('GitHub Actions is not permitted to create pull requests', 403);
      const pr = {...reply(body), number: 100, html_url: 'https://github.com/ja-dens/lahacksai/pull/100'};
      state.pulls.push(pr);
      return reply(pr);
    }
    throw new Error(`Unexpected fake request: ${method} ${endpoint}`);
  };
  return {state, api};
}

const publish = (plan, fake, extras = {}) => syncPlan({plan, readText, api: fake.api, repository: 'ja-dens/lahacksai', branch: 'codex/sticker-planning', sourceCommit: 'test-commit', now: () => '2026-10-17T20:00:00Z', ...extras});

test('reviewed backlog has nine task bodies, independent modules and an acyclic handoff graph', () => {
  const plan = loadPlan();
  assert.doesNotThrow(() => validatePlan(plan, readText));
  assert.equal(plan.issues.length, 9);
  assert.equal(plan.milestones.length, 2);
  assert.deepEqual(plan.owners, {A: null, B: null, C: null, D: null});
  assert.deepEqual(plan.issues.filter(task => task.depends_on.length).map(task => task.id), ['T5']);
  assert.deepEqual(plan.issues.find(task => task.id === 'T8').integration_depends_on, ['T4']);
});

test('bad dependencies, body paths, and usernames fail before publication', () => {
  const cycle = loadPlan();
  cycle.issues[0].depends_on = ['T1'];
  cycle.issues[1].depends_on = ['T0'];
  assert.throws(() => validatePlan(cycle, readText), /cycle/);
  const missing = loadPlan();
  missing.issues[0].depends_on = ['T999'];
  assert.throws(() => validatePlan(missing, readText), /Unknown task dependency/);
  const escape = loadPlan();
  escape.issues[0].body_file = '../../private-file';
  assert.throws(() => validatePlan(escape, readText), /body path/);
  const owner = loadPlan();
  owner.owners.A = 'not/a-username';
  assert.throws(() => validatePlan(owner, readText), /usernames/);
});

test('invalid or cyclic later handoffs fail before publication', () => {
  const missing = loadPlan();
  missing.issues[0].integration_depends_on = ['T999'];
  assert.throws(() => validatePlan(missing, readText), /Unknown integration dependency/);
  const malformed = loadPlan();
  malformed.issues[0].integration_depends_on = 'T1';
  assert.throws(() => validatePlan(malformed, readText), /Unknown integration dependency/);
  const cycle = loadPlan();
  cycle.issues[0].integration_depends_on = ['T8'];
  cycle.issues.find(task => task.id === 'T4').depends_on = ['T0'];
  assert.throws(() => validatePlan(cycle, readText), /cycle/);
  const duplicate = loadPlan();
  duplicate.issues.find(task => task.id === 'T2').depends_on = ['T1'];
  assert.throws(() => validatePlan(duplicate, readText), /Duplicate dependency/);
});

test('a different repository is rejected without a single API request', async () => {
  const fake = fakeGitHub();
  await assert.rejects(publish(loadPlan(), fake, {repository: 'someone/else'}), /differs/);
  assert.equal(fake.state.calls.length, 0);
});

test('initial publish creates one backlog, real dependency references, milestones, and a draft PR', async () => {
  const plan = loadPlan();
  const fake = fakeGitHub();
  const report = await publish(plan, fake);
  assert.equal(report.complete, true);
  assert.equal(fake.state.issues.length, 9);
  assert.equal(fake.state.milestones.length, 2);
  assert.equal(fake.state.labels.length, plan.labels.length + 1);
  assert.equal(report.issues.length, 9);
  const t2 = fake.state.issues.find(issue => issue.body.includes('<!-- sticker-plan:T2 -->'));
  assert.match(t2.body, /## Start dependencies\n\nNone; this task can start independently/);
  assert.match(t2.body, /## Later integration requirements\n\n#2\. These are needed for the later live handoff/);
  const t5 = fake.state.issues.find(issue => issue.body.includes('<!-- sticker-plan:T5 -->'));
  assert.match(t5.body, /## Start dependencies\n\n#3, #4, #5/);
  const t8 = fake.state.issues.find(issue => issue.body.includes('<!-- sticker-plan:T8 -->'));
  assert.match(t8.body, /## Later integration requirements\n\n#5\./);
  assert.equal(fake.state.pulls.length, 1);
  assert.equal(report.pull_request.draft, true);
  assert.ok(fake.state.issues.every(issue => !issue.assignees.length));
});

test('rerun preserves human notes, checked tasks, closed state, assignments, and unrelated labels', async () => {
  const plan = loadPlan();
  const fake = fakeGitHub();
  await publish(plan, fake);
  const t0 = fake.state.issues[0];
  t0.body = `Human introduction.\n\n${t0.body.replace('- [ ] Review IncomingMessage', '- [x] Review IncomingMessage')}\n\nHuman integration note.`;
  t0.state = 'closed';
  t0.title = 'A human clarified this title';
  t0.assignees = [{login: 'existing-owner'}];
  t0.labels.push('human-label');
  const callCount = fake.state.calls.length;
  const report = await publish(plan, fake);
  assert.equal(fake.state.issues.length, 9);
  assert.equal(fake.state.milestones.length, 2);
  assert.equal(fake.state.pulls.length, 1);
  assert.match(t0.body, /^Human introduction\./);
  assert.match(t0.body, /Human integration note\.$/);
  assert.match(t0.body, /- \[x\] Review IncomingMessage/);
  assert.equal(t0.state, 'closed');
  assert.equal(t0.title, 'A human clarified this title');
  assert.deepEqual(t0.assignees, [{login: 'existing-owner'}]);
  assert.ok(t0.labels.includes('human-label'));
  assert.equal(report.issues[0].state, 'closed');
  assert.equal(fake.state.calls.slice(callCount).filter(call => call.method !== 'GET').length, 0);
});

test('removed checked work survives task rewrites and repeated syncs without duplication', () => {
  const task = loadPlan().issues[0];
  const old = '<!-- sticker-plan:T0 -->\nHuman prefix.\n<!-- sticker-plan:managed:start -->\n- [x] Completed earlier investigation.\n<!-- sticker-plan:managed:end -->\nHuman suffix.';
  const first = replaceManaged(old, task, readText, new Map());
  const second = replaceManaged(first, task, readText, new Map());
  assert.match(first, /## Previously checked work/);
  assert.match(first, /- \[x\] Completed earlier investigation\./);
  assert.equal(second, first);
  assert.match(second, /Human prefix\./);
  assert.match(second, /Human suffix\.$/);
});

test('existing Photon checked evidence and interpreter assignment are preserved', async () => {
  const fake = fakeGitHub();
  await publish(loadPlan(), fake);
  const t1 = fake.state.issues.find(issue => issue.body.includes('<!-- sticker-plan:T1 -->'));
  const t3 = fake.state.issues.find(issue => issue.body.includes('<!-- sticker-plan:T3 -->'));
  t1.body += '\nHuman evidence link and phone-access blocker.';
  t3.assignees = [{login: 'existing-model-owner'}];
  await publish(loadPlan(), fake);
  assert.match(t1.body, /- \[x\] Document unsupported operations and investigate a supported fallback channel if needed\./);
  assert.match(t1.body, /- \[x\] Supported formats and line\/channel limitations are recorded honestly\./);
  assert.match(t1.body, /Human evidence link and phone-access blocker\.$/);
  assert.deepEqual(t3.assignees, [{login: 'existing-model-owner'}]);
});

test('main publication updates issues without requesting another pull request', async () => {
  const fake = fakeGitHub();
  const report = await publish(loadPlan(), fake, {branch: 'main'});
  assert.equal(report.complete, true);
  assert.equal(report.issues.length, 9);
  assert.equal(report.pull_request, undefined);
  assert.equal(fake.state.pulls.length, 0);
});

test('retry after a lost creation response finds the created issue instead of duplicating it', async () => {
  const fake = fakeGitHub();
  fake.state.failOnceForTask = 'T3';
  await assert.rejects(publish(loadPlan(), fake), error => {
    assert.equal(error.report.complete, false);
    assert.match(error.report.error, /lost response/);
    return true;
  });
  const report = await publish(loadPlan(), fake);
  assert.equal(report.complete, true);
  assert.equal(fake.state.issues.length, 9);
  assert.equal(fake.state.issues.filter(issue => issue.body.includes('<!-- sticker-plan:T3 -->')).length, 1);
});

test('duplicate task markers stop before mutations rather than guessing which issue to overwrite', async () => {
  const fake = fakeGitHub();
  fake.state.issues.push({number: 10, body: '<!-- sticker-plan:T0 -->'}, {number: 11, body: '<!-- sticker-plan:T0 -->'});
  await assert.rejects(publish(loadPlan(), fake), /Multiple issues/);
  assert.equal(fake.state.calls.filter(call => call.method !== 'GET').length, 0);
});

test('draft PR restrictions are reported without changing repository settings or losing issue publication', async () => {
  const fake = fakeGitHub();
  fake.state.forbidPulls = true;
  const report = await publish(loadPlan(), fake);
  assert.equal(report.complete, true);
  assert.equal(report.issues.length, 9);
  assert.equal(report.pull_request, undefined);
  assert.match(report.warnings[0], /not permitted/);
  assert.match(report.compare_url, /codex%2Fsticker-planning/);
  assert.ok(!fake.state.calls.some(call => call.method === 'PATCH' && call.endpoint === ''));
});

test('a supplied username is added without removing a human assignee', async () => {
  const plan = loadPlan();
  const fake = fakeGitHub();
  await publish(plan, fake);
  fake.state.issues[1].assignees = [{login: 'existing-owner'}];
  plan.owners.A = 'new-owner';
  await publish(plan, fake);
  assert.deepEqual(fake.state.issues[1].assignees.map(user => user.login), ['existing-owner', 'new-owner']);
});

test('the publication report is written to the selected branch and can be read back as JSON', async () => {
  const calls = [];
  const api = async (method, endpoint, body) => {
    calls.push({method, endpoint, body});
    if (method === 'GET') throw Object.assign(new Error('not found'), {status: 404});
    return {content: {sha: 'report-sha'}};
  };
  const report = {repository: 'ja-dens/lahacksai', complete: true, issues: [{id: 'T0', number: 1, url: 'https://github.com/ja-dens/lahacksai/issues/1'}]};
  await writeReport(api, report, 'codex/sticker-planning');
  const write = calls.find(call => call.method === 'PUT');
  assert.equal(write.body.branch, 'codex/sticker-planning');
  assert.deepEqual(JSON.parse(Buffer.from(write.body.content, 'base64').toString()), report);
});

test('CLI defaults to a dry run without credentials or external writes', () => {
  const result = spawnSync(process.execPath, ['.github/scripts/sync-planning.cjs'], {encoding: 'utf8', env: {...process.env, GITHUB_TOKEN: '', GITHUB_REPOSITORY: ''}});
  assert.equal(result.status, 0, result.stderr);
  const output = JSON.parse(result.stdout);
  assert.equal(output.dry_run, true);
  assert.equal(output.external_writes, 0);
  assert.equal(output.issues.length, 9);
  assert.deepEqual(output.issues.find(task => task.id === 'T8').integration_depends_on, ['T4']);
});
