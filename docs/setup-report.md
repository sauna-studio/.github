# Sauna Studio 初期構築の実績 — 2026-11-01 JST

## 完了

9リポジトリを公開で初期化し、元LICENSE/履歴を保護した。ユーザーの最新の公開承認を追加資料のprivate案より優先した。GoogleChatAppと個人Project9は変更していない。

- Organization profile / README / AGENTS / Issue Forms / PR template / CODEOWNERS / Dependabot / Codex5役割を配置
- Reusable repository / Swift / Web / Terraform workflows、実PythonのCodeQL
- 全9repoのmainにPR/required CI・force push/delete禁止Ruleset、bypassなし
- Secret scanning / push protection / Dependabot / 非公開脆弱性報告を有効化
- development/staging/production Environmentsを名前とbranch policyのみ作成。本番approval gate/Secrets/deploymentは未実施
- [Organization Project](https://github.com/orgs/sauna-studio/projects/1): 計画94件、native blocked-by180本、parent/subissue87本を実API照合
- Backlog / Development board / Roadmap / By repository / Blocked / Release readinessの6ビュー。リポジトリ別groupingとロードマップの日付入力は未設定
- 計画はMVP50 + G8 + T15 + W14 + Epic7。共有会話/元50件の個別題名は未確認、引継ぎ資料のグループIDへの暫定対応とcoverage gapを明記

## リポジトリとPR

初期9PRはGitHub Codex gateの追加指示前に独立Review/Security Reviewと実CI成功を確認しmergeした。追補PRは外部Codexレビュー未完のため全てopen。

| Repository | 初期PR（merge済み） | CodexルールとCI参照修正PR（open） |
| --- | --- | --- |
| [.github](https://github.com/sauna-studio/.github) | [#9](https://github.com/sauna-studio/.github/pull/9) | [#11](https://github.com/sauna-studio/.github/pull/11) |
| [sauna-api](https://github.com/sauna-studio/sauna-api) | [#37](https://github.com/sauna-studio/sauna-api/pull/37) | [#40](https://github.com/sauna-studio/sauna-api/pull/40) |
| [sauna-app](https://github.com/sauna-studio/sauna-app) | [#4](https://github.com/sauna-studio/sauna-app/pull/4) | [#5](https://github.com/sauna-studio/sauna-app/pull/5) |
| [sauna-web](https://github.com/sauna-studio/sauna-web) | [#8](https://github.com/sauna-studio/sauna-web/pull/8) | [#9](https://github.com/sauna-studio/sauna-web/pull/9) |
| [sauna-admin-app](https://github.com/sauna-studio/sauna-admin-app) | [#2](https://github.com/sauna-studio/sauna-admin-app/pull/2) | [#3](https://github.com/sauna-studio/sauna-admin-app/pull/3) |
| [sauna-admin-web](https://github.com/sauna-studio/sauna-admin-web) | [#3](https://github.com/sauna-studio/sauna-admin-web/pull/3) | [#4](https://github.com/sauna-studio/sauna-admin-web/pull/4) |
| [sauna-infrastructure](https://github.com/sauna-studio/sauna-infrastructure) | [#5](https://github.com/sauna-studio/sauna-infrastructure/pull/5) | [#6](https://github.com/sauna-studio/sauna-infrastructure/pull/6) |
| [sauna-automation](https://github.com/sauna-studio/sauna-automation) | [#30](https://github.com/sauna-studio/sauna-automation/pull/30) | [#31](https://github.com/sauna-studio/sauna-automation/pull/31) |
| [sauna-docs](https://github.com/sauna-studio/sauna-docs) | [#5](https://github.com/sauna-studio/sauna-docs/pull/5) | [#6](https://github.com/sauna-studio/sauna-docs/pull/6) |

## 最初のMVP実装

[sauna-api #39](https://github.com/sauna-studio/sauna-api/pull/39) は [Issue #5 / B01](https://github.com/sauna-studio/sauna-api/issues/5) のhealth/version OpenAPI契約。Swift OpenAPI Generatorでtypes/serverを実生成・compileし、固定依存lock、schema/example/否定テストを追加。HTTPサーバは後続 [Issue #6](https://github.com/sauna-studio/sauna-api/issues/6) であり、本PRでは未実装。

MacとLinuxでSwift build/test成功（Swift5 tests）、Python7 tests/OpenAPI4 examples成功。最新HEADのpush/PR Repository CIとCodeQL計4runすべて成功。独立Reviewで改行を許容するsemver不具合を発見し、[bug #38](https://github.com/sauna-studio/sauna-api/issues/38) に追跡、両version fieldの10改行caseを含む回帰を追加した。

## レビューと実検証

Coding Agentと別コンテキストのReview Agentを実際に並行起動。Security Reviewも別Agentで実施し、GitHub上のCodexレビューとは区別した。

- 共通設定: validator / YAML / TOML / local links / actionlint / diff-check成功
- 共通bootstrapの回帰17 tests成功。独立Reviewerも再実行成功
- 8repo追補PR: 最新headのpush/PR計16run成功
- Projectの実グラフ94/180/87とmembershipを独立再照合し一致
- 初期ReusableのSwift/Web/Terraformは対応コードなしのため包括動作未検証。Swift呼出は今回MVP契約で実動確認

修正した主要指摘: 既存/同run中のIssue本文上書き、title-only誤採用、入力DAG検査、配布リンク、source SHA追跡、リリースgateの依存漏れ、semver改行、共通Workflow参照の寿命。

[Project登録bug #10](https://github.com/sauna-studio/.github/issues/10) はSub-issue自動追加と一覧index伝播遅延によりduplicate応答で停止。Issue.projectItems参照と冪等batch同期で復旧し回帰検証した。

[Workflow参照bug #12](https://github.com/sauna-studio/.github/issues/12) はsquash後に未保持SHAがActionsで解決不能。全8追補とMVP PRでmain履歴SHA84222ffに修正、最新実CI成功。初期化scriptは未保持SHAを拒否する。各mainへの修正取り込みは追補PRの外部Codex gate完了後。

## GitHub Codexレビュー待ち

ユーザー指示により「指摘対応・thread返信 → @codex review → 最新commitで指摘ゼロ → CI成功」をmerge条件に追加。レビュー未着をゼロと見なさない。

既存9PRにもCLIで依頼。新しい追補9PRとMVP PRにも依頼し、応答を確認する。確認時点では自動Codexのreview投稿なし、MCPの連携先にsauna-studioがなくコメント書込は403。CLIはrepo/workflow/project権限を持つためPR/Issue操作には利用できる。Code Reviewの設定確認をユーザーへ依頼済み。外部レビューの応答と最新SHAを確認するまでmergeしない。

## MCP・Skillsと未完了

GitHub MCPはpublic repoメタデータと連携一覧の読取に実利用、書込403はCLIへ代替。OpenAI Docsでagent定義/GitHubレビュー公式仕様を確認。skill-installerでSwiftUI Expertを導入（次ターンから利用、SwiftUI実装にはまだ使っていない）。Xcode MCPは利用可能だがアプリ未作成につきビルドには未使用。Safari MCP binary確認済み・未接続。Wiki初期化可否をComputer Useで確認したがGitHub未ログイン。

- WikiはADR/原稿/索引まで。初回ページのWeb初期化と公開は未完了
- TablePro接続、PostgreSQL18/Docker/Atlas/Terraform導入と実DB/infra検証は後続Issue
- Appleアプリ/Simulator、SvelteKit/Playwrightの実動検証は後続Issue
- Releases/Packagesは配布成果物ができてレビュー完了後。空のreleaseは作らない
- org-wide Actions設定はadmin:org不足403、scope拡張せずrepo単位で設定
- 本番デプロイ、課金リソース作成、広範囲IAM/Workspace権限付与、Secrets設定はしていない

次は外部Codexレビューの指摘対応と反復、追補PRの取り込み、その後MVP依存順でHummingbird稼働・PostgreSQL/Atlasを実装する。
