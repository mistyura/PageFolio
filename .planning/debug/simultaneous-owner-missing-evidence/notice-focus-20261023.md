# 通知試験の前景不一致・継続調査（2026-10-23）

`$gsd-debug continue simultaneous-owner-missing` から、最新全件の別症状を調査した。元のowner_missing、DEP-05 timeoutとの因果は未確定。

## 保存済み失敗の分析

- `native-full-20261023.txt`: 1678 passed / 1 failed / 1 warning / 274.31秒。失敗は通知ownerの前後HWND比較199190→134248。
- `native-audit-artifacts/full/test_notice_dedup_eight_proces0/`: 8 peerは全てacquired=false、同じgeneration/deadline/HWNDのsnapshotを参照。各peerの処理前後HWNDは199190。ownerの通知HWNDは6295044で、前後の前景HWNDとは異なる。
- ownerのelapsed=1860ms、期限差=1800msは記録されている。ただし前景assertで停止したため、後続の期限assertが実行済みだったとは扱わない。
- `tests/test_startup_windows.py` のnotice-case分岐はNativeNoticeLifetimeを使う。simultaneous系のSetWindowSubclass監査はこの分岐では動作しない。間接影響を排除したことにはならない。
- `pagefolio/startup_win32.py` は表示・破棄の前後を既に測定するが、この分岐では4値を保存していなかった。保存済み失敗には、変更先HWNDのPID/class、変化した瞬間、表示/破棄前後4値がない。現在のHWND照会で当時の所有者を断定しない。

## 仮説と診断変更

製品側の表示/破棄で前景が変わる可能性と、通知の待機中に別要因で変わる可能性を並列に保持する。複合原因も未排除。8 peerの前後値が一致していても、その間の一時的変化は排除できない。

notice-caseの診断に既存のforeground_before_show / foreground_after_show / foreground_before_close / foreground_after_closeだけを保存する7行を追加。新しいOS呼出し・thread・hook・pollingは追加していない。製品コード、期限、guard、既存assertは変更なし。将来不一致が再発すれば区間を絞れるが、同期点間の値だけで因果や変更主体を確定するものではない。

## 対象検証

通常権限Windows・既存.venvで対象を1回だけ実行。

```powershell
.venv/Scripts/python.exe -m pytest tests/test_startup_windows.py::test_notice_dedup_eight_processes_keep_original_deadline -q --tb=short --basetemp="$env:LOCALAPPDATA\Temp\pf_notice_focus_20261023_01"
```

**1 passed / 1 warning / 2.49秒 / exit 0**。警告は既存PyMuPDF ByteString非推奨。ownerはelapsed=1875ms、期限差1800ms、追加4値と開始/終了の前景は全て199190。今回は前景比較後の期限assertまで通過した。前回失敗の原因修復・再現ではない。

`notice-focus-targeted-20261023.txt` と `notice-focus-artifacts-20261023/` に証拠を保存。ready/result/tracebackの19ファイルを原本保持でコピーしSHA256一致確認。manifest.jsonに原本パス・hashを記録。一時ディレクトリのsandbox読み取り拒否後、通常権限でコピーを完了した。

## 静的検証と作業上の復旧

- Ruff check成功。Pythonを明示対象とした全体formatは101 files left unchanged。pagefolio.py / tracerのAST成功。アクセス不能な既存生成物pf_owner_missing_entry_audit_20261023だけをRuff走査から除外。
- 最初のformatはMarkdownコードブロックも対象にして60文書を整形してしまった。開始時cleanだった追跡58文書をindexから復元。未追跡04-PATTERNS.md / 05-PATTERNS.mdは作成時sessionのAdd File原文を取得し、原文を同じRuffで整形した出力が変更後文書と完全一致することを確認して原文へ復元。対象外文書の変更は残していない。
- 製品等の先行4ファイル（app.py/settings.py/test_config_notification.py/test_settings_keyguard.py）は05-02-CHECKPOINTのSHA256と一致。
- 診断追加後tracer SHA256: `736CB28626B7F12C1C1710ACD611B323D449612F10E338EE521E6A229BC7CE09`。

## 判断・再開点

原因未確定のため全件を反復せず、最新全件の1 failedを保持する。新しい診断の単体成功で全件ゲートを解除しない。Phase 5停止、05-02-01未完了・未コミット、DEP-05未解除を維持。

次の判断候補は、(1) 診断を保持して次の必要な検証での再発証拠を待つ、(2) 対象1件に限定した前景イベント監査（時刻・HWND・PID/class、既存の期限とassert維持）を設計・検証する。過去の変更主体は保存記録だけでは復元できない。全件の無調整反復は提案しない。
