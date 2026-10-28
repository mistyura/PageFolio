---
phase: 06-release-validation
document: uat-preparation
status: preparation-complete-acceptance-pending
created: 2026-10-24
---

# Phase 6 実機受入の準備カード（入口ごとの準備可否と手順）

本書は**準備手段と観測限界**の記録である。準備ができたこと、build が成功したこと、人手 pass、
Phase 完了は別の状態であり、本書のどの記述も受入合格・出荷承認を意味しない。実配布 EXE に対する
実接続・native modal・lock 成立は本書では未実証で、06-04-02 で別に実証する（下表「実EXEでの未実証点」）。

## 現行状態（06-04 世代4・2026-10-28）

CR-03修正後のv1.10.2。全件2083 passed、Phase04/05 fresh passed、新入力で初回/再build各1回成功、build-only exit0。
最終EXE 6a0bd182d0ab717f45ddf2f36fd23aaad8aacdc83c264843fbcaab40ced20d3d。保護3名・起動時保持3条件・更新衝突/非衝突・X01〜X05外部条件の記録は 06-04g4-t2-result.json。
X04 write/replaceは初回WM_CLOSE後12秒で終了せず、所有handleで回収した。追加guardがこれを一律失敗扱いして停止した原記録も保持。D19の画面維持仕様を確認し、未実施replace/X05のみ続行した。通知・次の終了操作の人手合否は未判定。
実EXEのocr-single/W05b接続2件は成立。W05bはChatGPTから同確認HWND10686146へ自動復帰し、いいえで処理維持、同1POST完了を利用者回答と50ms観測で照合。両runは利用者が通常終了し残存ownerなし。準備監査exit0（phase_complete=false/release_allowed=false）。sourceの「isolated OCR」確認画面が自動復帰したとの回答は診断証拠で、実EXEや本受入のpassには転記しない。110行not-run、Phase06未完了、出荷未承認。
以下の世代3停止は履歴。現在の再開は利用者の「出荷停止状態を解消して」に基づく。

## 過去の状態（06-04 世代3・2026-10-28）

**W05b接続実証で停止:** `06-CONNECTION-STOP-20261028.md`を優先する。世代3の実操作2runは記録済みだがW05b自動復帰は未実証。peer前後で同modal HWND6753582がある一方、実foregroundはChatGPT側PID18044。利用者補足は「自分で PageFolio に切り替えて確認した」。元回答を保持し、自動復帰成功の解釈を取り下げた。`peer_returned_to_modal=false`、準備監査exit1で06-05/06・出荷停止。次は`$gsd-debug phase06-w05b-manual-switch`、再試行しない。原因/製品関与を断定せず、チャット回答手順の影響を切り分ける。

**品質停止解除後の再開照合済み:** 最新正本は `.planning/debug/quality-gate-unblock.md`（resolved）と同証拠dirの単一全件2071 passed / 2 warnings / 480.86秒 / exit0。旧1846 passed / 1 failedと`06-04g3-QUALITY-STOP.md`は履歴のまま保持。今回の読取照合は`06-RESUME-CHECK-20261028.json`で、実build入力65/65・品質Python137/137・依存環境が一致し、build-only exit0・監査前後tree/hash/mtime不変、追加build不要。親の独立Phase04再検証はpassed、現行digestは`v4:sha256:b6d4189f833dd62188a4105334e54ad44c663753825eea431e072f1c4030a145`。本照合を人手passにしない。

- v1.10.1の初回/再buildがともに成功し、`audit --build-only` はexit 0。最終EXEは `9b3ebbce390c3b9f1752a97820a5ef81a0c39b7e148b93717b86bb47f9f5f73b`。配布元は直接起動しない。
- 保護3名のbuild前停止、更新/衝突時の保持、normal/corrupt/unreadableの起動時保持、X01〜X05の外部障害成立を新EXEで実測。生記録は `06-04g3-t2-result.json`。X04の通常終了不成立と所有PIDの強制回収は診断付き観測として保持し、人手passと扱わない。
- unreadableの初回試行は利用者の手動終了が介在。`06-04g3-STOP.json` と `06-04g3-t2-first-attempt.json` に原本と利用者原文を保持。操作を止める案内後の新runでは安定時生存・hash保持・通常終了・owner回収を確認した。旧試行はpassへ書き換えない。
- 接続事前照合は10項目成功（実EXE内蔵コード・隔離設定・loopbackモデル一覧）。`--check-routing-only` はEXEを起動せず、本接続・人手受入の代用ではない。
- ocr-single `0d73a0cdf5b8465f9970b3702c2653e7`とw05b-modal `cf52cf1df4db42a3b384db6f13a6c103`の実操作/原文を記録。両方同1POSTを完了したが、後者は自動復帰未実証。ocr-singleのprimary terminated/stop診断、W05bのprimary closedをそのまま保持。`--preparation-only` 合格前に06-05へ進まない。全110受入は世代3のnot-run、Phase未完了・出荷停止。
- rootは`C:/Users/shdwf/AppData/Local/Temp/pf06_t2_g3_unreadable_8433fc4ee5324234931fb80ac0f310d1`。sandbox不可視runも原本保持しpassにしない。現在は全ownerを回収済みで重複/再試行しない。原本copy/hashと補足は`06-CONNECTION-STOP-20261028-evidence/`。
- 旧世代16 runの参照不足は、入れ子の世代1証拠と`06-04-t2-result.json`原本（SHA256 `7f2590850e4b6937b9b12d83a3f33067861ade549c09b14334e77c80729ceb5a`）に全IDが存在することを確認し、下表へ履歴として補った。世代3へ昇格させず、接続不足によるpreparation-only未合格は維持する。

