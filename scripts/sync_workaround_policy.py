#!/usr/bin/env python3
"""Copy only the merged workaround rule and form into a clean Sauna checkout."""
from __future__ import annotations

import argparse
import difflib
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
HEADING = '## ワークアラウンドの追跡'
FORM = Path('.github/ISSUE_TEMPLATE/workaround.yml')
CONSUMERS = {
    'sauna-api', 'sauna-web', 'sauna-admin-web', 'sauna-app', 'sauna-admin-app',
    'sauna-automation', 'sauna-docs', 'sauna-infrastructure', 'postgres-nio', 'SwiftCBOR',
}


def git(root: Path, *args: str) -> str:
    result = subprocess.run(['git', '-C', str(root), *args], capture_output=True)
    if result.returncode:
        raise ValueError('Required Git state is unavailable; fetch the default branch first')
    return result.stdout.decode('utf-8')


def github_repo(root: Path) -> str:
    remote = git(root, 'remote', 'get-url', 'origin').strip()
    match = re.fullmatch(r'(?:https://github\.com/|git@github\.com:)(sauna-studio/[^/]+?)(?:\.git)?', remote)
    if not match:
        raise ValueError('Expected a Sauna Studio GitHub origin')
    return match[1]


def section(text: str) -> tuple[int, int]:
    headings = list(re.finditer(r'^' + re.escape(HEADING) + r'\r?$', text, re.M))
    if len(headings) != 1:
        raise ValueError('Expected exactly one workaround tracking section')
    start = headings[0].start()
    next_heading = re.search(r'^## ', text[headings[0].end():], re.M)
    end = headings[0].end() + next_heading.start() if next_heading else len(text)
    return start, end


def source_files(source: Path, sha: str) -> tuple[str, bytes]:
    if not re.fullmatch(r'[0-9a-f]{40}', sha):
        raise ValueError('Use a full lowercase source commit SHA')
    if github_repo(source) != 'sauna-studio/.github':
        raise ValueError('Source must be sauna-studio/.github')
    # A fetchable branch object is not evidence that the policy is merged.
    git(source, 'merge-base', '--is-ancestor', sha, 'refs/remotes/origin/main')
    contents = []
    for filename in ['AGENTS.md', FORM.as_posix()]:
        entry = git(source, 'ls-tree', sha, '--', filename)
        if not entry.startswith(('100644 ', '100755 ')):
            raise ValueError('Source policy and form must be regular tracked files')
        contents.append(git(source, 'show', f'{sha}:{filename}'))
    start, end = section(contents[0])
    rule = contents[0][start:end].rstrip('\r\n')
    stamp = f'ワークアラウンド追跡規則の適用元: `sauna-studio/.github@{sha}`。'
    return rule + '\n\n' + stamp + '\n\n', contents[1].encode('utf-8')


def safe_path(root: Path, relative: Path) -> Path:
    path = root
    for component in relative.parts:
        path = path / component
        if path.is_symlink():
            raise ValueError(f'Refusing symlink policy path: {relative}')
    if path.exists() and not path.is_file():
        raise ValueError(f'Expected a regular policy file: {relative}')
    return path


