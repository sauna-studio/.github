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