## 過去の状態（06-04 世代2 時点・現行EXEには適用しない）

世代2の元台帳は `06-04g2-preserved-20261028-06-BUILD-EVIDENCE.json` と `06-04g2-preserved-20261028-06-PROTECTION-EVIDENCE.json` に保持。以下の合格は当時のv1.10.0だけを対象とする。

| 項目 | 状態 |
|---|---|
| 検証支援ツール（`tests/release_uat_support.py`）・合成OCR（`tests/release_fake_ocr.py`） | 実装済み。単体試験で支援ロジックを検証（実配布EXEの証拠ではない） |
| 実配布EXE（v1.10.0 最終版） | **作成済み**（06-04-01 世代2: 初回/再 build 各 1 回、最終EXE sha256 `b3d4a07e…8c17`。`06-BUILD-EVIDENCE.json`。世代1の `f918bf76…da23` は superseded） |
| 保護 3 名の build 開始前停止・起動時保持・更新/衝突の保持（06-04-02 自動部分） | **実測済み**（`06-PROTECTION-EVIDENCE.json`、世代2の生記録 `06-04g2-t2-result.json`。世代1は `06-04-t2-result.json` に原本保持） |
| X01〜X05 の外部 lock/tmp/hash 成立（実EXE上） | **実測済み**（同上。通知・操作時点の人手観測は 06-05-02） |
| 実配布EXEへの fake OCR 接続（ocr-single）・native modal（w05b-modal） | **準備段階として実測・記録済み**（ocr-single = `cd4dc81a…`、w05b-modal = `9cea6581…`。`audit --preparation-only` は exit 0）。ただし受入ではない。実際のダブルクリック起動での前景挙動は 06-05-02 の W05b 本受入で人手確認する |
| W01〜W12・WR-01・X01〜X06 の人手 pass | **not-run**（06-05-02 / 06-06-01） |

世代2について: 製品修正（52258de ollama 選択時の送信先修正 / 7fb41a2 LLM 設定適用後のプロバイダ表示更新）の後に、build・保護・起動・更新・障害 X01〜X05 を新しい最終 EXE で取り直した。世代1（旧 EXE に対する記録）は `06-PROTECTION-EVIDENCE.json` の `previous_generations` に原文のまま保持し、本書の run 参照では `[世代1 superseded]` と表記する。w05b-modal は有効試行を 2 回得た。先の `release-uat-3dab246a0dd34f6eae066392a88ffd3a` は peer 後の前景が入力中の PowerShell のままで `peer_returned_to_modal=false`（原因未確定）となり準備監査が不成立だったため、利用者の判断で同じ未変更のシナリオを再実行した `release-uat-9cea65811a8c4db998d9dfcf54e849e6` を準備証拠として採用した。3dab246a… は `06-PROTECTION-EVIDENCE.json` の `failed_connection_attempts` に superseded として保持している（破棄しない）。また無効試行 `release-uat-7e4629e4f555465183a070c1efdbfb6e`（クリップボード誤貼り付けで中断）も同所に保持している。世代1で不成立だった接続実証 2 回（`release-uat-c75a19aa09b84f1788c0dee965915dd7` / `release-uat-034578b2c4b94c2aae9fa70afe620d25`）は成立と記録せず、理由を同 JSON に残す。

run 参照（`run-ref: <32桁hex>` 形式の行）は下記の生成ブロックに置く。06-PROTECTION-EVIDENCE.json の
`run_id` と双方向に一致しない場合、`audit --preparation-only` は不合格になる。ブロックは
`06-04-drivers/assemble_protection.py` が証拠 JSON から再生成する（手で編集しない）。接続実証 2 件は
利用者の回答後に追加される。

