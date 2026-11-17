#!/usr/bin/env python3
"""Synchronize only the approved production-deploy wording in Sauna checkouts."""
from __future__ import annotations

import argparse
import difflib
import os
from pathlib import Path
import re
import tempfile
import tomllib

import sync_workaround_policy as common

ROOT = Path(__file__).resolve().parents[1]
CODING = Path('.codex/agents/coding.toml')
OLD_APPROVAL = 'Domain-wide delegation・組織全体の権限・課金リソース・本番デプロイは明示承認を得る。'
NEW_APPROVAL = ('Domain-wide delegation・組織全体の権限・課金リソースは明示承認を得る。'
                '本番デプロイ自体は都度の明示承認を求めず実行してよい。既存の認証・権限設定、CI・レビュー条件は維持する。')
OLD_ENVIRONMENTS = 'Environmentsは開発・検証・本番の承認境界を分ける。'
NEW_ENVIRONMENTS = 'Environmentsは開発・検証・本番を分離する。'
OLD_INFRA = 'apply・本番デプロイ・課金リソース・広いIAM付与は明示承認まで実行しない。'
NEW_INFRA = 'apply・課金リソース・広いIAM付与は明示承認まで実行しない。本番デプロイ自体は都度確認を求めない。'
OLD_CODING = 'Do not deploy production, create billed resources, expand permissions, or merge your own PR without explicit authorization.'
NEW_CODING = ('Do not create billed resources, expand permissions, or merge your own PR without explicit authorization.\n'
              'Production deploys do not require separate user confirmation; preserve existing authentication, authorization, CI, and review requirements.')
STAMP = '本番デプロイ方針の適用元: '


def committed_text(source: Path, sha: str, filename: str) -> str:
    entry = common.git(source, 'ls-tree', sha, '--', filename)
    if not entry.startswith(('100644 ', '100755 ')):
        raise ValueError('Source deployment policy files must be regular tracked files')
    return common.git(source, 'show', f'{sha}:{filename}').replace('\r\n', '\n')


def instructions(text: str) -> str:
    try:
        value = tomllib.loads(text)['developer_instructions']
    except (tomllib.TOMLDecodeError, KeyError) as error:
        raise ValueError('Unknown coding agent instruction format') from error
    if not isinstance(value, str):
        raise ValueError('Coding agent instructions must be text')
    return value


def verify_source(source: Path, sha: str) -> None:
    common.source_files(source, sha)
    agents = committed_text(source, sha, 'AGENTS.md')
    coding = instructions(committed_text(source, sha, CODING.as_posix()))
    initializer = committed_text(source, sha, 'bootstrap/initialize_repositories.py')
    if (NEW_APPROVAL not in agents or NEW_ENVIRONMENTS not in agents or NEW_CODING not in coding or NEW_INFRA not in initializer
            or OLD_APPROVAL in agents or OLD_ENVIRONMENTS in agents or OLD_CODING in coding or OLD_INFRA in initializer):
        raise ValueError('Merged source does not contain the approved production-deploy policy')


def replace_known(text: str, old: str, new: str, label: str) -> str:
    newline = '\r\n' if '\r\n' in text else '\n'
    old, new = old.replace('\n', newline), new.replace('\n', newline)
    if text.count(old) == 1 and text.count(new) == 0:
        return text.replace(old, new, 1)
    if text.count(old) == 0 and text.count(new) == 1:
        return text
    raise ValueError(f'Unknown or duplicate {label} wording; review it before synchronizing')


def stamp(text: str, sha: str) -> str:
    newline = '\r\n' if '\r\n' in text else '\n'
    line = STAMP + f'`sauna-studio/.github@{sha}`。'
    existing = list(re.finditer(r'^' + re.escape(STAMP) + r'`sauna-studio/\.github@[0-9a-f]{40}`。(?:\r?\n|$)', text, re.M))
    if STAMP in text:
        if len(existing) != 1 or text.count(STAMP) != 1:
            raise ValueError('Unknown or duplicate deployment policy source marker')
        item = existing[0]
        return text[:item.start()] + line + newline + text[item.end():]
    separator = '' if text.endswith(newline * 2) else newline if text.endswith(newline) else newline * 2
    return text + separator + line + newline


