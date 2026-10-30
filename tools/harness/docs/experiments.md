# 로컬 실험 실행·기록·비교

반복별 원본의 독립성·실제 명령·입력 연결의 상세 판정은 [검증 무결성](verification-integrity.md)을 따른다.

실험은 질문에 답하는 측정이며 코드 검사의 통과와 다르다. 표준 라이브러리만으로 작은 로컬 실험을 재현한다.
MLflow/DVC·서버·클라우드 계정·자동 모델 호출을 설치하지 않는다.
[MLflow Tracking](https://mlflow.org/docs/latest/ml/tracking/)의 실행별 파라미터·코드·지표·산출물 기록과
[DVC 실험 관리](https://doc.dvc.org/user-guide/experiment-management)의 조건을 고정한 비교 개념을 필요한 범위로 재구현했다.
그 도구들과의 저장 형식 호환이나 기능 동등성을 주장하지 않는다.

## 실행 전 프로토콜

레포 안의 JSON 파일에 다음을 기록한다. JSON을 택해 명령 인자·중첩 지표·타입을 CLI와 동일하게 명확히 남긴다.
프로젝트에 따라 docs/projects/<이름>/experiments/ 또는 작업 자료 폴더에 둔다.

```json
{
  "version": 1,
  "question": "같은 입력에서 후보가 정확도 하한을 유지하면서 지연을 줄이는가?",
  "population": "고정한 작은 입력 세트; 운영 전체를 대표하지 않음",
  "limitations": "로컬 측정이며 외부 서비스 변동·통계적 유의성은 평가하지 않음",
  "evaluation_type": "author_pilot",
  "inputs": ["data/evaluation.json"],
  "baseline": "baseline",
  "seeds": [11, 23, 37],
  "timeout": 30,
  "budget_seconds": 180,
  "max_output_bytes": 1048576,
  "metrics": {
    "accuracy": {"unit": "ratio", "direction": "maximize", "minimum": 0.95, "maximum": 1},
    "latency": {"unit": "ms", "direction": "minimize", "minimum": 0}
  },
  "variants": {
    "baseline": {"parameters": {"mode": "baseline"}, "command": ["{python}", "measure.py", "--mode", "baseline", "--seed", "{seed}", "--output", "{metrics}"]},
    "candidate": {"parameters": {"mode": "candidate"}, "command": ["{python}", "measure.py", "--mode", "candidate", "--seed", "{seed}", "--output", "{metrics}"]}
  }
}
```

これは形式の例であり data/measure.py やサービスを自動生成しない。実際にレビューした測定コードを用意する。
parametersは宣言記録で、勝手にCLIや環境変数へ注入しない。commandの実引数と一致していることをレビューする。
seedは重複のない整数1〜20個。単一の決定的測定なら1個でよい。回数を増やして最良値を選ぶための上限ではない。
timeoutは各試行最大3600秒、budget_secondsは1候補全体最大7200秒、出力上限は最大64 MiB。
期限切れの後続試行も not_run として残す。プロセス生成・終了処理のOS待ち時間は期限を少し超える場合がある。

evaluation_typeは fixture（既知の合成例）、author_pilot（作成者が実作業で確認）、agent_benchmark（別途設計した比較）を区別する。
このラベル自体はブラインド評価・独立性・母集団の妥当性を証明しない。

## 測定コマンドの出力

`{python}`は現在のPython、`{seed}`・`{trial}`は宣言した試行、`{metrics}`は毎回新しい絶対ファイルパス、
`{output_dir}`は同じ試行の保存場所に置換する。cwdはレポルート。shell展開はしない。
命令そのものは信頼したローカルコードであり、任意コード実行のsandboxではない。

測定コードは指定された metrics ファイルへ次のように書く。

```json
{"metrics":{"accuracy":{"value":0.98,"unit":"ratio"},"latency":{"value":12.5,"unit":"ms"}}}
```

欠けた/追加の指標、単位違い、非有限数、古いファイル、終了失敗、出力制限、期限超過は成功にしない。
全試行が品質上下限を満たさなければ run は failed。測定がソースを変えたら stale とする。
乱数seedが実際にライブラリまで伝わるか、計測コードが正しいか、条件にリークがないかは別途レビューする。

## 実行と比較

```sh
python3 tools/harness/run.py experiment run docs/projects/demo/experiments/search.json --variant baseline
python3 tools/harness/run.py experiment run docs/projects/demo/experiments/search.json --variant candidate
python3 tools/harness/run.py experiment compare .runtime/experiments/基準線ID/report.json .runtime/experiments/候補ID/report.json
```

結果は .runtime/experiments/<ID>/report.json と試行別 output.log/metrics.json に残る。
プロトコル全体・入力ハッシュ・ソース状態・Python/OS・環境ハッシュ・実引数・cwd・終了コード・所要時間・全試行・原本ハッシュを記録する。
環境変数の値は保存しない。原本ログにはアプリの出力が含まれるので合成データを使い、外部へ自動送信しない。

集計は試行総数、passed/failed/not_runと、通過試行の平均・中央値・最小・最大・件数を分ける。
失敗したrunから「成功した一回だけ」を抜き出して比較しない。欠測を0で補完しない。
比較には同じプロトコル・入力・seed構成・環境と正しい基準線順序が必要で、原本と集計も再確認する。
コードが違う候補は実行前に variant.source_paths の相対パターンへ許容する変更だけ宣言する。
宣言外のソース差がある比較は拒否する。全レポを `**` で許容して条件差を隠さない。

比較の improvement は maximizeなら候補−基準線、minimizeなら基準線−候補で、正値が宣言した方向への改善を表す。
これは記述統計であり有意差検定・優越性・本番品質保証ではない。品質と費用のトレードオフは解釈文書に残す。
runを [作業証拠](completion.md) のexperiment型に、結論/比較条件/比較報告へのリンクをartifact型に接続する。

## 対応しない範囲

外部DB・モデル・GPU状態の自動固定、大規模分散実験、適応的探索、すべてのOSでの子孫プロセス終了、
有料APIの実予算制御、使用量の推測は実装していない。commandがネットワークを使うなら既存の実行権限・予算に従う。
大規模化が必要になれば同じプロトコル項目を保って専用ツールへ接続する。今の汎用ハネスへ先回りで追加依存を増やさない。