## run 参照（06-04-02）

<!-- run-refs:start (assemble_protection.py が生成。手で編集しない) -->

| run-ref | 用途 |
|---|---|
| run-ref: 3a60a10440724b72a6c5e6274cf531c5 | [世代2 superseded] 保護停止 ocr_custom_prompt.md |
| run-ref: 222e3a0876394942a376f7f1dcb7fcdf | [世代2 superseded] 保護停止 pagefolio_settings.json |
| run-ref: c6f94beab4e64cf596209cc22a6b656b | [世代2 superseded] 保護停止 ocr_summary_prompt.md |
| run-ref: eed85c78bb854616b87140ee8d57ae6f | [世代2 superseded] 起動時保持 normal |
| run-ref: 5021b5ccbaf348bb96411745ed4f5630 | [世代2 superseded] 起動時保持 corrupt |
| run-ref: 27332ac0db33443dbf48cc8b53237baa | [世代2 superseded] 起動時保持 unreadable |
| run-ref: 4b2a6810ce074698b2a83c7264c961b2 | [世代2 superseded] 更新 collision old(initial run tree) |
| run-ref: baf05b8dc25a41078ad50ae4fd6e7d0a | [世代2 superseded] 更新 collision new(final) |
| run-ref: f7315188f0954ecabc9c8d5ff2447af3 | [世代2 superseded] 更新 no_collision old(initial run tree) |
| run-ref: 407c0a66363649389729d81b22ba79bb | [世代2 superseded] 更新 no_collision new(final) |
| run-ref: cd4dc81af699415abcb3be8ad2cb44aa | [世代2 superseded] 接続実証 ocr-single |
| run-ref: 9cea65811a8c4db998d9dfcf54e849e6 | [世代2 superseded] 接続実証 w05b-modal |
| run-ref: 4ef38ba7f7df48bda95d3491925bb026 | [世代2 superseded] 障害 X01 |
| run-ref: c60fc8eba2a449a18df2fbc6bb105a50 | [世代2 superseded] 障害 X02 |
| run-ref: cb067afb49e04824b36c8e4a0e49c5a2 | [世代2 superseded] 障害 X03 |
| run-ref: bbcfc78b50294e0e86d15010ea69f840 | [世代2 superseded] 障害 X04-write |
| run-ref: be21694e38a443bf8d229414d8957e69 | [世代2 superseded] 障害 X04-replace |
| run-ref: c25f8a7004794159810f91752d1898cc | [世代2 superseded] 障害 X05 |
| run-ref: 25f54397fd024c9e88e0e1f6f17fead7 | [世代3 superseded] 保護停止 ocr_custom_prompt.md |
| run-ref: 1204059f0d3142a183b10c384ff1d96f | [世代3 superseded] 保護停止 pagefolio_settings.json |
| run-ref: 2e0441fcc32a46e4ba321e0a33037966 | [世代3 superseded] 保護停止 ocr_summary_prompt.md |
| run-ref: a595886789f040579d5c3f241623b745 | [世代3 superseded] 起動時保持 normal |
| run-ref: a0ca066b3aa54cb28b6f38301efffc95 | [世代3 superseded] 起動時保持 corrupt |
| run-ref: 58ff032e11a841c6a59a7a1c0616a60d | [世代3 superseded] 起動時保持 unreadable |
| run-ref: e02363d89ba84303b29ff60095f77f7d | [世代3 superseded] 更新 collision old(initial run tree) |
| run-ref: db35587c8f33453e9a51878d7e2cb212 | [世代3 superseded] 更新 collision new(final) |
| run-ref: 5654df8b2e7440cd947501059a95707f | [世代3 superseded] 更新 no_collision old(initial run tree) |
| run-ref: 37ec71257ac448bd8e87eaab1ba4a668 | [世代3 superseded] 更新 no_collision new(final) |
| run-ref: 0d73a0cdf5b8465f9970b3702c2653e7 | [世代3 superseded] 接続実証 ocr-single |
| run-ref: cf52cf1df4db42a3b384db6f13a6c103 | [世代3 superseded] 接続実証 w05b-modal |
| run-ref: a7614753199f4b4e98b34fe2e595d25b | [世代3 superseded] 障害 X01 |
| run-ref: c89865557c764799a7dfd9fd8f3f1e61 | [世代3 superseded] 障害 X02 |
| run-ref: f1ca0ebc157a420d9b5261893f5f69a9 | [世代3 superseded] 障害 X03 |
| run-ref: fe3add65702a40c98798a0970e09f58c | [世代3 superseded] 障害 X04-write |
| run-ref: 56338ac54a164624a41e93c16e6682b1 | [世代3 superseded] 障害 X04-replace |
| run-ref: 387b095a12db4f4e82d299061686e5c6 | [世代3 superseded] 障害 X05 |
| run-ref: b26038b9f2b8416c973999963d00ae34 | 保護停止 ocr_custom_prompt.md |
| run-ref: a629a1461d59476194d2e4cbe827fd73 | 保護停止 pagefolio_settings.json |
| run-ref: 6c5d3d9975de4f1cbe66da9ea0ec8ee8 | 保護停止 ocr_summary_prompt.md |
| run-ref: d5920b826931450790e37505c22ef9a8 | 起動時保持 normal |
| run-ref: e5482609351a4315911f49fcf32c9551 | 起動時保持 corrupt |
| run-ref: e4cd696760d144a1b6919d216a9caf3f | 起動時保持 unreadable |
| run-ref: 587de1d767ae48d08249c15e31351acd | 更新 collision old(initial run tree) |
| run-ref: 72430bf00e444418aad97b98a86a9269 | 更新 collision new(final) |
| run-ref: 92d5de34749f4021b17de797023ebb52 | 更新 no_collision old(initial run tree) |
| run-ref: f97103c7354440659c886e604f6877d2 | 更新 no_collision new(final) |
| run-ref: 6dd0b4d0997b4b8eb0ccb665ab067123 | 接続実証 ocr-single |
| run-ref: 1125b7a0cfad4a4ab00a08b522e5aab1 | 接続実証 w05b-modal |
| run-ref: d390155a909548a0b6173ea8c36af9e3 | 障害 X01 |
| run-ref: 07ac51ea8e0e4a9694cc2a4396272e14 | 障害 X02 |
| run-ref: 07375ba737604156b77ba5fa6f0daf6b | 障害 X03 |
| run-ref: 8729b769b9ab45648a63714b79b1fce7 | 障害 X04-write |
| run-ref: 9dde180c8c62403eac3e42dd6f274e12 | 障害 X04-replace |
| run-ref: 86e97d624b3147bca01e0207f0fcfe36 | 障害 X05 |
| run-ref: 034da46ced8d4c02b001c1350ad4cfbf | 過去世代を含む原記録（現行受入への昇格なし） |
| run-ref: 5787245f4ffc41ad8142f14f7fb7eebd | 過去世代を含む原記録（現行受入への昇格なし） |
| run-ref: f597309fe4ac4f958994fc9000bef612 | 過去世代を含む原記録（現行受入への昇格なし） |
| run-ref: 0c289c364a25402e9aa514b5be8fe2c2 | 過去世代を含む原記録（現行受入への昇格なし） |
| run-ref: f7a78d95a4cc442b815d8e79c001d488 | 過去世代を含む原記録（現行受入への昇格なし） |
| run-ref: 2b7a53f82f014af294721a2c96ee6f2a | 過去世代を含む原記録（現行受入への昇格なし） |
| run-ref: 65468902bf4f4efeb4f880f83f302acc | 過去世代を含む原記録（現行受入への昇格なし） |
| run-ref: eea9ec4a38e044f989f27d52a9a185de | 過去世代を含む原記録（現行受入への昇格なし） |
| run-ref: 64058e97276540f38e6ae5c6f4052f5d | 過去世代を含む原記録（現行受入への昇格なし） |
| run-ref: db2f16a9041546caaf9bc9d5eb015683 | 過去世代を含む原記録（現行受入への昇格なし） |
| run-ref: 2354dd0e4c934de6a44fc624f62e01da | 過去世代を含む原記録（現行受入への昇格なし） |
| run-ref: ca66fbc00cdf49958d7d0f801949d934 | 過去世代を含む原記録（現行受入への昇格なし） |
| run-ref: bbe088a0fd8344a688d81ec4eaa66d89 | 過去世代を含む原記録（現行受入への昇格なし） |
| run-ref: efbcd9bebc234e5ba8b4029d2d1a8b97 | 過去世代を含む原記録（現行受入への昇格なし） |
| run-ref: d04fea5666194452b2cd65aa4a5ce20e | 過去世代を含む原記録（現行受入への昇格なし） |
| run-ref: 2680bdf5bd9943cbb99c3a7e63e78e97 | 過去世代を含む原記録（現行受入への昇格なし） |
| run-ref: d04061c65a42406c90736c4a3e183368 | 過去世代を含む原記録（現行受入への昇格なし） |

