'use strict';

const fs = require('node:fs');
const path = require('node:path');

const START = '<!-- sticker-plan:managed:start -->';
const END = '<!-- sticker-plan:managed:end -->';
const marker = id => `<!-- sticker-plan:${id} -->`;

function validatePlan(plan, readText) {
  if (plan.schema_version !== 1 || !/^[\w.-]+\/[\w.-]+$/.test(plan.repository || '')) {
    throw new Error('Invalid planning version or repository.');
  }
  for (const key of ['labels', 'milestones', 'issues']) {
    if (!Array.isArray(plan[key]) || !plan[key].length) throw new Error(`Missing ${key}.`);
  }
  const unique = (items, key) => {
    const values = items.map(item => item[key]);
    if (values.some(value => typeof value !== 'string' || !value.trim()) || new Set(values).size !== values.length) {
      throw new Error(`Invalid or duplicate ${key}.`);
    }
    return new Set(values);
  };
  const labels = unique(plan.labels, 'name');
  const milestones = unique(plan.milestones, 'id');
  unique(plan.milestones, 'title');
  const ids = unique(plan.issues, 'id');
  for (const label of plan.labels) {
    if (!/^[0-9a-f]{6}$/i.test(label.color)) throw new Error('Invalid label color.');
  }
  if (!plan.owners || typeof plan.owners !== 'object') throw new Error('Missing owner map.');
  for (const username of Object.values(plan.owners)) {
    if (username !== null && !/^[a-z\d](?:[a-z\d-]{0,37}[a-z\d])?$/i.test(username)) {
      throw new Error('Owner usernames must be valid GitHub usernames or null.');
    }
  }
  for (const task of plan.issues) {
    if (!/^T\d+$/.test(task.id) || typeof task.title !== 'string' || !task.title.trim()) throw new Error('Invalid task.');
    if (!Object.hasOwn(plan.owners, task.owner_role) || !milestones.has(task.milestone)) throw new Error('Unknown task owner or milestone.');
    if (!Array.isArray(task.labels) || task.labels.some(label => !labels.has(label))) throw new Error('Unknown task label.');
    if (!Array.isArray(task.depends_on) || task.depends_on.some(id => !ids.has(id))) throw new Error('Unknown task dependency.');
    if (task.body_file !== `planning/issues/${task.id}.md`) throw new Error('Task body path must match its ID.');
    if (readText(task.body_file).includes('<!-- sticker-plan:')) throw new Error('Task bodies must not contain publisher markers.');
  }
  const visiting = new Set();
  const visited = new Set();
  const tasks = new Map(plan.issues.map(task => [task.id, task]));
  function visit(id) {
    if (visiting.has(id)) throw new Error('Task dependency cycle.');
    if (visited.has(id)) return;
    visiting.add(id);
    for (const dependency of tasks.get(id).depends_on) visit(dependency);
    visiting.delete(id);
    visited.add(id);
  }
  for (const id of ids) visit(id);
}

function preserveCheckedItems(text, previous) {
  const checked = new Set([...previous.matchAll(/^\s*- \[[xX]\] (.+)$/gm)].map(match => match[1]));
  return text.replace(/^(\s*- )\[ \] (.+)$/gm, (line, prefix, label) => checked.has(label) ? `${prefix}[x] ${label}` : line);
}

function managedSection(task, readText, issueMap) {
  const dependencies = task.depends_on.map(id => issueMap.has(id) ? `#${issueMap.get(id).number}` : id);
  return `${START}\n${readText(task.body_file).trim()}\n\n## Dependencies\n\n${dependencies.length ? dependencies.join(', ') : 'None; this task can start independently.'}\n\nPlanning ID: ${task.id}. Source: ${task.body_file}. Owner role: ${task.owner_role}.\n${END}`;
}

function replaceManaged(previous, task, readText, issueMap) {
  const section = preserveCheckedItems(managedSection(task, readText, issueMap), previous);
  const start = previous.indexOf(START);
  const end = previous.indexOf(END, start >= 0 ? start + START.length : 0);
  if ((start >= 0) !== (end >= 0)) throw new Error(`Incomplete managed section for ${task.id}; preserve and inspect it.`);
  if (start >= 0) return previous.slice(0, start) + section + previous.slice(end + END.length);
  return previous ? `${previous}\n\n${section}` : `${marker(task.id)}\n\n${section}`;
}

