#!/usr/bin/env python3
"""Explicit, resumable GitHub bootstrap. Reads gh's existing auth; never reads tokens.

Run --stage project|issues|relationships|settings. Repo contents always use PRs.
Only allowlisted Sauna Studio repositories may be mutated.
"""
import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORG = 'sauna-studio'
REPOS = ['.github', 'sauna-api', 'sauna-app', 'sauna-web', 'sauna-admin-app',
         'sauna-admin-web', 'sauna-infrastructure', 'sauna-automation', 'sauna-docs']
STATE_PATH = ROOT / 'docs/provisioning-results.json'


def gh(*args, data=None):
    cmd = ['gh', *args]
    if data is not None:
        cmd += ['--input', '-']
    r = subprocess.run(cmd, input=json.dumps(data) if data is not None else None,
                       text=True, capture_output=True)
    if r.returncode:
        raise RuntimeError(f'{" ".join(args[:4])}: {r.stderr.strip()}')
    return json.loads(r.stdout) if r.stdout.strip() else None


def api(path, method='GET', data=None):
    return gh('api', path, '--method', method, data=data)


def save(state):
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n')


def pages(path):
    result = []
    for page in range(1, 101):
        part = api(f'{path}{"&" if "?" in path else "?"}per_page=100&page={page}')
        result.extend(part)
        if len(part) < 100:
            return result
    raise RuntimeError('Pagination limit exceeded')


def project(state):
    projects = gh('project', 'list', '--owner', ORG, '--format', 'json', '--limit', '100')['projects']
    matches = [p for p in projects if p['title'] == 'Sauna Studio — MVP']
    if len(matches) > 1:
        raise RuntimeError('Ambiguous existing project')
    p = matches[0] if matches else gh('project', 'create', '--owner', ORG, '--title', 'Sauna Studio — MVP', '--format', 'json')
    n = str(p['number'])
    state['project'] = {k: p[k] for k in ('id', 'number', 'url')}
    save(state)
    fields = gh('project', 'field-list', n, '--owner', ORG, '--format', 'json', '--limit', '100')['fields']
    for name, options in [('Priority', 'P0,P1,P2'), ('Phase', 'Foundation,MVP,Integration'),
                          ('Area', 'github,api,apple,web,infra,automation,docs')]:
        if name not in [f['name'] for f in fields]:
            gh('project', 'field-create', n, '--owner', ORG, '--name', name, '--data-type', 'SINGLE_SELECT', '--single-select-options', options, '--format', 'json')
    for repo in REPOS:
        gh('project', 'link', n, '--owner', ORG, '--repo', f'{ORG}/{repo}')
    print(p['url'], flush=True)


def issue_body(item, state):
    lines = [f'<!-- sauna-backlog:{item["key"]} -->', '', item['body'], '', '## 受け入れ条件', '']
    lines += [f'- [ ] {a}' for a in item['acceptance']]
    lines += ['', '## 依存関係', '']
    for dep in item['dependencies']:
        lines.append(f'- Blocked by {state.get("issues", {}).get(dep, {}).get("url", dep)}')
    if not item['dependencies']:
        lines.append('- なし。担当実装は関連ADRと現状を確認して開始する。')
    lines += ['', '## 実装・検証', '', '- Coding Agentと独立Review Agentを並行起動する。',
              '- 認証・決済・予約競合・個人情報・施設権限を変更する場合はSecurity Review Agentも起動する。',
              '- 実ビルド/テスト/MCPの結果、未検証項目、レビュー指摘と対応をPRに記録する。',
              '- バグは重複検索後にIssue化し、回帰テストを追加して再レビューする。', '',
              '出典: 提示要件から再構成。共有会話の元50件との照合は未実施。']
    return '\n'.join(lines) + '\n'


def validate_backlog(backlog):
    keys = [i['key'] for i in backlog]
    if len(keys) != len(set(keys)):
        raise ValueError('Duplicate backlog keys')
    indexed = {i['key']: i for i in backlog}
    for i in backlog:
        if i['repo'] not in REPOS or len(i['acceptance']) < 2:
            raise ValueError('Invalid repo or acceptance criteria: ' + i['key'])
        for dep in i['dependencies'] + ([i['parent']] if i.get('parent') else []):
            if dep not in indexed or dep == i['key']:
                raise ValueError('Invalid relationship: ' + i['key'])
    for field in ('dependencies', 'parent'):
        done, active = set(), set()
        def visit(key):
            if key in active:
                raise ValueError('Cycle in ' + field + ': ' + key)
            if key in done:
                return
            active.add(key)
            value = indexed[key].get(field, [])
            for dep in ([value] if isinstance(value, str) else value):
                visit(dep)
            active.remove(key)
            done.add(key)
        for key in keys:
            visit(key)