<!-- run-refs:end -->

## 共通の約束（D-13〜D-16・移管条件）

- 配布元（`dist/` 配下の版付き出力）は**直接起動しない**。`prepare` が検証済み配布 tree を `.planning/tmp/release-uat-<run>/dist` へ
  完全 copy し、同梱 `release-report.json` の全名・全 hash と照合してから使う。copy 後も配布元の全 tree hash を再照合する。
- 配布 manifest に属する不変 tree と、合成設定・2prompt 等の**明示 fixture overlay**は別 manifest。overlay 以外の差分・
  未宣言ファイルがあれば `start` を拒否する。アプリの正当な明示保存（overlay 変化）と、起動による無断変更は別時点の snapshot で判断する。
- 製品を import/patch しない。EXE へ nonce・試験引数を渡さず、そのまま起動する。
- 固定 production namespace（`Local\PageFolio.Startup.Owner` / `.State`）に既存 owner があれば**何も送らず停止**する（読取 preflight）。
- 回収は記録した PID + 生成時刻 + image path を再照合してから行い、通常終了（WM_CLOSE）を先に試す。残る場合は診断を
  `evidence/stop-diagnostics-<pid>.json` に保存してから所有 handle で終了する。名前による一括 kill は行わない。
- 証拠種別は `production-exe` / `python-real` / `fault-injection` / `unit` / `manual`。`unit` と `fault-injection` を
  実配布 EXE の人手 pass に昇格できない。回答は「ケースID＋短い観察結果」で、環境・時刻・PID・session・権限・入口・hash は実行担当が補う。
