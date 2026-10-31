#!/usr/bin/env python3
"""Prepare and optionally publish eight repository foundations through PRs only.

Requires a reviewed, pushed .github commit SHA and the user's public-repo authorization. Existing local directories,
unexpected remote files, pre-existing work branches or PRs fail before writes.
Never merges, deploys, reads secrets, edits GoogleChatApp, or force-pushes.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORG = "sauna-studio"
WORKSPACE = ROOT.parent / "sauna-studio-workspace"
BRANCH = "codex/repository-foundation"
STATE_PATH = ROOT / "docs/repository-results.json"
SCOPES = {
    "sauna-api": (
        "予約・決済・在庫・設備・シフト・チャットの業務API。Swift 6 / Hummingbird / PostgreSQL 18 / PostgresNIO / Atlas / OpenAPIを採用する。",
        "施設IDによる境界をAPIとDBで検証する。予約・決済・シフトの正本はPostgreSQL。認証・決済・競合制御・個人情報・施設権限を実装する際はSecurity Review Agentを必須とする。",
        "実装後はswift build / swift test、PostgreSQL 18統合テスト、OpenAPI整合性とAtlas migrationを検証する。",
    ),
    "sauna-app": (
        "利用者向けSwiftUI iOS・iPadOSアプリ。iOS・iPadOS 27.2以上。予約・決済・チャットのUIを提供する。",
        "Sauna APIを正本とし、Passkeyでログインする。TweetbotのVintage・Pumpkinをデザイン参照にする。利用条件の未確認な資産はコピーしない。",
        "実装後は対象Xcodeでbuild/testを実行し、Xcode MCP・Simulatorで主要導線を確認する。古いOS向けの互換分岐は追加しない。",
    ),
    "sauna-web": (
        "利用者向けSvelteKit / TypeScript Web。予約・決済・チャットのUIを提供する。",
        "Sauna APIを正本とし、WebAuthn / Passkeyでログインする。最新安定版ブラウザを対象にVintage・Pumpkinを参照する。",
        "実装後はnpm ci / npm run check / npm test -- --run / npm run buildとPlaywright検証を実行する。",
    ),
    "sauna-admin-app": (
        "管理者・スタッフ向けSwiftUI iOS・iPadOSアプリ。iOS・iPadOS 27.2以上。予約・設備・在庫・シフト管理を扱う。",
        "社員はGoogle Workspace組織アカウントとの紐付けを必須とするが、SaunaログインはPasskeyのみ。施設権限の最終判断はAPIが行う。",
        "実装後は対象Xcodeでbuild/testとSimulator動作検証を行い、所属喪失・施設権限不足時の拒否を検証する。",
    ),
    "sauna-admin-web": (
        "管理者・スタッフ向けSvelteKit / TypeScript Web。予約・設備・在庫・シフト管理を扱う。",
        "社員はGoogle Workspace組織アカウントとの紐付けを必須とするが、SaunaログインはPasskeyのみ。APIで所属と施設権限を検証する。",
        "実装後はnpm ci / npm run check / npm test -- --run / npm run build、Playwrightで権限別操作を検証する。",
    ),
    "sauna-infrastructure": (
        "Terraform / Google Cloud Run / Cloud SQL PostgreSQL 18 / OpenTelemetry / Dockerの基盤コード。",
        "業務データの正本はSauna APIとPostgreSQL。認証情報をTerraform state・plan・ログ・リポジトリに公開しない。",
        "実装後はterraform fmt -check -recursive / init -backend=false / validateを実行する。apply・本番デプロイ・課金リソース・広いIAM付与は明示承認まで実行しない。",
    ),
    "sauna-automation": (
        "Google Chat Bot、Google Workspace API連携、AIエージェント向けsauna-mcp。",
        "Google Cloud SwiftクライアントとWorkspace APIの対応範囲を区別する。Sauna APIが業務データの正本。zunda-pixel/GoogleChatAppおよびそのProjectは独立しており変更しない。",
        "実装言語は対応IssueとADRで確定する。実装後はBot署名・権限・冪等性・Workspace scope・MCP認可のテストを行う。Domain-wide delegationは無断で有効化しない。",
    ),
    "sauna-docs": (
        "アーキテクチャ・ADR・GitHub Wiki索引・依存関係を持つ横断バックログ。",
        ".githubを共通規則の正本、各業務repoを実コードの正本として参照する。設計変更は背景・決定・代替案・影響をADRへ記録する。",
        "Markdownリンク・ADR整合性・backlogのキーと依存関係を検証する。Wiki反映前にGitHub側の実際の内容を確認する。",
    ),
}


def run(args: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"Command failed ({args[0]} {args[1]}): {result.stderr.strip()}")
    return result.stdout.strip()


def gh(*args: str) -> object:
    output = run(["gh", *args])
    return json.loads(output) if output else None


def preflight(repos: list[str], sha: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("--workflow-ref must be an immutable 40-character commit SHA")
    source_commit = gh("api", f"repos/{ORG}/.github/commits/{sha}")
    if source_commit["sha"] != sha:
        raise RuntimeError("Common policy commit SHA mismatch")
    for path in ["AGENTS.md", ".github/workflows/reusable-repository.yml"]:
        gh("api", f"repos/{ORG}/.github/contents/{path}?ref={sha}")
    policy_sources = [ROOT / name for name in ["AGENTS.md", "CONTRIBUTING.md", "SECURITY.md", "LICENSE", ".github/CODEOWNERS", ".github/pull_request_template.md"]]
    policy_sources += list((ROOT / ".github/ISSUE_TEMPLATE").glob("*.yml"))
    policy_sources += list((ROOT / ".codex").rglob("*.toml"))
    for source in policy_sources:
        committed = run(["git", "show", f"{sha}:{source.relative_to(ROOT)}"], ROOT)
        if source.read_text().strip() != committed:
            raise RuntimeError(f"Local policy differs from pinned commit: {source.relative_to(ROOT)}")
    for repo in repos:
        if (WORKSPACE / repo).exists():
            raise RuntimeError(f"Refusing to overwrite existing local path: {WORKSPACE / repo}")
        info = gh("repo", "view", f"{ORG}/{repo}", "--json", "nameWithOwner,defaultBranchRef,viewerPermission,isPrivate")
        if info["nameWithOwner"] != f"{ORG}/{repo}" or info["defaultBranchRef"]["name"] != "main":
            raise RuntimeError(f"Unexpected repository identity or default branch: {repo}")
        if info["viewerPermission"] not in {"ADMIN", "MAINTAIN", "WRITE"}:
            raise RuntimeError(f"No repository write permission: {repo}")
        if info["isPrivate"]:
            raise RuntimeError(f"Expected public repository per current explicit user authorization: {repo}")
        tree = gh("api", f"repos/{ORG}/{repo}/git/trees/main?recursive=1")
        if tree.get("truncated"):
            raise RuntimeError(f"Cannot verify truncated repository tree: {repo}")
        files = {entry["path"] for entry in tree["tree"] if entry["type"] == "blob"}
        if files != {"README.md"}:
            raise RuntimeError(f"Repository has existing files beyond expected bootstrap README: {repo}")
        refs = gh("api", f"repos/{ORG}/{repo}/git/matching-refs/heads/{BRANCH}")
        if refs:
            raise RuntimeError(f"Foundation branch already exists: {repo}")
        prs = gh("pr", "list", "--repo", f"{ORG}/{repo}", "--state", "all", "--head", BRANCH, "--json", "url")
        if prs:
            raise RuntimeError(f"Foundation PR already exists: {repo}")


def write_new(destination: Path, text: str) -> None:
    if destination.exists():
        raise RuntimeError(f"Refusing to replace existing file: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text)


def copy_new(source: Path, destination: Path) -> None:
    write_new(destination, source.read_text())


def build_files(repo: str, directory: Path, sha: str) -> None:
    scope, architecture, verification = SCOPES[repo]
    for name in ["CONTRIBUTING.md", "SECURITY.md", "LICENSE"]:
        copy_new(ROOT / name, directory / name)
    copy_new(ROOT / ".github/CODEOWNERS", directory / ".github/CODEOWNERS")
    copy_new(ROOT / ".github/pull_request_template.md", directory / ".github/pull_request_template.md")
    for source in sorted((ROOT / ".github/ISSUE_TEMPLATE").glob("*.yml")):
        copy_new(source, directory / ".github/ISSUE_TEMPLATE" / source.name)
    for source in sorted((ROOT / ".codex").rglob("*.toml")):
        copy_new(source, directory / source.relative_to(ROOT))
    agents = (ROOT / "AGENTS.md").read_text()
    agents += f"\n## {repo} 固有指針\n\n共通規則適用元: `sauna-studio/.github@{sha}`。\n\n{scope}\n\n{architecture}\n\n{verification}\n\n初期CIは共通Repository policy検査のみ。アプリのビルド・テスト・実行を検証済みとは扱わない。実装Issueでmanifest・lockfile・テストを追加し、対応する実コードCIを有効化する。\n"
    write_new(directory / "AGENTS.md", agents)
    readme = directory / "README.md"
    original = readme.read_text()
    addition = f"\n\n## Scope\n\n{scope}\n\n## Architecture\n\n{architecture}\n\n## Verification\n\n{verification}\n\n初期PRは開発基盤のみを追加します。CIはRepository policy検査を実行し、業務機能の実装や動作検証はまだ含みません。\n\n[AGENTS.md](AGENTS.md) と [CONTRIBUTING.md](CONTRIBUTING.md) に従い、Issueの依存関係を満たしてから独立Review Agentを並行起動して実装します。共通規則適用元: [sauna-studio/.github@{sha[:12]}](https://github.com/sauna-studio/.github/tree/{sha})。\n"
    if repo == "sauna-docs":
        addition += "\n設計文書: [Architecture ADR](docs/adr/0001-architecture.md) / [Wiki source](docs/wiki/Home.md) / [Backlog](docs/backlog.md)。\n"
        for category in ["adr", "wiki"]:
            for source in sorted((ROOT / "docs" / category).glob("*.md")):
                copy_new(source, directory / "docs" / category / source.name)
        backlog_index = (ROOT / "docs/backlog.md").read_text().replace("../bootstrap/backlog.json", "backlog.json")
        write_new(directory / "docs/backlog.md", backlog_index)
        copy_new(ROOT / "bootstrap/backlog.json", directory / "docs/backlog.json")
    readme.write_text(original + addition)
    write_new(directory / ".gitignore", """.DS_Store