async function listAll(api, endpoint) {
  const values = [];
  for (let page = 1; page <= 100; page++) {
    const batch = await api('GET', `${endpoint}${endpoint.includes('?') ? '&' : '?'}per_page=100&page=${page}`);
    if (!Array.isArray(batch)) throw new Error(`Expected a list from ${endpoint}.`);
    values.push(...batch);
    if (batch.length < 100) return values;
  }
  throw new Error(`Pagination exceeded the planning limit for ${endpoint}.`);
}

async function syncPlan({plan, readText, api, repository, branch, sourceCommit, now = () => new Date().toISOString()}) {
  validatePlan(plan, readText);
  if (repository !== plan.repository) throw new Error('Refusing to publish to a repository that differs from backlog.json.');
  if (!branch || /[\r\n]/.test(branch)) throw new Error('A valid source branch is required.');
  const report = {repository, branch, source_commit: sourceCommit, generated_at: now(), complete: false, issues: [], milestones: [], warnings: []};
  try {
    const repo = await api('GET', '');
    const existingIssues = (await listAll(api, '/issues?state=all')).filter(issue => !issue.pull_request);
    const issueMap = new Map();
    for (const task of plan.issues) {
      const matches = existingIssues.filter(issue => (issue.body || '').includes(marker(task.id)));
      if (matches.length > 1) throw new Error(`Multiple issues contain ${marker(task.id)}; no duplicate backlog will be created.`);
      if (matches.length) issueMap.set(task.id, matches[0]);
    }
    const existingLabels = await listAll(api, '/labels');
    const names = new Set(existingLabels.map(label => label.name.toLowerCase()));
    for (const label of plan.labels) {
      if (!names.has(label.name.toLowerCase())) await api('POST', '/labels', label);
    }
    const existingMilestones = await listAll(api, '/milestones?state=all');
    const milestoneMap = new Map();
    for (const milestone of plan.milestones) {
      let actual = existingMilestones.find(item => item.title === milestone.title);
      if (!actual) actual = await api('POST', '/milestones', {title: milestone.title, description: milestone.description});
      milestoneMap.set(milestone.id, actual);
      report.milestones.push({id: milestone.id, number: actual.number, url: actual.html_url});
    }
    for (const task of plan.issues) {
      if (!issueMap.has(task.id)) {
        const desired = {title: `[${task.id}] ${task.title}`, body: replaceManaged('', task, readText, issueMap), labels: task.labels, milestone: milestoneMap.get(task.milestone).number};
        const username = plan.owners[task.owner_role];
        if (username) desired.assignees = [username];
        const issue = await api('POST', '/issues', desired);
        issueMap.set(task.id, issue);
      }
      const issue = issueMap.get(task.id);
      report.issues.push({id: task.id, number: issue.number, url: issue.html_url, state: issue.state, owner_role: task.owner_role});
    }
    for (const task of plan.issues) {
      const issue = issueMap.get(task.id);
      const desiredBody = replaceManaged(issue.body || '', task, readText, issueMap);
      const currentLabels = (issue.labels || []).map(label => typeof label === 'string' ? label : label.name);
      const labels = [...new Set([...currentLabels, ...task.labels])];
      const patch = {};
      if (desiredBody !== issue.body) patch.body = desiredBody;
      if (labels.length !== currentLabels.length) patch.labels = labels;
      const username = plan.owners[task.owner_role];
      const assignees = (issue.assignees || []).map(user => user.login);
      if (username && !assignees.includes(username)) patch.assignees = [...assignees, username];
      if (Object.keys(patch).length) issueMap.set(task.id, await api('PATCH', `/issues/${issue.number}`, patch));
    }
    const base = repo.default_branch;
    report.compare_url = `https://github.com/${repository}/compare/${encodeURIComponent(base)}...${encodeURIComponent(branch)}`;
    if (branch !== base) {
      try {
        const head = `${repository.split('/')[0]}:${branch}`;
        const pulls = await listAll(api, `/pulls?state=open&head=${encodeURIComponent(head)}&base=${encodeURIComponent(base)}`);
        const pr = pulls[0] || await api('POST', '/pulls', {
          title: 'docs: add sticker interpreter plan and task automation',
          head: branch, base, draft: true,
          body: `${readText('planning/PULL_REQUEST_BODY.md').trim()}\n\n## Published task backlog\n\n${report.issues.map(issue => `- ${issue.id}: ${issue.url}`).join('\n')}`
        });
        report.pull_request = {number: pr.number, url: pr.html_url, draft: pr.draft};
      } catch (error) {
        report.warnings.push(`Draft PR could not be confirmed: ${error.message}`);
      }
    }
    report.complete = true;
    return report;
  } catch (error) {
    error.report = {...report, error: error.message};
    throw error;
  }
}

