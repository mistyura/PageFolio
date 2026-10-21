# Project Research Summary

**Project:** PageFolio v1.9.0「安全性・整合性の是正 + OpenAI プロバイダ追加」
**Domain:** Windows デスクトップ PDF エディタ（Tkinter・PyMuPDF・PyInstaller配布）へのバグ修正・設定UI整合性是正・OCR/LLMプロバイダ追加
**Researched:** 2026-08-10
**Confidence:** MEDIUM〜HIGH

## Executive Summary

v1.9.0 は新機能追加が主目的ではなく、既存機能レビュー（V190-REV-01〜08）で発見された8件の安全性・整合性バグの是正と、その基盤の上に載せるOpenAI(ChatGPT) OCR プロバイダのフル実装という2階建ての構成である。4本の並行リサーチ（STACK/FEATURES/ARCHITECTURE/PITFALLS）は「安全性是正が先、OpenAI追加が後」「プロバイダメタデータ一元化（V190-REV-08）がOpenAI追加の直前必須依存」という2点で完全に一致しており、これがロードマップの背骨になる。

技術的な核心は3つ。(1) PyMuPDF の Document.save()/tobytes() は encryption= 引数を明示しない限り暗号化を静かに解除する仕様であり、これが暗号化PDF平文化事故（V190-REV-01）の直接原因——encryption=fitz.PDF_ENCRYPT_KEEP を通常保存・別名保存・インクリメンタル失敗フォールバックの3経路すべてに共通ヘルパー経由で適用することが対策。(2) OCRプロバイダのメタデータ（表示名・クラウド判定・既定モデル・送信先ホスト等）が最低7ファイル・5〜8箇所に手書きで重複しており、この状態でOpenAIを追加すると分岐の書き漏らしがほぼ確実に発生する——catalog.py を新設し一元化してから追加すべき。(3) OpenAI の Chat Completions API は既存 RunPodProvider/LMStudioProvider とほぼ同一の「OpenAI互換」形状であり、urllib直叩き（新規pip依存ゼロ方針を維持）で最小差分実装が可能。ただし /v1/models に vision対応フラグが無いという非対称性があり、モデル一覧フィルタは名前ベースの簡易ヒューリスティックで妥協する必要がある。

主要リスクは3つ。第一に Undo/編集系のロールバック不備——記録タイミングをずらすだけでは current_page/selected_pages スナップショットがずれる副作用を生むため、既存の _do_insert の「仮エントリ→確定」パターンを踏襲する必要がある。第二に設定ダイアログの外部ファイル副作用（V190-REV-05）——「Apply一本化」と「Cancel時復元（ライブ連動維持）」の二択で実装がまったく異なり、未決定のまま着手すると中途半端な実装になる。第三に Python 3.14 環境の Tcl/Tk 問題——STACKリサーチでは実機再現せず（別原因のPermissionErrorのみ検出）、PITFALLSリサーチは早期対応を推奨しており、この評価の食い違いを次フェーズで解消する必要がある。

## Key Findings

### Recommended Stack

新規pip依存は追加しない（urllib.request 直叩き方針を継続、V14-D-01）。OpenAI プロバイダは Chat Completions API を採用し、Responses API は不採用とする——既存 RunPodProvider が事実上同一形状で実装済みであり統合コストが最小、かつ Chat Completions は無期限サポートが公式に明言されているため。暗号化維持保存は PyMuPDF の encryption=fitz.PDF_ENCRYPT_KEEP で解決する。

**Core technologies:**
- OpenAI Chat Completions API (api.openai.com/v1/chat/completions) — OCR/サマリ送信先 — RunPodProvider/LMStudioProvider と同型の「OpenAI互換」形状のため最小差分で統合可能
- urllib.request（標準ライブラリのみ） — OpenAI API実装手段 — PyInstaller肥大化回避・既存5プロバイダとの実装一貫性維持
- fitz.PDF_ENCRYPT_KEEP（PyMuPDF既存API） — 暗号化維持保存 — パスワード文字列の再取得・再保持が不要

**環境修復:** Python 3.14.6 + Tkinter の init.tcl 読み込み失敗はSTACKリサーチの実機検証では再現せず、TCL_LIBRARY/TK_LIBRARY の venv相対パス誤解決（CPython #125235）が有力候補。PITFALLSリサーチは「テスト環境専用のハードコード修正は配布EXEのTcl/Tk探索ロジックと衝突しうる」ため、frozen判定と開発環境判定を分離した修復を推奨。

### Expected Features