.env
.env.*
!.env.example
.build/
.swiftpm/
DerivedData/
*.xcuserstate
xcuserdata/
node_modules/
.svelte-kit/
build/
coverage/
.terraform/
*.tfstate
*.tfstate.*
*.tfplan
*.tfvars
!*.tfvars.example
*.p12
*.p8
*.key
""")
    write_new(directory / ".github/dependabot.yml", """version: 2
updates:
  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: weekly
    open-pull-requests-limit: 5
""")
    write_new(directory / ".github/workflows/ci.yml", f"""name: Repository CI
on:
  pull_request:
  push:
    branches: [main, 'codex/**']
  workflow_dispatch:
permissions:
  contents: read
concurrency:
  group: repository-${{{{ github.workflow }}}}-${{{{ github.ref }}}}
  cancel-in-progress: true
jobs:
  policy:
    uses: sauna-studio/.github/.github/workflows/reusable-repository.yml@{sha}
    permissions:
      contents: read
""")


def verify(directory: Path) -> None:
    run(["git", "diff", "--check"], directory)
    # Verify the same structure required by the pinned reusable workflow.
    for filename in ["AGENTS.md", "README.md", ".github/CODEOWNERS", ".github/workflows/ci.yml", ".github/dependabot.yml"]:
        if not (directory / filename).is_file() or not (directory / filename).read_text().strip():
            raise RuntimeError(f"Missing generated policy file: {filename}")
    for source in (directory / ".github").rglob("*.yml"):
        if "pull_request_target" in source.read_text():
            raise RuntimeError("Unexpected privileged workflow trigger")


def publish(repo: str, directory: Path, sha: str, state: dict) -> None:
    run(["git", "clone", f"https://github.com/{ORG}/{repo}.git", str(directory)])
    cloned_files = run(["git", "ls-tree", "--name-only", "-r", "HEAD"], directory).splitlines()
    if cloned_files != ["README.md"] or run(["git", "branch", "--show-current"], directory) != "main":
        raise RuntimeError(f"Repository changed since preflight; refusing to modify: {repo}")
    run(["git", "switch", "-c", BRANCH], directory)
    original = (directory / "README.md").read_text()
    build_files(repo, directory, sha)
    if not (directory / "README.md").read_text().startswith(original):
        raise RuntimeError("Original README was not preserved")
    verify(directory)
    run(["git", "add", "--all"], directory)
    run(["git", "commit", "-m", f"chore: initialize {repo} development foundation"], directory)
    commit = run(["git", "rev-parse", "HEAD"], directory)
    run(["git", "push", "--set-upstream", "origin", BRANCH], directory)
    # Forms deliberately avoid implicit labels; baseline labels are created if missing.
    labels = gh("label", "list", "--repo", f"{ORG}/{repo}", "--limit", "100", "--json", "name")
    names = {label["name"] for label in labels}
    for name, color, description in [("type:task", "1D76DB", "Implementation or foundation task"), ("type:bug", "D73A4A", "Confirmed defect with regression verification")]:
        if name not in names:
            run(["gh", "label", "create", name, "--repo", f"{ORG}/{repo}", "--color", color, "--description", description])
    body = f"""## 変更内容

