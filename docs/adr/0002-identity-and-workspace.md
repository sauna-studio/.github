# ADR-0002: Passkey認証とWorkspace連携の分離

Status: Accepted / 2026-11-01

## Decision
SaunaへのログインはPasskey/WebAuthnのみ。Google OAuthをログイン手段に追加しない。登録/認証challengeは有効期限、単回利用、RP ID、origin、user verification、replay拒否をサーバーで検証する。端末紛失時の復旧は別のPasskey追加や監査付き手順を設計し、メールリンクをログイン代替にしない。

社員はGoogle Workspace組織アカウント必須。Google identityのissuer/subjectを既存のPasskey主体と安全に紐付け、Directory/Groups等で所属と退職・停止を確認する。ドメイン文字列やOAuth同意だけで施設管理権限を付与しない。業務権限はAPIの施設membershipから判定する。

OAuth scopesはChat / Calendar / Directory / Groups / Driveの必要最小単位を統合ごとに明記する。refresh tokenは暗号化保管し失効・再認可に対応。組織全体のdomain-wide delegationや広範囲の権限付与は明示承認が必要で、本構築では実施しない。

Google Cloud Swiftクライアントの生成対象はCloud APIであり、Workspace APIのクライアント提供を意味しない。WorkspaceごとにDiscovery/REST、OAuth、pagination、quota、retry、admin権限の対応表を作る。対応していると推測して依存を追加しない。

Google Chat Botはsauna-automationに置き、GoogleChatApp (zunda-pixel/GoogleChatApp と個人Project9) には変更を加えない。Chat要求の認証・署名/issuer/audience、再送、API権限を検証する。sauna-mcpも同じAPIと認可を利用し、DB直接更新や破壊操作の自動承認をしない。

## References
- https://github.com/googleapis/google-cloud-swift
- https://developers.google.com/workspace
- https://developers.google.com/workspace/chat
- https://www.w3.org/TR/webauthn-3/