def updates(source: Path, target: Path, sha: str) -> dict[Path, tuple[bytes, bytes]]:
    verify_source(source, sha)
    repo = common.validate_target(target)
    agents = common.safe_path(target, Path('AGENTS.md'))
    if not agents.exists():
        raise ValueError('Existing AGENTS.md is required')
    before = agents.read_bytes()
    text = replace_known(before.decode('utf-8'), OLD_APPROVAL, NEW_APPROVAL, 'production approval')
    text = replace_known(text, OLD_ENVIRONMENTS, NEW_ENVIRONMENTS, 'Environment separation')
    if repo == 'sauna-studio/sauna-infrastructure':
        text = replace_known(text, OLD_INFRA, NEW_INFRA, 'infrastructure approval')
    desired = {agents: (before, stamp(text, sha).encode('utf-8'))}
    coding = common.safe_path(target, CODING)
    if coding.exists():
        before = coding.read_bytes()
        agent_text = before.decode('utf-8')
        expected = replace_known(instructions(agent_text), OLD_CODING, NEW_CODING, 'coding instruction')
        candidate = replace_known(agent_text, OLD_CODING, NEW_CODING, 'coding instruction')
        if instructions(candidate) != expected:
            raise ValueError('Coding policy replacement must only change developer instructions')
        desired[coding] = (before, candidate.encode('utf-8'))
    elif repo not in {'sauna-studio/postgres-nio', 'sauna-studio/SwiftCBOR'}:
        raise ValueError('Existing coding agent instructions are required')
    if repo == 'sauna-studio/sauna-infrastructure':
        readme = common.safe_path(target, Path('README.md'))
        if readme.exists():
            before = readme.read_bytes()
            desired[readme] = (before, replace_known(before.decode('utf-8'), OLD_INFRA, NEW_INFRA, 'infrastructure README approval').encode('utf-8'))
    changes = {path: value for path, value in desired.items() if value[0] != value[1]}
    dirty = set()
    for args in [('diff', '--no-ext-diff', '--name-only', '-z'), ('diff', '--no-ext-diff', '--cached', '--name-only', '-z'),
                 ('ls-files', '--others', '--exclude-standard', '-z')]:
        dirty.update(name for name in common.git(target, *args).split('\0') if name)
    managed = {path.relative_to(target).as_posix() for path in desired}
    if dirty and (changes or dirty - managed):
        raise ValueError('Target has local changes; use a clean checkout')
    return changes


def sync(source: Path, target: Path, sha: str, *, write: bool = False, check: bool = False) -> bool:
    changes = updates(source, target, sha)
    if write:
        for path, (before, _) in changes.items():
            common.safe_path(target, path.relative_to(target))
            if path.read_bytes() != before:
                raise ValueError('Target policy changed during synchronization')
    for path, (before, value) in changes.items():
        if not check:
            print(''.join(difflib.unified_diff(before.decode('utf-8').splitlines(True), value.decode('utf-8').splitlines(True),
                                              fromfile=str(path.relative_to(target)), tofile=str(path.relative_to(target)))), end='')
        if write:
            common.safe_path(target, path.relative_to(target))
            fd, temporary = tempfile.mkstemp(prefix='.deploy-policy-', dir=path.parent)
            try:
                with os.fdopen(fd, 'wb') as output:
                    output.write(value)
                os.chmod(temporary, path.stat().st_mode & 0o777)
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
    args = parser.parse_args()
    try:
        changed = sync(ROOT, args.target.absolute(), args.source_commit, write=args.write, check=args.check)
    except (ValueError, OSError, UnicodeError) as error:
        parser.exit(2, f'{error}\n')
    return int(args.check and changed)


if __name__ == '__main__':
    raise SystemExit(main())