function githubApi(repository, token) {
  if (!/^[\w.-]+\/[\w.-]+$/.test(repository) || !token) throw new Error('Repository and workflow token are required.');
  return async (method, endpoint, body) => {
    if (endpoint && !endpoint.startsWith('/')) throw new Error('Only repository-relative API endpoints are permitted.');
    const response = await fetch(`https://api.github.com/repos/${repository}${endpoint}`, {
      method,
      headers: {Authorization: `Bearer ${token}`, Accept: 'application/vnd.github+json', 'Content-Type': 'application/json', 'X-GitHub-Api-Version': '2022-11-28'},
      ...(body === undefined ? {} : {body: JSON.stringify(body)}),
      signal: AbortSignal.timeout(30000)
    });
    const text = await response.text();
    let data;
    try { data = text ? JSON.parse(text) : null; } catch { data = null; }
    if (!response.ok) {
      const error = new Error(`${method} ${endpoint}: HTTP ${response.status}${data?.message ? ` - ${data.message}` : ''}`);
      error.status = response.status;
      throw error;
    }
    return data;
  };
}

async function writeReport(api, report, branch) {
  const endpoint = '/contents/planning/published.json';
  let sha;
  try { sha = (await api('GET', `${endpoint}?ref=${encodeURIComponent(branch)}`)).sha; }
  catch (error) { if (error.status !== 404) throw error; }
  await api('PUT', endpoint, {
    message: 'docs: record published sticker planning links',
    branch,
    content: Buffer.from(`${JSON.stringify(report, null, 2)}\n`).toString('base64'),
    ...(sha ? {sha} : {})
  });
}

async function main() {
  const args = process.argv.slice(2);
  if (args.some(arg => !['--dry-run', '--apply'].includes(arg)) || args.includes('--dry-run') && args.includes('--apply')) {
    throw new Error('Use --dry-run (default) or --apply.');
  }
  const readText = file => fs.readFileSync(path.resolve(process.cwd(), file), 'utf8');
  const plan = JSON.parse(readText('planning/backlog.json'));
  validatePlan(plan, readText);
  if (!args.includes('--apply')) {
    console.log(JSON.stringify({dry_run: true, repository: plan.repository, labels: plan.labels.length, milestones: plan.milestones.length, issues: plan.issues.map(task => ({id: task.id, owner_role: task.owner_role, depends_on: task.depends_on})), external_writes: 0}, null, 2));
    return;
  }
  const repository = process.env.GITHUB_REPOSITORY;
  const branch = process.env.GITHUB_REF_NAME;
  if (repository !== plan.repository) throw new Error('GITHUB_REPOSITORY must match the reviewed backlog destination.');
  const api = githubApi(repository, process.env.GITHUB_TOKEN);
  let report;
  try { report = await syncPlan({plan, readText, api, repository, branch, sourceCommit: process.env.GITHUB_SHA}); }
  catch (error) {
    report = error.report || {repository, branch, complete: false, error: error.message};
    process.exitCode = 1;
  }
  fs.mkdirSync('planning', {recursive: true});
  fs.writeFileSync('planning/published.json', `${JSON.stringify(report, null, 2)}\n`);
  try { await writeReport(api, report, branch); }
  catch (error) {
    report.warnings = [...(report.warnings || []), `Publication report could not be committed: ${error.message}`];
    process.exitCode = 1;
  }
  console.log(JSON.stringify(report, null, 2));
  if (process.env.GITHUB_STEP_SUMMARY) {
    fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY, `## Sticker planning publication\n\n${report.complete ? 'Task publication completed.' : 'Publication incomplete; inspect the error.'}\n\n${(report.issues || []).map(issue => `- [${issue.id}](${issue.url})`).join('\n')}\n\n${(report.warnings || []).join('\n')}\n`);
  }
}

module.exports = {validatePlan, replaceManaged, syncPlan, writeReport, githubApi};
if (require.main === module) main().catch(error => {console.error(error.message); process.exitCode = 1;});
