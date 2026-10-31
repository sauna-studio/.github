# Sauna Studio backlog

共有 ChatGPT 会話の取得に失敗したため、要件から再構成した暫定50件、原文照合未了。元会話の50 Issueをそのまま継承したものではない。追加15件と親Epic7件を区別して管理する。

## 構成

- MVP: `MVP-001`–`MVP-050` の50件。
- GitHub基盤: `FOUND-001`–`FOUND-008` の8件。
- Workspace・Chat・MCP: `INTEGRATION-001`–`INTEGRATION-007` の7件。
- 親Epic: `EPIC-001`–`EPIC-007` の7件。合計72件。

正本は [backlog.json](../bootstrap/backlog.json)。各 Issue は安定キーで既存 Issue を照合してから作成する。受け入れ条件と依存キーを本文に保存し、GitHub の Sub-issues と blocking dependencies にも反映する。GitHub API の制約で一部反映できない場合は本文リンクと再実行手順を残す。

## 最初の実装

`FOUND-001` の完了後、`MVP-001`（OpenAPI health/version契約）を `sauna-api` のブランチとPRで開始する。基盤未整備を完了扱いにせず、後続の `MVP-002` で Hummingbird を実行可能にする。

## 依存順

以下はグラフのトポロジカル順。同一段階でも受け入れ条件が満たされるまでは依存先を完了扱いにしない。親Epicの包含は実装ブロックと区別する。

