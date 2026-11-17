# Sauna Studio · Organization foundation

川沿いの小規模サウナ施設の予約・決済・運営を支えるサービスです。初期は1施設、データ・認可は複数施設に対応します。

このリポジトリは共通開発規則、Organizationプロフィール、Issue Forms、PRテンプレート、Reusable Workflows、Codexエージェント定義の正本です。

| Repository | Responsibility |
| --- | --- |
| [sauna-api](https://github.com/sauna-studio/sauna-api) | Swift 6 / Hummingbird / PostgreSQL 18 / PostgresNIO / Atlas / OpenAPI |
| [sauna-app](https://github.com/sauna-studio/sauna-app) | 利用者向け SwiftUI / iOS・iPadOS 27.2以上 |
| [sauna-web](https://github.com/sauna-studio/sauna-web) | 利用者向け SvelteKit / TypeScript |
| [sauna-admin-app](https://github.com/sauna-studio/sauna-admin-app) | 管理者向け SwiftUI / iOS・iPadOS 27.2以上 |
| [sauna-admin-web](https://github.com/sauna-studio/sauna-admin-web) | 管理者向け SvelteKit / TypeScript |
| [sauna-infrastructure](https://github.com/sauna-studio/sauna-infrastructure) | Terraform / Google Cloud Run・Cloud SQL / OpenTelemetry |
| [sauna-automation](https://github.com/sauna-studio/sauna-automation) | Google Chat Bot / Workspace連携 / sauna-mcp |
| [sauna-docs](https://github.com/sauna-studio/sauna-docs) | 設計書 / ADR / Wiki / 実装バックログ |
| [.github](https://github.com/sauna-studio/.github) | 共通設定・テンプレート・Actions |

SaunaへのログインはPasskeyのみ。社員にはGoogle Workspace組織アカウントを必須とし、所属確認・本人との紐付け・Google API認可に使用します。予約・決済・シフトの正本はSauna APIとPostgreSQLです。Google Cloud SwiftクライアントとWorkspace APIの対応範囲を区別します。

[GoogleChatApp](https://github.com/zunda-pixel/GoogleChatApp) は独立プロジェクトです。移動・複製・変更しません。デザインは [Tweetbot](https://github.com/zunda-pixel/tweetbot) のVintage・Pumpkinを参照し、資産の利用条件を確認してから取り込みます。

開発前に [AGENTS.md](AGENTS.md) と [CONTRIBUTING.md](CONTRIBUTING.md) を読み、Issueの依存関係を満たしてからブランチとPRで変更します。実装中は独立Review Agentを並行起動します。

共通ファイルは自動継承されるとは限りません。`AGENTS.md`・CODEOWNERS・CI・ライセンスは各リポジトリに明示配置し、共通規則の改訂時は追従PRで更新します。Reusable Workflowはレビュー済みのコミットSHAを指定して呼び出します。

SwiftUIを実装する両iOS repoには、[専用指針](policies/swiftui.md)の本文と適用元commitをAGENTSへ明示配置します。この指針は文書だけでUI動作・性能検証を完了扱いにしません。

ローカル検証（Python 3.11以上を使用。macOS標準Pythonが古い場合はHomebrew等のPythonを明示指定）:

```sh
python3 -m venv /tmp/sauna-foundation-venv
/tmp/sauna-foundation-venv/bin/pip install -r scripts/validation-requirements.txt
/tmp/sauna-foundation-venv/bin/python scripts/validate_repository.py
actionlint
```

これは本番デプロイや課金リソース作成を行うリポジトリではありません。GitHub上の設定・適用結果と未完了事項は作業記録に残します。

- [Workflow dependency lockfiles](policies/workflow-lockfiles.md): generated coverage and provenance verification alongside existing SHA pins.

共通Swift workflowは独立したlint jobで`swift format lint -r -p -s .`を実行し、リポジトリ全体のSwift書式違反をエラーにします。build/testと同じdigest固定のSwift toolchainを使用します。呼出先への適用には、この変更を含むdefault branchのcommit SHAへ更新する追従PRが必要です。


Workaroundを導入するPRは、merge前に`workaround`ラベル付きの追跡Issueへ紐付けます。専用フォームは問題・回避方法・取り外す条件を短く残すための3欄です。通常の設計変更は対象にしません。

共通規則の追従には、merge済みsource SHAを指定して同期します（既定は差分表示、`--write`で反映、`--check`で一致検証）。既存の固有指針と他フォームは保持します。

```sh
python scripts/sync_workaround_policy.py /path/to/consumer --source-commit <full-merged-SHA> --write
python scripts/sync_workaround_policy.py /path/to/consumer --source-commit <full-merged-SHA> --check
```

Issues無効forkは`--issues-disabled`でフォームを追加せず、利用側Issueへ追跡します。AGENTS未配置のforkに限り`--allow-new-agents`も明示します。Issue機能や他の設定は変更しません。

`postgres-nio`の同期対象は維持branch `sauna-1.33.2`です。上流同期用の`main`は変更しません。`origin/main`と`origin/sauna-1.33.2`をfetchし、維持履歴を含む作業branchでhelperを実行して、PRのbaseも`sauna-1.33.2`にします。helperは`main`・維持branchへの直接適用、detached HEAD、維持履歴を含まないcheckout、および維持branchにないmain側の履歴を取り込んだcheckoutを拒否します。