{SCOPES[repo][0]}

既存READMEを保持して開発方針を追記し、共通AGENTS.mdと固有指針、Codexエージェント5種、Issue Forms、PRテンプレート、CODEOWNERS、Dependabot、最小権限のCIを明示配置します。共通規則・Reusable Workflowは `{ORG}/.github@{sha}` に固定しています。

## 検証結果

- `git diff --check`、必須policyファイルと未信頼PR用triggerの検査: 成功
- 元のREADMEが全文prefixとして保持されていることを検証: 成功
- CI: 共通Repository policy検査のみ。アプリ実コード・ビルド・テストは未配置
- Actions結果はPR作成後に別途確認

## エージェントレビュー

Coding Agentと独立Review Agentが並行稼働し、共通policyと初期化scriptをレビューしました。実行結果の再レビューは作成後に追記します。認証・決済・個人情報・施設権限の実コードはこのPRに含みません。

## 既知の制限

業務機能、デプロイ、課金リソース、Secrets、広範囲の権限付与は含みません。各実装Issueで実コードCIと検証を追加します。提示要件および追加された正式な引き継ぎ仕様に従います。
"""
    body_path = directory / ".git/sauna-foundation-pr.md"
    body_path.write_text(body)
    url = run(["gh", "pr", "create", "--repo", f"{ORG}/{repo}", "--base", "main", "--head", BRANCH, "--title", f"chore: initialize {repo} development foundation", "--body-file", str(body_path)], directory)
    state["repositories"][repo] = {"url": f"https://github.com/{ORG}/{repo}", "branch": BRANCH, "commit": commit, "pr_url": url, "validation": "policy structure and git diff --check passed; Actions pending"}
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")
    print(f"{repo}: {url}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflow-ref", required=True)
    parser.add_argument("--repo", action="append", choices=list(SCOPES))
    parser.add_argument("--apply", action="store_true", help="Clone, commit, push branches, and open PRs after review")
    args = parser.parse_args()
    repos = list(dict.fromkeys(args.repo or SCOPES))
    preflight(repos, args.workflow_ref)
    if not args.apply:
        print("Preflight passed; no files or remote settings changed.")
        return
    state = json.loads(STATE_PATH.read_text()) if STATE_PATH.exists() else {"organization": ORG, "repositories": {}}
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    state["common_policy_sha"] = args.workflow_ref
    for repo in repos:
        publish(repo, WORKSPACE / repo, args.workflow_ref, state)


if __name__ == "__main__":
    main()