1. **EPIC-001** `.github` — GitHub 開発基盤（依存: なし）
2. **EPIC-002** `sauna-api` — API・認証・施設境界（依存: なし）
3. **EPIC-003** `sauna-api` — 予約・在庫・決済（依存: なし）
4. **EPIC-004** `sauna-web` — 利用者・管理者クライアント（依存: なし）
5. **EPIC-005** `sauna-infrastructure` — 運用・品質・リリース（依存: なし）
6. **EPIC-006** `sauna-automation` — Google Workspace・Chat・MCP 連携（依存: なし）
7. **EPIC-007** `sauna-api` — スタッフ業務・チャット（依存: なし）
8. **FOUND-001** `.github` — Organization 共通開発基盤を整備する（依存: なし）
9. **FOUND-002** `.github` — 8 リポジトリを安全に初期化する（依存: FOUND-001）
10. **FOUND-003** `.github` — Organization Project と Issue グラフを構築する（依存: FOUND-001）
11. **FOUND-007** `.github` — MCP・Skills とローカルツールの実行可能性を監査する（依存: FOUND-001）
12. **MVP-001** `sauna-api` — OpenAPI の health・version 契約を定義する（依存: FOUND-001）
13. **FOUND-004** `.github` — Rulesets と Required Checks を設定する（依存: FOUND-002）
14. **FOUND-005** `.github` — 依存関係・コード・Secret のセキュリティ検査を整備する（依存: FOUND-002）
15. **FOUND-006** `sauna-docs` — ADR と GitHub Wiki の運用を開始する（依存: FOUND-002）
16. **FOUND-008** `.github` — 言語別 CI とリリース・Environment 規約を整備する（依存: FOUND-002）
17. **MVP-002** `sauna-api` — Hummingbird の実行可能な API 雛形を構築する（依存: MVP-001）
18. **INTEGRATION-001** `sauna-automation` — Google Workspace 認可と API 対応表を設計する（依存: FOUND-006）
19. **MVP-003** `sauna-api` — PostgreSQL 18 と PostgresNIO の基盤を構築する（依存: MVP-002）
20. **MVP-030** `sauna-web` — SvelteKit 利用者 Web の基盤を作成する（依存: FOUND-008, MVP-001）
21. **MVP-037** `sauna-app` — SwiftUI iOS・iPadOS 利用者アプリ基盤を作成する（依存: FOUND-008, MVP-001）
22. **MVP-004** `sauna-api` — Atlas によるマイグレーションを導入する（依存: MVP-003）
23. **MVP-005** `sauna-api` — 施設境界と tenant context を強制する（依存: MVP-004）
24. **INTEGRATION-002** `sauna-automation` — Directory による社員所属確認を実装する（依存: INTEGRATION-001, MVP-005）
25. **MVP-006** `sauna-api` — Passkey challenge のライフサイクルを実装する（依存: MVP-005）
26. **MVP-012** `sauna-api` — サウナ・テントの商品カタログ API を実装する（依存: MVP-005）
27. **MVP-007** `sauna-api` — Passkey 登録を実装する（依存: MVP-006）
28. **MVP-013** `sauna-api` — リソース・在庫台帳を実装する（依存: MVP-012）
29. **MVP-008** `sauna-api` — Passkey ログインを実装する（依存: MVP-007）
30. **MVP-014** `sauna-api` — 価格・営業日・時間帯ルールを実装する（依存: MVP-013）
31. **MVP-009** `sauna-api` — セッション・ログアウト・Passkey 管理を実装する（依存: MVP-008）
32. **MVP-015** `sauna-api` — 空き状況検索 API を実装する（依存: MVP-014）
33. **INTEGRATION-003** `sauna-api` — Passkey 利用者と Workspace 社員 ID を紐付ける（依存: INTEGRATION-002, MVP-009）
34. **MVP-016** `sauna-api` — 複数商品カートと見積もりを実装する（依存: MVP-015, MVP-009）
35. **MVP-031** `sauna-web` — Web の Passkey 認証 UI を実装する（依存: MVP-030, MVP-009）
36. **MVP-032** `sauna-web` — 商品・空き状況検索画面を実装する（依存: MVP-030, MVP-015）
37. **MVP-038** `sauna-app` — Apple アプリの Passkey 認証を実装する（依存: MVP-037, MVP-009）
38. **MVP-010** `sauna-api` — Workspace 必須の社員プロビジョニングを実装する（依存: INTEGRATION-003）
39. **MVP-017** `sauna-api` — 期限付き在庫 hold と競合制御を実装する（依存: MVP-016）
40. **MVP-011** `sauna-api` — スタッフの施設別ロール・認可を実装する（依存: MVP-010）
41. **MVP-018** `sauna-api` — 複数商品予約を原子的に確定する（依存: MVP-017）
42. **INTEGRATION-006** `sauna-automation` — Groups・Drive の必要範囲を連携する（依存: INTEGRATION-003, MVP-011）
43. **MVP-019** `sauna-api` — hold 失効・在庫解放ジョブを実装する（依存: MVP-018）
44. **MVP-026** `sauna-api` — 管理者の商品・価格・営業設定 API を実装する（依存: MVP-014, MVP-011）
45. **MVP-027** `sauna-api` — 設備状態・メンテナンス枠を管理する（依存: MVP-017, MVP-011）
46. **MVP-028** `sauna-api` — スタッフシフト API を実装する（依存: MVP-011）
47. **MVP-020** `sauna-api` — Stripe Checkout と決済開始を実装する（依存: MVP-019）
48. **MVP-035** `sauna-admin-web` — 管理者 SvelteKit Web と予約・設備管理を実装する（依存: FOUND-008, MVP-026, MVP-027, MVP-031）
49. **MVP-021** `sauna-api` — Stripe webhook の検証と冪等処理を実装する（依存: MVP-020）
50. **MVP-022** `sauna-api` — 決済照合と例外回復を実装する（依存: MVP-021）
51. **MVP-033** `sauna-web` — 複数商品予約と Stripe 遷移 UI を実装する（依存: MVP-031, MVP-032, MVP-021）
52. **MVP-023** `sauna-api` — 予約取消・キャンセル料・返金を実装する（依存: MVP-022）
53. **MVP-024** `sauna-api` — 利用者の予約一覧・詳細 API を実装する（依存: MVP-023）
54. **MVP-025** `sauna-api` — 利用者・スタッフ間チャット API を実装する（依存: MVP-024, MVP-011）
55. **MVP-029** `sauna-api` — 業務イベント outbox と通知を実装する（依存: MVP-024, MVP-028）
56. **INTEGRATION-004** `sauna-automation` — Google Chat Sauna Bot を実装する（依存: INTEGRATION-003, MVP-024, MVP-029）
57. **INTEGRATION-005** `sauna-automation` — Calendar に予約・シフトの派生ビューを同期する（依存: INTEGRATION-003, MVP-028, MVP-029）
58. **MVP-034** `sauna-web` — 予約管理とチャット画面を実装する（依存: MVP-033, MVP-025）
59. **MVP-036** `sauna-admin-web` — シフト・社員・チャット管理画面を実装する（依存: MVP-035, MVP-028, MVP-025）
60. **MVP-039** `sauna-app` — 利用者アプリの予約・決済・チャットを実装する（依存: MVP-038, MVP-025, MVP-033）
61. **MVP-041** `sauna-infrastructure` — OpenTelemetry の trace・metric・log を整備する（依存: MVP-002, MVP-029）
62. **MVP-046** `sauna-docs` — 個人情報の保持・削除・利用規約を設計する（依存: FOUND-006, MVP-025）
63. **MVP-040** `sauna-admin-app` — SwiftUI 管理者アプリを実装する（依存: MVP-037, MVP-038, MVP-036）
64. **MVP-042** `sauna-api` — API コンテナと PostgreSQL 18 開発環境を作成する（依存: MVP-003, MVP-041）
65. **MVP-047** `sauna-api` — 業務監査ログを実装する（依存: MVP-023, MVP-028, MVP-046）
66. **INTEGRATION-007** `sauna-automation` — sauna-mcp の認可付き業務ツールを実装する（依存: INTEGRATION-003, MVP-024, MVP-047）
67. **MVP-043** `sauna-infrastructure` — Cloud Run・Cloud SQL の Terraform を設計・検証する（依存: FOUND-008, MVP-042）
68. **MVP-045** `sauna-api` — 予約・決済・認証の統合・競合テストを整備する（依存: MVP-023, MVP-009, MVP-042）
69. **MVP-049** `sauna-web` — アクセシビリティと最新安定ブラウザ互換性を検証する（依存: MVP-034, MVP-036, MVP-039, MVP-040）
70. **MVP-044** `sauna-infrastructure` — staging 用 CI/CD と Environment を定義する（依存: MVP-043）
71. **MVP-048** `sauna-docs` — 障害対応・backup・復旧手順を整備する（依存: MVP-044, MVP-047）
72. **MVP-050** `sauna-docs` — MVP の受け入れ・リリース判定を実施する（依存: MVP-045, MVP-048, MVP-049, INTEGRATION-004, INTEGRATION-005, INTEGRATION-006, INTEGRATION-007）

## 実装・レビュー条件

すべての実装で Coding Agent と独立 Review Agent を並行起動する。認証、決済、予約競合、個人情報、施設権限を変更する場合は Security Review Agent も起動する。レビュー結果だけで完了せず、実ビルド・テスト・利用可能なMCPで検証し、結果と未検証項目をPRへ記録する。

新しいバグは安定キー・タイトル・既存本文を照合して重複を避け、回帰テストと再レビューを行う。重要な設計決定と繰り返す指摘はADRと必要に応じたAGENTS.md更新に反映する。

GoogleChatApp とその個人Projectは対象外。Google Chat BotはSauna APIを経由し、予約・決済・シフトの正本をGoogle側へ移さない。本番deploy、有料リソース作成、広範囲の権限付与はこのbacklogによって承認されない。
