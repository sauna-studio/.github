# ADR-0005: GitHub Codexレビューと保持されたWorkflow参照

Status: Accepted / 2026-11-01

## Context

初期基盤の独立並行Review/Security Reviewと実CIは成功しPR経由でmergeした。その後、ユーザーからGitHub上の自動Codexレビューへ対応・返信し、`@codex review`を依頼して指摘ゼロまで反復してからmergeする条件が追加された。

最初のAPI契約PRのCIでは、共通Workflowを未merge branchのSHAへ固定していたため、.githubをsquash mergeしてbranchを削除した後にActionsが参照を解決できなくなった。Contents APIで同SHAのblobは取得できても、Actionsの解決可能性は保証されなかった。

## Decision

独立並行Review Agent・Security Review Agent・実ビルド/テストに加えてGitHub Codex review roundを必須とする。各指摘へ修正・回帰テスト・thread返信を行い、新しい `@codex review` 依頼で最新commitのレビュー結果を得る。未着・エラー・上限は指摘なしではなく未完了である。詳細はpolicies/github-codex-review.mdに保持し全repoへ配布する。

Reusable Workflow参照は、共通repoのdefault branch履歴に保持された40桁SHAを使う。未merge/破棄されたbranchのSHAは初期化scriptで拒否する。compare APIでmerge_base==指定SHAかつstatusがahead/identicalを確認する。ユーザーのソース内容が同じでも呼出先repoで実Actionsを再実行する。共通branchの削除やsquash merge後も動作を確認する。

Code Review連携を有効化するための資格情報/広範な権限付与は勝手に追加しない。連携不在の場合は必要な設定先と現状を記録し、PRをopenに保つ。

## Consequences

PRのCI成功とGitHub Codexレビュー完了を別々に確認する。共通Workflow変更はmainの保持SHAができてから追従PRを作る。公開のWorkflow/規則には機密を置かない。

## Evidence

- https://github.com/sauna-studio/.github/issues/12
- https://github.com/sauna-studio/sauna-api/actions/runs/41214711200
- https://learn.chatgpt.com/docs/third-party/github
