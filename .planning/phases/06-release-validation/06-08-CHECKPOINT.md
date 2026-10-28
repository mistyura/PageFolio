# 06-08 世代5の実行状況（2026-10-28）

- 案B承認 `W11-B-20261028` を反映。必須108行not-run、W11対象外2行not-run。Phase完了/出荷許可false。
- 配布文書の契約85件、文書反映後の単一全件2232 passed / 2 warnings / 607.00秒。`06-08-evidence/native-docs-20261028`。Phase04 21/21、Phase05 23/23を独立再検証済み。
- freeze65入力digest `ae08f9422ee0010bbc827720aae0c1873552d0dd51b63ddf4960baeba036658d`。実初回/再build各1回成功。最終EXE `66be5df663e333057c5c3cde02180857f930d2433e377f69c2838432d49a19d4`、tree `b1e55ca6efa3a7bafb4dec9ea9fa2c715dfca6f538ba906632058f912f575d85`。第三buildなし。
- 保護3名、起動時保持3条件、更新衝突/非衝突、X01〜X05外部条件成立。X04 write/replaceの初回終了時の画面保持・強制回収は観測のまま保持し正常終了passにしない。
- update処理終了直前0.948秒にfaultsを開始した進行上の逸脱により、共有t2-resultのupdate節が上書きされた。保存済みupdate原本とfaults原本の共通節一致を確認し、update節をそのまま合成した。元raw保持、`06-08-combined-t2-result.json`のmerge_provenanceに出典SHAを記録。再観測や推測値は使用していない。以降は完了確認後に次段階を起動した。
- ocr-single `18986e4dd7b341bd81d4a6d4b0da8afd`、W05b `af629ccbe3514294a7814e1de2e98463`成立。各同1POST完了、配布元不変、利用者通常終了、残存ownerなし。W05bは同確認HWND3867420への自動復帰を50ms観測と原文で照合。
- W05b初回 `31d4388e2cbb4f80944a015b67bc3234` は観測中の手動切替で不成立。原本SHA `4c356aa575b6aca7020cb436e0d3040d1df55c9eb3cf8fdd26aaac15afb14f5e` と補足回答を保持。自動復帰後10秒無操作の別runで確認した。製品/driver/期限/判定条件変更なし。
- `audit --preparation-only` exit0、required_pass0/required_not_run108/deferred2。接続準備を本受入passに転用していない。
- 台帳確定後の指定契約試験は192 passed / 1 warning / 49.22秒。`06-08-evidence/ready-contracts.xml`。現行151入力の単一全件は2232 passed / 2 warnings / 513.66秒 / exit0、前後入力不変。`06-08-evidence/native-ready-20261028`。品質参照更新後のbuild-only/preparation-only/allow-pendingも全てexit0。allow-pendingはstructural_only=true/task_ready=false。

次: 06-08の差分/証拠/SUMMARYを整理してから06-05→06-06本受入へ。既存dirty/index・旧世代原本を保持。CR-03修正はe13a00bに分離。保存したrawのCRLFと旧UAT末尾空行を変更せず、cr-at-eolを用いた検査で通常編集ファイルのwhitespace問題0を確認。