- 画面記録は通知/DPI/異常を中心にする（D-16）。入力先・foreground・時間上限は画面記録だけで実証とみなさない。
- 製品コード・build 依存・収集設定が変われば、`resume_contract` に従い 06-04 の初回/再 build・保護・接続と全 production-exe 行を新世代で取り直す。

## コマンド

すべて `.venv/Scripts/python.exe tests/release_uat_support.py <subcommand>`。

| subcommand | 役割 |
|---|---|
| `prepare --distribution <版付きdir> --case <ID> [--pdf ocr-one-page] [--pdf edit-three-page]` | 完全 copy・hash 固定・run manifest・合成 PDF |
| `serve-ocr --run <run> [--mode hold]` | loopback の合成 OCR を起動し、隔離 copy の設定へ接続先を書く（待機解放は `<run>/release.flag` を作る） |
| `fault --run <run> --kind missing\|corrupt\|unreadable\|save-write\|save-replace` | 設定障害を外部 handle / tmp 衝突で保持（解放は `<run>/release-fault.flag`）。成立しなければ exit 3（not-run） |
| `start --run <run>` | 所有 process として起動し、PID・生成時刻・session・foreground を保存 |
| `peer --run <run> [--with-run <別run>]` | 一次 owner の生存・同一性確認後に 2 つ目を起動（混在確認） |
| `inspect --run <run>` | PID/生成時刻/window/foreground/tree/原本の外部観測（`evidence/inspect-NNN.json`） |
| `stop --run <run>` | 同一性再照合後の回収 |
| `resume-check --phase-dir <dir> --run <run>` | 中断状態と現状の照合（同一なら未実施から続行、差分は新世代） |
| `audit --phase-dir <dir> <モード>` | 読取専用の証拠監査（下記） |

### audit のモード（相互排他・どれも台帳を書き換えず、成功しても `phase_complete=false` / `release_allowed=false`）

| モード | 使う担当 | 検査 |
|---|---|---|
| `--allow-pending` | 06-05/06-06-01 の途中記録 | 構造のみ。未実施を許容するが task の done は満たさない |
| `--require-pass ID,ID,...` | 06-05-02 / 06-06-01 の完了 | 指定 ID の全 subrow に実測根拠付き pass。空指定・未知 ID・宣言不足・行欠落・回答不足・hash 不一致・not-run/fail は nonzero |
| `--build-only` | 06-04-01 | 06-BUILD-EVIDENCE.json の初回/再 build の異なる 2 run、記録 output-root の実 tree/hash/report、保護名不在。build を呼ばず何も変えない |
| `--preparation-only` | 06-04-02 | 保護 3 名・起動・更新/衝突の前後 hash、1page 画像 OCR 接続と利用者回答、native modal、X01〜X05 の障害成立 |
| `--for-handoff` | 06-06-02 | 全必須 W/WR-01/X と build/保護/版/品質の一致、Phase4 鮮度、未解除事項の保持。親 4 ゲートだけ pending を許容 |
| （指定なし） | 親 orchestrator | 親 4 ゲートの実走結果反映後の最終監査。pending/not-run/stale/根拠なし/対象不一致は nonzero |

## 入口ごとの準備可否

