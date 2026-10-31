#!/usr/bin/env python3
"""Plan/apply native issue graph and Project metadata in bounded serial batches.

Reads actual Issue.projectItems (including archived items), avoiding the eventually
consistent Project item-list index. No resources outside the validated allowlist.
"""
import argparse
import json
from pathlib import Path
import provision as p

ROOT = Path(__file__).resolve().parents[1]


def graphql(query, variables=None):
    result = p.gh('api', 'graphql', data={'query': query, 'variables': variables or {}})
    if result.get('errors'):
        raise RuntimeError(result['errors'])
    return result['data']


def snapshot(ids):
    query = '''query($ids:[ID!]!){nodes(ids:$ids){... on Issue{id url state parent{id}
      blockedBy(first:100){nodes{id} pageInfo{hasNextPage}}
      projectItems(first:100,includeArchived:true){nodes{id isArchived project{id}} pageInfo{hasNextPage}}}}}'''
    nodes = graphql(query, {'ids': ids})['nodes']
    if any(n is None for n in nodes):
        raise ValueError('Missing issue node')
    for n in nodes:
        if n['blockedBy']['pageInfo']['hasNextPage'] or n['projectItems']['pageInfo']['hasNextPage']:
            raise ValueError('Connection exceeds reviewed bootstrap bound')
    return {n['id']: n for n in nodes}


def execute(operations):
    for start in range(0, len(operations), 20):
        batch = operations[start:start + 20]
        query = 'mutation{' + ' '.join(f'm{idx}:{op}' for idx, op in enumerate(batch)) + '}'
        graphql(query)
        print(f'Applied {min(start+20,len(operations))}/{len(operations)} operations', flush=True)


def project_item(node, pid):
    matches = [i for i in node['projectItems']['nodes'] if i['project']['id'] == pid]
    if any(i['isArchived'] for i in matches):
        raise ValueError('Refusing to silently unarchive an existing item')
    if len(matches) > 1:
        raise ValueError('Ambiguous Project membership')
    return matches[0] if matches else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    backlog = json.loads((ROOT / 'bootstrap/backlog.json').read_text())['issues']
    p.validate_backlog(backlog)
    state = json.loads(p.STATE_PATH.read_text())
    for item in backlog:
        issue = state['issues'][item['key']]
        expected = f'https://github.com/{p.ORG}/{item["repo"]}/issues/{issue["number"]}'
        if issue['repo'] != item['repo'] or issue['url'] != expected:
            raise ValueError('Unsafe issue provenance')
    actual_project = p.gh('project', 'view', str(state['project']['number']), '--owner', p.ORG, '--format', 'json')
    if actual_project['id'] != state['project']['id'] or actual_project['url'] != state['project']['url']:
        raise ValueError('Unsafe Project provenance')
    indexed = state['issues']
    nodes = snapshot([indexed[i['key']]['node_id'] for i in backlog])
    operations = []
    for item in backlog:
        current = nodes[indexed[item['key']]['node_id']]
        if current['url'] != indexed[item['key']]['url']:
            raise ValueError('Node ID and validated URL disagree')
        known = {i['id'] for i in current['blockedBy']['nodes']}
        for dependency in item['dependencies']:
            target = indexed[dependency]['node_id']
            if target not in known:
                operations.append('addBlockedBy(input:{issueId:%s,blockingIssueId:%s}){clientMutationId}' % (json.dumps(current['id']), json.dumps(target)))
        if item.get('parent'):
            target = indexed[item['parent']]['node_id']
            if current['parent'] and current['parent']['id'] != target:
                raise ValueError('Refusing to replace an existing parent')
            if not current['parent']:
                operations.append('addSubIssue(input:{issueId:%s,subIssueId:%s}){clientMutationId}' % (json.dumps(target), json.dumps(current['id'])))
    print(f'Planning issues={len(backlog)}; missing native edges={len(operations)}', flush=True)
    if not args.apply:
        return
    execute(operations)
    pid = state['project']['id']
    # Parent auto-add workflow may already have added children. Read by issue node.
    nodes = snapshot(list(nodes))
    for item in backlog:
        node = nodes[indexed[item['key']]['node_id']]
        if project_item(node, pid) is None:
            graphql('mutation($p:ID!,$i:ID!){addProjectV2ItemById(input:{projectId:$p,contentId:$i}){item{id}}}', {'p': pid, 'i': node['id']})
    nodes = snapshot(list(nodes))
    fields = p.gh('project', 'field-list', str(state['project']['number']), '--owner', p.ORG, '--format', 'json', '--limit', '100')['fields']
    operations = []
    for item in backlog:
        node = nodes[indexed[item['key']]['node_id']]
        pi = project_item(node, pid)
        if pi is None:
            raise ValueError('Project membership has not materialized; safely rerun')
        values = [('Phase', item['phase']), ('Area', item['area']), ('Priority', 'P1' if item['key'].startswith('MVP') else 'P0'),
                  ('Status', 'Done' if node['state'] == 'CLOSED' else 'In Progress' if item['key'] == 'MVP-001' else 'Todo')]
        for field, value in values:
            f = next(f for f in fields if f['name'] == field)
            option = next(o['id'] for o in f['options'] if o['name'] == value)
            inp = 'projectId:%s,itemId:%s,fieldId:%s,value:{singleSelectOptionId:%s}' % tuple(json.dumps(x) for x in [pid, pi['id'], f['id'], option])
            operations.append('updateProjectV2ItemFieldValue(input:{%s}){clientMutationId}' % inp)
    execute(operations)
    actual = snapshot(list(nodes))
    for item in backlog:
        node = actual[indexed[item['key']]['node_id']]
        expected = {indexed[d]['node_id'] for d in item['dependencies']}
        if not expected.issubset({d['id'] for d in node['blockedBy']['nodes']}):
            raise ValueError('Missing blocking edges: ' + item['key'])
        if item.get('parent') and (not node['parent'] or node['parent']['id'] != indexed[item['parent']]['node_id']):
            raise ValueError('Missing parent: ' + item['key'])
        if project_item(node, pid) is None:
            raise ValueError('Missing project item: ' + item['key'])
    state['relationships_complete'] = True
    state['graph_verified'] = {'planning_issues': len(backlog), 'blocking_edges': sum(len(i['dependencies']) for i in backlog),
                               'parent_edges': sum(bool(i.get('parent')) for i in backlog)}
    p.save(state)
    print(json.dumps(state['graph_verified']), flush=True)


if __name__ == '__main__':
    main()