def issues(state):
    backlog = json.loads((ROOT / 'bootstrap/backlog.json').read_text())['issues']
    validate_backlog(backlog)
    created = set()
    state.setdefault('issues', {})
    existing = {repo: pages(f'repos/{ORG}/{repo}/issues?state=all') for repo in REPOS}
    for item in backlog:
        repo = item['repo']
        if repo not in REPOS:
            raise ValueError(repo)
        marker = f'<!-- sauna-backlog:{item["key"]} -->'
        matches = [i for i in existing[repo] if not i.get('pull_request') and
                   (marker in (i.get('body') or '') or i['title'].startswith(f'[{item["key"]}]'))]
        if len(matches) > 1:
            raise RuntimeError(f'Duplicate key: {item["key"]}')
        if matches and marker not in (matches[0].get('body') or ''):
            raise RuntimeError('Title-only match requires manual reconciliation: ' + item['key'])
        if not matches:
            created.add(item['key'])
        i = matches[0] if matches else api(f'repos/{ORG}/{repo}/issues', 'POST', {
            'title': f'[{item["key"]}] {item["title"]}', 'body': issue_body(item, state)})
        state['issues'][item['key']] = {'repo': repo, 'number': i['number'], 'id': i['id'], 'url': i['html_url'], 'node_id': i['node_id']}
        save(state)
        print(item['key'], i['html_url'], flush=True)
    # Existing bodies (including human edits) are never overwritten on reruns.
    for item in backlog:
        if item['key'] not in created:
            continue
        i = state['issues'][item['key']]
        api(f'repos/{ORG}/{i["repo"]}/issues/{i["number"]}', 'PATCH', {'body': issue_body(item, state)})


def relationships(state):
    backlog = json.loads((ROOT / 'bootstrap/backlog.json').read_text())['issues']
    validate_backlog(backlog)
    for item in backlog:
        i = state['issues'][item['key']]
        expected = f'https://github.com/{ORG}/{item["repo"]}/issues/{i["number"]}'
        if i['repo'] != item['repo'] or i['url'] != expected:
            raise ValueError('Unsafe issue state: ' + item['key'])
    n = str(state['project']['number'])
    fields = gh('project', 'field-list', n, '--owner', ORG, '--format', 'json', '--limit', '100')['fields']
    for item in backlog:
        i = state['issues'][item['key']]
        path = f'repos/{ORG}/{i["repo"]}/issues/{i["number"]}'
        for dep in item['dependencies']:
            target = state['issues'][dep]
            known = pages(path + '/dependencies/blocked_by')
            if target['id'] not in [d['id'] for d in known]:
                api(path + '/dependencies/blocked_by', 'POST', {'issue_id': target['id']})
        if item.get('parent'):
            p = state['issues'][item['parent']]
            parent_path = f'repos/{ORG}/{p["repo"]}/issues/{p["number"]}/sub_issues'
            if i['id'] not in [s['id'] for s in pages(parent_path)]:
                api(parent_path, 'POST', {'sub_issue_id': i['id']})
        pi = gh('project', 'item-add', n, '--owner', ORG, '--url', i['url'], '--format', 'json')
        for field_name, value in [('Phase', item['phase']), ('Area', item['area']), ('Priority', 'P1' if item['key'].startswith('MVP') else 'P0')]:
            f = next(f for f in fields if f['name'] == field_name)
            opt = next(o for o in f['options'] if o['name'] == value)
            gh('project', 'item-edit', '--id', pi['id'], '--project-id', state['project']['id'], '--field-id', f['id'], '--single-select-option-id', opt['id'])
        print('linked', item['key'], flush=True)
    state['relationships_complete'] = True
    save(state)


def settings(state):
    state.setdefault('settings', {})
    for repo in REPOS:
        path = f'repos/{ORG}/{repo}'
        record = state['settings'].setdefault(repo, {})
        api(path, 'PATCH', {'has_issues': True, 'has_wiki': True, 'delete_branch_on_merge': True,
                            'allow_squash_merge': True, 'allow_merge_commit': False, 'allow_rebase_merge': False,
                            'security_and_analysis': {'secret_scanning': {'status': 'enabled'},
                            'secret_scanning_push_protection': {'status': 'enabled'}}})
        for endpoint in ['vulnerability-alerts', 'automated-security-fixes', 'private-vulnerability-reporting']:
            try:
                api(path + '/' + endpoint, 'PUT')
                record[endpoint] = 'enabled'
            except RuntimeError as e:
                record[endpoint] = str(e)
        # Empty environments only: no credentials, deploys, IAM or billing resources.
        for name in ['development', 'staging', 'production']:
            api(path + '/environments/' + name, 'PUT', {'deployment_branch_policy': {'protected_branches': True, 'custom_branch_policies': False}})
        record['security_and_analysis'] = api(path)['security_and_analysis']
        save(state)
        print('settings', repo, flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage', required=True, choices=['project', 'issues', 'relationships', 'settings'])
    args = p.parse_args()
    state = json.loads(STATE_PATH.read_text()) if STATE_PATH.exists() else {'organization': ORG}
    globals()[args.stage](state)


if __name__ == '__main__':
    main()