| 入口 | 準備手段 | 準備可否（06-03 時点） | 観測限界・注意 |
|---|---|---|---|
| Python 直接 script / module / relocated | 既存 harness `tests/test_startup_windows.py --uat`（start/peer/inspect/stop。`--entry script\|module\|relocated`） | 既存手段を利用（本ツールは変更しない） | 本ツールは Python 入口を起動しない。W12a は既存 harness の証拠と人手照合 |
| 実配布 EXE（final-release-candidate） | `prepare` → `start` → `peer`/`inspect` → `stop` | **ツール準備のみ**。実 EXE は 06-04 | EXE 内蔵の Python/Tk 版は同梱 report の欄に、観測者の Python/Tk は別欄。UAC 前後は process の elevated/session/生成時刻で同一性を確認 |
| 実 EXE ↔ 06-01 tracer 実 EXE（W12b） | `prepare --role technical-tracer-real-exe` を別 run で作り、`peer --with-run` | 来歴（run ID・source manifest・実版・EXE hash）を 06-01 の report から読めた場合だけ | tracer は「公式旧版」でも「最終 EXE 受入済み」でもない。来歴を検証できなければ W12b の該当 subrow は not-run |
| 実 EXE ↔ Python 入口 | 一次/二次を `start`/`peer` と既存 harness で組み合わせ | 06-05-02 で実施 | 許可 API の戻りと実 foreground は別に記録する |
| Python 故障注入（W07 slowready/busy、W08 初期化死亡・古い mapping・旧 worker 等） | 既存 Python harness の fault 経路で生の証拠を作り、人が照合 | 既存手段を利用 | **実 EXE に同じ注入は届かない**（frozen に hook がない）。証拠種別は `fault-injection` のまま、実 EXE の共通挙動は別 subrow |
| fake OCR（W04 / W05b / 接続実証） | `serve-ocr`（`FakeOcrServer`）＋ `prepare --pdf ocr-one-page` | ツール準備のみ。実 EXE 接続は 06-04-02 | 下記「fake OCR」参照 |
| 設定障害 X01〜X05 | `fault`（外部 CreateFileW handle / 排他 tmp 衝突）＋ overlay | ツール準備のみ。実 EXE 上の成立確認は 06-04-02 | 下記「設定障害」参照。noconsole EXE の DEBUG ログには依存しない |
| W10 medium↔elevated | 人が実 UAC を操作。背景 helper の Start-Process は `-WindowStyle Hidden` | 06-06-01 | `inspect` が process の elevated/session/生成時刻を外部記録。アカウント新設・資格情報取得・mock は行わない |
| W11 既存別 session | 準備不能（別アカウント） | **not-run のまま** | 準備継続か再計画かは親が利用者に判断を求める。免除・合格扱いはしない |
| W09 実 DPI 100/150/200% | 人が Windows 設定を変更 | 06-06-01 | 通知/閉鎖領域は画面記録＋ログ |
| Phase 5 H01〜H14・意味評価 2 件 | 既存正本（05-UAT.md）の対象 hash/環境/回答を参照 | 無理由に再実施しない | 実 EXE 固有の受入は X01〜X06 として新規 |

## fake OCR（R06-07 / R06-08）

- 127.0.0.1 の空き port 以外に listen しない（`0.0.0.0` 等は構築時に拒否）。クライアント実装を持たず外部へ転送しない。
- 形状は既存 `OllamaProvider` が使うものだけ: `GET /v1/models` → `data[].id`（モデル名 `pagefolio-uat-fixture`）、
  `POST /v1/chat/completions` → `choices[0].message.content` と `finish_reason`。
- 接続は既存 Ollama 設定のみ。隔離 copy の `pagefolio_settings.json` に `ocr_provider=ollama`、`ollama_url`、
  `ollama_model=pagefolio-uat-fixture`、`ocr_concurrency=1`、`ocr_fallback_enabled=false` を置く（実利用 directory には書かない）。
  サマリ実行の設定は無く、人がサマリ操作をしないことをカードで確認する（`summary_executed=false` を記録）。
- OCR 接続 / W04 / W05b は**埋込文字のない 1page 画像 PDF**（`ocr-one-page`）・対象 1page・並列 1 で POST 1 件を期待する。
  EXE 側は UI で対象 1page を選び、必要なら force OCR を指定する。W03 用の 3page 編集 PDF（`edit-three-page`）とは別 fixture で、
  ページ数を request 数へ投影しない。
- 受理する画像は 1 ページ分に限る: PNG であること、対象ページ数を超える別画像は拒否（409）、事前に描画 hash を登録した場合は登録外を拒否。
  画像本体は保存せず SHA-256 だけを記録する。**限界:** 描画結果の hash は EXE 内蔵 PyMuPDF に依存して事前に確定できないため、
  既定では「最初の 1 画像を p1 に束縛」する方式で、合成入力であることの暗号学的証明ではない（loopback 限定・外部転送なしで担保）。
