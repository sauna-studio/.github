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