**Must have (table stakes):**
- 暗号化維持のデフォルト化（V190-REV-01）— 3保存経路すべてにPDF_ENCRYPT_KEEP適用
- OCR OFFの全経路一貫化（V190-REV-02）— 通常OCR・バッチOCR起動時/実行開始時・プラグイン経路の4箇所で同一意味論
- 複数ファイル挿入のall-or-nothingトランザクション化（V190-REV-03）
- Undo記録の成功後確定（V190-REV-04）、復元失敗時のスタック保護（V190-REV-07）
- OpenAIプロバイダのtable stakes一式: セッションAPIキー入力欄・モデル一覧動的取得+静的フォールバック・送信先確認・コスト確認・バッチOCR組み込み・フォールバック候補組み込み・429/5xxリトライ共有基盤活用

**Should have (competitive/differentiator):**
- detailレベル選択（low/high/auto）— コストダイヤル。OCR用途では既定をhigh/auto寄りにする
- reasoning effort相当パラメータ（gpt-5系）— Claudeの EFFORT_MODELS 許可リスト方式を流用
- organization/project ID任意入力欄 — 優先度低、詳細設定領域に格納

**Defer (v2+/anti-features):**
- OpenAI Responses APIへのフル移行、公式SDK導入、organization自動検出、detail=high常時強制、部分適用の無警告許容、外部ファイルへのライブ即時書き込み維持（Cancel復元なしの場合）

### Architecture Approach

既存コードは「ロジックの重複は意図的（OCRDialog/BatchOCRDialogの独立性維持のため正当）」だが「データの重複は非意図的な技術的負債」という構造。pagefolio/ocr_providers/catalog.py を新設し、ProviderMeta（frozen dataclass）による非機密メタデータを一元管理する。registry.py（機密キー名解決、V180-D-01独立性制約）とは一方向import（catalog→registry）のみで循環を回避。

**Major components:**
1. catalog.py（新設）— プロバイダメタデータの単一情報源。7参照面へ段階的移行
2. openai_provider.py（新設）— OpenAIProvider。LMStudioProviderの payload/response処理を土台に固定エンドポイント・認証・パラメータ分岐を実装
3. file_ops.pyの保存系ヘルパー統一 — 4呼び出しが共通経由でencryption=を得る
4. Undo/Redoの「記録後置」パターン — _do_insertが確立している「仮エントリpush→成功時確定/失敗時pop」を横展開、_undo/_redoはpeek→正常終了後に確定popへ変更

### Critical Pitfalls

1. doc.save(path)のencryption省略が暗号化解除になる — 3保存経路すべてにPDF_ENCRYPT_KEEPを共通ヘルパー経由で適用し、パスワード付与/解除系とはヘルパーを分離する
2. _save_undoを実処理後へ移すとcurrent_page/selected_pagesスナップショットがずれる — _do_insertの「仮エントリ確定」パターンを流用するか、操作前値をローカル変数へ明示退避する
3. offをプロバイダ生成不可にする変更が既存の後方互換経路を壊す — 全参照箇所を洗い出し、専用例外を全呼び出し元で捕捉させる
4. メタデータ一元化リファクタでmonkeypatch対象の名前空間が断絶する — v1.8.0 Phase 1で実際に発生済み。リファクタ後、意図的に本番コードへバグを注入してテストが検知することを確認する
5. 外部プロンプトファイル書き込みが二重トリガー — 「一本化」と「ライブ連動維持+Cancel復元」の二択を実装前に確定させる

## Implications for Roadmap

4本のリサーチが完全一致する依存構造: 安全性是正（P0/P1）→ 設定UI整合性（P1、並行可）→ Undo/Redo回帰強化 → OCRプロバイダメタデータ一元化（V190-REV-08）→ OpenAIプロバイダ追加。catalog一元化はOpenAI追加のrequires-beforeであると定量的に裏付けられている。

### Phase 1: 保存・編集の安全性
**Rationale:** PROJECT.mdに明記された確定方針。4件は相互にファイルが独立し並行実施可能だが、REV-04→REV-03→REV-07の順で「記録後置パターン」を確立してから複雑ケースへ展開するのが自然
**Delivers:** V190-REV-01(暗号化維持)・REV-02(OCR OFF一貫化)・REV-03(複数ファイル挿入トランザクション化)・REV-04(複製Undo成功後確定)
**Addresses:** 失敗時ロールバックのtable stakes
**Avoids:** Pitfall 1(encryption省略)・6(Undoタイミング移動)・9(挿入部分残留)・10(offの二重意味)

### Phase 2: 設定UIの整合性
**Rationale:** llm_config配下のみに閉じており、Phase 1と衝突しないため並行実施可能。V190-REV-05の実装方式は着手前に確定必須
**Delivers:** REV-05(外部プロンプトApply一本化/Cancel復元)・REV-06(未保存確認のファイル連動非依存化)
**Uses:** 既存ShortcutsDialog(V171-D-05)の前例パターン