- 記録: request ID・attempt ID（画像 hash 先頭 12 桁＋連番）・画像 hash・page ID・received/released/completed/expired 時刻を
  `evidence/fake-ocr-events.jsonl` に追記する。再送が起きても元の attempt は消さず `retransmissions` に残す。
  通常ケースが 1 POST でなければ `single_attempt_ok` は未合格を返す。
- 待機（hold）は既定 90 秒で、provider timeout（既定 120 秒）より短い。上限到達は `expired` として可視化し、通常ケースでは
  429/5xx を返さない（error モードも 429/5xx を拒否）。製品の 5 秒/10 秒/15.5 秒契約は変更しない。
- **W05b:** fake OCR を hold したまま、利用者が OCRDialog の「閉じる」を押して既存 `_on_close` → `askyesno(parent=self)` を表示する。
  modal 表示中に `peer` を起動して同じ native modal へ戻ることを確認し、「いいえ」を選んで OCRDialog・処理・入力を維持してから
  `release.flag` で同じ request を解放する。通信エラー経由の modal は仮定しない。Python 側も同じ実 UI 経路で準備検証し、
  **06-04 で未改変 EXE の成立を確認してから**カードを使う。
- 接続実証（`purpose=connection-preparation`）は W04 本受入の回答・pass へ転記しない（`audit --preparation-only` が拒否）。

## 設定障害（R06-09）

| 障害 | 作り方（合成 JSON / 隔離 copy のみ） | 成立の外部観測 |
|---|---|---|
| X01 missing | 設定ファイルを置かない（overlay で不存在を宣言） | 起動安定時まで不存在・警告なし。終了時の正当な window 保存による作成は失敗としない（別時点で判断） |
| X02 corrupt | 閉じていない不正 JSON bytes を overlay で配置 | 不正 JSON であること、原本 hash の前後一致（終了後も保持） |
| X03 unreadable | 観測側が CreateFileW（共有なし）で外部 handle を保持 | 同等の open が `ERROR_SHARING_VIOLATION(32)` で拒否される probe、holder の PID + 生成時刻 + access/share flags、時点 |
| X04 save-write | 同名 `.tmp` を排他的に先置きし `open("x")` の衝突を作る | 衝突の probe、tmp の存在/所有/内容、元 hash 不変、操作・通知の時点 |
| X04 save-replace | 読取/書込は共有・delete 共有なしの外部 handle | DELETE access の open が 32 で拒否・READ は成功する probe、元 hash 不変、所有 tmp の消去、時点 |
| X05 | X03/X04 の保持条件下の FIFO・再構築・終了 D19/D20 | 10 秒 FIFO・再構築残時間・終了 No→初回失敗→次回終了・unreadable 保存抑止を操作と通知の時点で記録 |

- tmp 衝突は**書込開始前の失敗**であり「書込途中失敗」とは呼ばない。内部書込途中の cleanup は既存 Python 障害注入が別の証拠種別で保持する。
- write と replace の失敗は**同じ通知文**になるため、通知文だけから原因を断定しない。外部 lock・tmp・元 hash・操作時点の組で判定する。
- 必要な外部観測が得られなければ `NotEstablished`（`fault` は exit 3）で **not-run** とし、準備を停止する。実利用 directory の ACL・製品コードは変更しない。
- Python 側の単体確認として、製品の `_load_settings_result` / `_save_settings` が上記の各障害を想定どおり（missing / corrupt / unreadable、
  保存失敗で原本不変）に扱うことを `TestSettingsFaultPreparation` で確認している（EXE の成功ではない）。

## 実EXEでの未実証点（06-04-02 以降で実証）

1. 未改変の実配布 EXE が、既存 Ollama 設定を通じて loopback fake OCR へ接続し、待機→peer 復帰→同じ page/attempt の解放→合成結果表示に到達すること。
2. W05b の hold 中の OCRDialog 閉じる確認が実 EXE で native modal を出し、peer 後に同じ modal へ戻れること。
3. X01〜X05 の外部 lock / tmp 衝突が実 EXE の設定読込・保存で想定どおり成立すること（成立しなければ not-run）。
4. 保護 3 名（設定・OCR/サマリ prompt）を置いた output-root で build が開始前に停止し、起動/更新で無断変更されないこと。
5. 実 EXE の foreground / 入力先 / 時間上限（人手と外部観測）。画面記録だけでは実証にならない。

## 証拠 schema（audit の入力・正本）