def updates(source: Path, target: Path, sha: str, *, issues_disabled: bool = False,
            allow_new_agents: bool = False) -> dict[Path, tuple[bytes | None, bytes]]:
    if target.is_symlink() or Path(git(target, 'rev-parse', '--show-toplevel').strip()).resolve() != target.resolve():
        raise ValueError('Target must be the checkout root, not a symlink or subdirectory')
    target_repo = github_repo(target)
    if target_repo not in {f'sauna-studio/{name}' for name in CONSUMERS}:
        raise ValueError('Target is not an approved Sauna consumer repository')
    if target_repo == 'sauna-studio/postgres-nio':
        branch = git(target, 'branch', '--show-current').strip()
        if not branch or branch in {'main', 'sauna-1.33.2'}:
            raise ValueError('Use a feature branch based on origin/sauna-1.33.2 for postgres-nio')
        try:
            git(target, 'merge-base', '--is-ancestor', 'refs/remotes/origin/sauna-1.33.2', 'HEAD')
        except ValueError as error:
            raise ValueError('PostgresNIO target must include the fetched origin/sauna-1.33.2 history') from error
    rule, form = source_files(source, sha)
    agents = safe_path(target, Path('AGENTS.md'))
    if agents.exists():
        original_bytes = agents.read_bytes()
        original = original_bytes.decode('utf-8')
        start, end = section(original)
        replacement = rule.rstrip('\r\n') + '\n' if end == len(original) else rule
        desired = (original[:start] + replacement + original[end:]).encode('utf-8')
    elif allow_new_agents:
        original_bytes = None
        if not issues_disabled or github_repo(target) not in {'sauna-studio/postgres-nio', 'sauna-studio/SwiftCBOR'}:
            raise ValueError('New fork instructions require an approved Issues-disabled fork')
        desired = ('# Sauna Studio fork instructions\n\n'
                   '上流の構成・ライセンス・検証手順を保持する。\n\n' + rule.rstrip('\r\n') + '\n').encode('utf-8')
    else:
        raise ValueError('Missing AGENTS.md; new fork instructions require --allow-new-agents')
    desired_files = {agents: (original_bytes, desired)}
    if not issues_disabled:
        form_path = safe_path(target, FORM)
        desired_files[form_path] = (form_path.read_bytes() if form_path.exists() else None, form)
    changes = {path: values for path, values in desired_files.items() if values[0] != values[1]}
    # A completed rerun is harmless even while its own output is uncommitted.
    dirty = set()
    for args in [('diff', '--no-ext-diff', '--name-only', '-z'), ('diff', '--no-ext-diff', '--cached', '--name-only', '-z'),
                 ('ls-files', '--others', '--exclude-standard', '-z')]:
        dirty.update(name for name in git(target, *args).split('\0') if name)
    managed = {path.relative_to(target).as_posix() for path in desired_files}
    if dirty and (changes or dirty - managed):
        raise ValueError('Target has local changes; use a clean checkout for synchronization')
    return changes


def sync(source: Path, target: Path, sha: str, *, write: bool = False, check: bool = False,
         issues_disabled: bool = False, allow_new_agents: bool = False) -> bool:
    changes = updates(source, target, sha, issues_disabled=issues_disabled,
                      allow_new_agents=allow_new_agents)
    if write:
        for path, (before, _) in changes.items():
            safe_path(target, path.relative_to(target))
            if (path.read_bytes() if path.exists() else None) != before:
                raise ValueError('Target policy changed during synchronization')
    for path, (before, value) in changes.items():
        before = before or b''
        if not check:
            print(''.join(difflib.unified_diff(before.decode('utf-8').splitlines(True),
                                              value.decode('utf-8').splitlines(True),
                                              fromfile=str(path.relative_to(target)),
                                              tofile=str(path.relative_to(target)))), end='')
        if write:
            safe_path(target, path.relative_to(target))
            path.parent.mkdir(parents=True, exist_ok=True)
            mode = path.stat().st_mode & 0o777 if path.exists() else 0o644
            fd, temporary = tempfile.mkstemp(prefix='.workaround-', dir=path.parent)
            try:
                with os.fdopen(fd, 'wb') as output:
                    output.write(value)
                os.chmod(temporary, mode)
                os.replace(temporary, path)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
    return bool(changes)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target', type=Path)
    parser.add_argument('--source-commit', required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--write', action='store_true')
    mode.add_argument('--check', action='store_true')
    parser.add_argument('--issues-disabled', action='store_true', help='Do not add an unusable Issue Form to a fork')
    parser.add_argument('--allow-new-agents', action='store_true', help='Create minimal fork instructions when AGENTS.md is absent')
    args = parser.parse_args()
    try:
        changed = sync(ROOT, args.target.absolute(), args.source_commit, write=args.write,
                       check=args.check, issues_disabled=args.issues_disabled,
                       allow_new_agents=args.allow_new_agents)
    except (ValueError, OSError, UnicodeError) as error:
        parser.exit(2, f'{error}\n')
    return int(args.check and changed)


if __name__ == '__main__':
    raise SystemExit(main())