### Phase 3: Undo/Redo回帰強化
**Rationale:** Phase 1の「記録後置」安全網を復元側にも拡張。v1.8.0 Phase 6のD-17と同型パターン
**Delivers:** _undo/_redoのpeek→確定popへの変更、duplicate/merge/merge_resizeの4手往復テスト
**Avoids:** Pitfall 8(pop→restore間の例外)・7(Blob二重dispose)

### Phase 4: OCRプロバイダ基盤整理（catalog.py新設）
**Rationale:** Phase 1〜3完了後に着手。OpenAI追加の技術的前提条件
**Delivers:** catalog.py、7参照面への段階的移行
**Research Flag:** monkeypatch名前空間断絶リスク（Pitfall 12）に要注意

### Phase 5: OpenAIプロバイダのフル実装
**Rationale:** catalog完成後の着手で統合コスト最小化
**Delivers:** OpenAIProvider新設、UI統合一式
**Research Flag:** (a)モデル一覧フィルタ方式が未決定、(b)o-series向けパラメータ分岐、(c)実装開始時に実キーでモデル一覧を確認

### Phase 6: 品質保証・持ち越し（リリースゲート）
**Rationale:** Tcl/Tk環境修復は早期着手が望ましいが、最終確認はPhase 5完了後
**Delivers:** Tkinter環境修復、全テスト完走ゲート化、IN-01、human-verify/UAT

### Phase Ordering Rationale
- Phase 1・2は完全独立で並行可。Phase 5はPhase 4に技術的に依存する
- Phase 1の「記録後置」パターンはPhase 3の安全網にも構造的に流用できる
- Phase 4着手前にv1.8.0 Phase 1の類似リファクタ事例を参照し同じ轍を踏まない

### Research Flags

Needs research: Phase 4（catalog一元化・monkeypatch断絶リスク）、Phase 5（OpenAIモデルラインナップ・フィルタ方式未決定）、Phase 6（Tcl/Tk根本原因がリサーチ間で食い違い）

Standard patterns: Phase 1（PDF_ENCRYPT_KEEP・仮エントリパターンとも実コードで確立済み）、Phase 2（ShortcutsDialog前例あり）、Phase 3（D-17前例あり）

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM | OpenAI API仕様は複数クエリでクロス照合済みだがモデル名詳細は変動速い。Tcl/Tk根本原因はLOW〜MEDIUM(実機再現せず) |
| Features | MEDIUM | OpenAI API仕様はMEDIUM。原子的保存・OK/Apply/Cancel意味論は業界一般則としてMEDIUM |
| Architecture | HIGH | すべて実コード読解に基づく |
| Pitfalls | HIGH | 公式ドキュメント・既存コード・v1.8.0の実際の回帰事例で裏付け |

**Overall confidence:** MEDIUM〜HIGH

### Gaps to Address

- OpenAIモデルラインナップの陳腐化: 実装フェーズ開始時にGET /v1/modelsを実キーで確認すること
- PyMuPDF「暗号化済み+incremental+PDF_ENCRYPT_KEEP」の可否: 情報源間で食い違い、V190-REV-01実装時に実機確認
- Python 3.14 Tcl/Tk根本原因: STACKとPITFALLSで評価が一致しない。実行コンテキストの切り分けが必要
- 外部プロンプトファイルのApply一本化 vs Cancel復元: 未決定、Phase 2着手前に確定させる
- OpenAIモデル一覧のフィルタ方式: 未決定、Phase 5計画時に確定
- Document.authenticate()後の暗号化パラメータ取得API: 公式記述見つからず、実装上は影響低

## Sources

### Primary (HIGH confidence)
- PageFolio既存コードベース直接読解（file_ops.py・page_ops.py・ocr.py・ocr_providers/*・ocr_dialog.py・dialogs/*）
- .planning/notes/2026-08-10-v1.9.0-existing-feature-review.md
- .planning/PROJECT.md

### Secondary (MEDIUM confidence)
- OpenAI公式ドキュメント（developers.openai.com） — Chat Completions・画像入力形状・/v1/models
- Artifex公式ブログ — PDF_ENCRYPT_KEEP・incremental
- PyMuPDF公式ドキュメント（pymupdf.readthedocs.io）
- OpenAI Developer Community・Rate limits guide

### Tertiary (LOW confidence)
- CPython issue #125235 / python-build-standalone issue #913（Tcl/Tk根本原因候補、未再現）
- Foxit公式ドキュメント（他社横比較、一次情報限定的）

---
*Research completed: 2026-08-10*
*Ready for roadmap: yes*