担当 task が次の形で書く。いずれも UTF-8・LF。fixture JSON（`tests/test_release_uat_support.py` 内）は本番台帳へコピーしない。

### 06-BUILD-EVIDENCE.json（06-04-01）

```
version: "v1.10.0"（APP_VERSION と一致）, release_allowed: false, uat_status: "not-run"
final_release:
  output_root, final_dir（実際に使った出力先。dist を決め打ちしない）
  exe_sha256, tree_sha256, input_manifest_sha256, bundled_sha256{サンプル2・はじめに.md・docs/CONFIGURATION.md}
  runs[2]: role="final-release", order="initial"|"rebuild", run_id, cli_argv, pyinstaller_exit=0,
           pyinstaller_executed=true, report_path, report_sha256, input_manifest_sha256, tree_sha256
           （tracer は role="final-release" を付けず tracer=true。2 回に数えない）
```
tree_sha256 は `walk_tree` の files/dirs の canonical JSON の SHA-256（`release_uat_support.tree_sha`）。
initial の tree は `.release-history/<rebuild の run_id>/` に保持されている必要がある。

### 06-PROTECTION-EVIDENCE.json（06-04-02）

`build_ref{final_run_id, exe_sha256}` / `protection_stop[3名: name, run_id, builder_started=false, exit_code!=0, before, after]` /
`launch.cases[{name, run_id, binary_sha256, hash_before, hash_stable, hash_after_exit}]` /
`update{collision{stopped_before_choice, old_before/after, new_before/after}, no_collision{copied_hash_match, old_preserved}}` /
`connection[{purpose="connection-preparation", kind="ocr-single"|"w05b-modal", run_id, binary_sha256, user_answer, observed_at, server{...}}]`
（`build_connection_entry` が組み立てる。w05b-modal は modal_shown / peer_returned_to_modal / answered_no / same_request_completed も必須）/
`faults{X01..X05: {established, method, run_id, binary_sha256, observed_at, observation{...}}}`。
本書の `run-ref:` 行とこの JSON の全 `run_id` が双方向に一致する。

### 06-MANUAL-EVIDENCE.json（06-05-01 で宣言、06-05-02/06-06-01 で記入）

`cases[{id, subrows[{subrow, entry, condition, evidence_kind, status(not-run|pass|fail|blocked), required_observations[], observations{}, answer, run_id, observed_at, environment{os, elevated, session_id,...}, binary_sha256, input_manifest_sha256, superseded_by?, supersede_reason?}]}]`。
pass の条件: 回答にケース ID、必須観測がすべて非空、`production-exe` の入口は `evidence_kind=production-exe` かつ `binary_sha256` が最終 EXE と一致、
Python 行は `input_manifest_sha256` が現行 build と一致、`unit` は不可。W12b は `subject{role=final-release-candidate, binary_sha256, version}` と
`peer{role=technical-tracer-real-exe|same-version-copy|python-entry, ...}` を持つ（tracer peer は別 hash・別版・来歴 `provenance{run_id, source_manifest_sha256}` 必須。
同版 copy は別版と主張できない）。宣言下限: W01(normal/zoomed)、W02(settings/thumb/preview)、W12a(9 行)、W12b(subject)、W12a 以外は実 EXE 入口の行を最低 1 つ。
中断/修正後は `supersede_rows` で元 pass を残したまま `superseded_by`/理由を追記し、新世代の not-run 行を作る。

### 06-EVIDENCE.json / 06-RELEASE-GATE.md（06-06-02 / 親）

06-EVIDENCE.json: `inputs{exe_sha256, tree_sha256, version, input_manifest_sha256, ...}` / `quality{ruff_check, ruff_format, ast, pytest{exit, passed, failed=0, errors=0, crashed=false, excluded=false, single_process=true, log_sha256}}` /
`phase4{fresh, covered_digest, current_digest}` / `unresolved[{id, status, evaluation, evidence?, approval?}]`（DEP-05-REGRESSION・owner_missing・notice-foreground-mismatch・tcl-warning・edge-unclassified を保持）。
06-RELEASE-GATE.md: 本文中の ```` ```json release-gate ```` ブロックに `parent_gates[4: code-review, secure-phase, validate-phase, verification]`
（pending は owner/command/expected_report 必須、pass は report{path, sha256, exit, at, verdict, target_inputs_sha256}）/ `release_conditions[]` /
`threats[T-06-01..14: id, severity, status(mitigated|open|unevaluated)]` / `nyquist{ran, passed}`。
引渡し監査では親 4 ゲートの pending と high 脅威の未評価を許容し、既知の open・fail は許容しない。最終監査はすべて根拠付きを要求する。
