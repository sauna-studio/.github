# 環境監査 — 2026-11-01 JST

## 確認できたこと

- GitHub CLI 2.101.0 / GitHub MCPでsauna-studio/.githubへのADMIN権限を確認。CLI利用者はzunda-pixel、Org membershipはactive/admin。
- 初期状態はpublic .githubのみ、LICENSEのみ、clean main。既存アプリ変更なし。GoogleChatAppと個人Project9は操作対象外。
- 認証scopeはrepo/workflow/project/read:org/gist。token値の取得・ファイル保存はしない。
- Organization Actions policiesのAPIは403 (admin:org不足)。scope拡張や組織全体の権限変更は未実施。repo単位Actionsはenabled。
- Swift6.4.2 / Xcode27.2 / Node26.10.0 / npm11.19.1 / Python3.9.6を実行確認。
- GitHub MCPでrepo metadataを取得。Xcode MCPはセッションに公開済み。アプリがまだないためAppleビルド/Simulator動作は未検証。
- Safari MCP実行ファイル /usr/bin/safarimcp を確認しhelp実行。現在セッションでは未接続。safarimcp stdio用設定はアプリ開発時に追加し、Safariの自動操作許可を勝手に有効化しない。
- skill-installerの公式helperでAvdLee/SwiftUI-Agent-Skillのskills/swiftui-expert-skillをユーザー領域に導入。次ターンから利用可能。まだSwiftUI実装には使っていない。

- 構造検証はHomebrew Python3.14の一時venvで実施。macOS標準Python3.9はtomllibを持たないため本validatorの要件(Python3.11+)を満たさない。
- 追加資料3件を全読し、.githubのみpublic/他8repo privateという資料中の案(後続ユーザー明示で全publicに変更)、計画ID体系、schema.sql正本/forward-only、hosted Checkout、天候閉鎖、read-only Bot/MCPを追加確認。資料原本は個人のDownloadsパスを含むためコミットしない。

## 未導入・未接続

- TablePro MCP: このセッションのツールとして利用不可、DB接続先も未作成。実DBテストは未実施。
- PostgreSQL18 / Docker / Atlas / Terraform: PATHに実行ファイルなし。DB/infra Issueで公式バージョンを選定し導入・実行検証する。本構築に本番GCP資格情報は不要。
- XcodeMCPKit: ローカルソースと公式READMEを確認。現在のXcode MCP (xcrun mcpbridge)とは別物。proxy未導入・未使用。auto-approveを有効化しない。
- NeoSimulator: ローカルソースと公式リポジトリを確認。未ビルド・未使用。
- lynnswap/swift-build / Custom Xcode Build Service: 公式repo確認。Xcodeのグローバルbuild service置換は未実施。標準xcodebuild/swiftを代替とする。
- Playwright / Svelte関連Skills: Webコード作成時にproject devDependencyとして導入し、ブラウザ実行を確認する。現在Web動作検証なし。

## 引継ぎ元と参照

共有ChatGPT会話はタイムアウトで取得不能。提示要件を正本とし、元のMVP50件は未照合。blindlog-apiのGitHub上のPackage.swiftとtweetbotのテーマ実装を確認。blindlogの独自branch依存や別事業の環境設定はコピーしない。

- https://chatgpt.com/share/6ae603ff-1330-83ee-a7ca-510c48e0e64b
- https://github.com/zunda-pixel/blindlog-api
- https://github.com/zunda-pixel/tweetbot
- https://github.com/googleapis/google-cloud-swift
- https://github.com/lynnswap/XcodeMCPKit
- https://github.com/lynnswap/NeoSimulator
- https://github.com/lynnswap/swift-build
- https://github.com/AvdLee/SwiftUI-Agent-Skill
- https://webkit.org/blog/18136/introducing-the-safari-mcp-server-for-web-developers/

Wiki cloneは未初期化のためRepository not found。GitHub Wiki有効化とwiki git repository初期化は別。docs/wikiにレビュー可能な原稿を準備し、GitHub UI初期化後に同期する。

## 完了状態の補足

全9repoは最新ユーザー明示によりpublic。初期構築9PRは独立Review/Security ReviewとCI成功確認後にmerge済み。その後ユーザーからGitHub上の自動Codex指摘対応・返信・@codex review反復・指摘ゼロ確認を今後のmerge条件に追加する指示を受領した。全9既存PRを実APIで検査した時点でCodex reviews/commentsは0。MCPのGitHub連携一覧にsauna-studioがなく、コメント書込は403のためCLIで.github#9にレビュー依頼済み。未着を指摘ゼロと扱わない。

Rulesetsは全9repoでactive、PRと実在するCI contextを必須、bypassなし、mainのforce push/delete禁止。唯一ownerのためrequired approving reviewsは0。Codex GitHubレビュー条件はAGENTSとPR運用で追加し、機械的に実装したrequired status checkとは区別する。

Wiki原稿は準備済み、Wiki機能有効。Wiki git repositoryは未初期化。BrowserはGitHub未ログイン、MCPにWiki初期化機能がないため最初のページ公開は未実施。Environmentsはdevelopment/staging/productionを作成したがbranch policyのみで、本番承認gate・deployment・Secrets設定は未実施。

横断グラフの実API照合が完了: planning Issue94件、blocked-by180本、parent/subissue87本、全94件のProject membershipを確認。ProjectのSub-issue自動追加がenabledであるため一覧index反映前の重複応答が発生した。Issue.projectItemsを参照する同期で復旧した。途中のネットワークエラーは隠さず停止し、冪等再実行で補完した。

共通Workflowは初期075c669をsquash後に解決できないCI実障害を確認。追補PRではdefault branch履歴上の84222ffへcallerを修正し実Actionsを再検証。初期化scriptにmain祖先検査と4回帰テストを追加した。新しいCodexレビュー条件に従い、追補PRとMVP PRは外部レビュー未着の間はopenとする。
