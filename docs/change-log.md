# Schedule For SNS 変更記録

## 2026-05-01 22:55:01 JST

### 追加

- React/Viteのフロントエンド雛形を作成
- LISM CSSを導入
- Schedule For SNSの初期UIを作成
- 予約作成画面を作成
- 予約前確認モーダルを作成
- 予約一覧画面を作成
- 投稿履歴の並び替えを追加
  - 新しい順
  - 古い順
  - ステータス順
- 予約済み投稿の編集・削除UIを追加
- 失敗投稿から同じ本文で新規予約を作成する導線を追加
- 投稿分析画面を作成
- 設定画面を作成
- Threads再連携ダイアログを追加
- 休止中ダイアログを追加
- トライアル残り時間表示を追加
- 法務文書リンクを追加
- AWS SAMテンプレート雛形を作成
- Python Lambdaハンドラー雛形を作成
- DynamoDBテーブル定義案をSAMテンプレートへ追加
- DynamoDB Point-in-Time Recoveryを有効化する構成を追加

### 変更

- カレンダーに年・月選択を追加
- カレンダーの日付表示を1段横スクロール形式に調整
- モバイル表示時にサイドバーを上部ヘッダー型へ変更
- モバイル表示時にトライアル残り時間をヘッダーへ表示
- モバイル表示時のメニュー配置を調整

### 検証

- `npm run lint` 成功
- `npm run build` 成功
- Python Lambda雛形の構文チェック成功
- Vite開発サーバー起動確認

### 未解決・次回対応

- 携帯表示がまだ不自然なため、モバイルレイアウトを再調整する
- 多言語対応はまだUI文言の辞書化前
- Threads OAuth、Stripe Checkout、EventBridge Scheduler実処理は未実装
- Meta App Review用説明文・審査動画台本は画面実装後に作成する

## 2026-05-01 22:56:51 JST

### 変更

- モバイル表示のメニューをハンバーガーメニューに変更
- モバイル表示ではナビゲーションを初期状態で閉じるように変更
- ハンバーガーメニューを開いたときだけナビゲーションを表示するように変更
- カード内の長いテキストが横にはみ出さないように折り返しを調整
- 再連携ダイアログのボタンがモバイル幅でカードからはみ出さないように調整
- アプリ全体の横スクロール発生を抑制

### 未解決・次回確認

- 実機またはブラウザのモバイル幅で、ハンバーガーメニュー開閉と各カード幅を確認する

## 2026-05-01 23:02:04 JST

### 変更

- モバイルヘッダーでトライアル残り時間を2段目に移動
- 1段目はブランド名とハンバーガーメニュー、2段目はトライアル表示に分離
- モバイルヘッダー内でブランド名、トライアル表示、ハンバーガーが重ならないように調整

## 2026-05-01 23:02:58 JST

### 変更

- モバイルヘッダーを全体で2行構成に調整
- 1行目にS4Sロゴ、サービス名、ハンバーガーメニューを横揃え
- 2行目にトライアル残り時間を表示

## 2026-05-01 23:04:46 JST

### 追加

- AWSバックエンド環境設定ドキュメントを追加
- `.env.example` を追加
- `.gitignore` を追加
- `backend/samconfig.toml` を追加
- `backend/env/dev.example.json` を追加
- `backend/env/prod.example.json` を追加

### 内容

- AWSリージョンは `ap-northeast-1` を基本に設定
- SAMスタックを `schedule-for-sns-dev` と `schedule-for-sns-prod` に分離
- Amplifyは `dev` ブランチを開発、`main` ブランチを本番として扱う方針を記載
- DynamoDB運用ルール、IAM、環境変数、次の設定項目を整理
- `node_modules`、`dist`、`.env`、SAMビルド成果物、実値入り環境ファイルをgit管理対象外に設定

## 2026-05-01 23:07:36 JST

### 追加

- Stripe設定ドキュメントを追加

### 内容

- Product / Price設定手順を整理
- Checkout subscription modeと14日無料トライアルの設定方針を整理
- Customer Portalの扱いを整理
- Webhook endpointと購読イベントを整理
- Stripe Webhookの二重処理防止ルールを整理
- サブスクリプション状態ごとの予約可否を整理
- Stripeメール通知の扱いを整理
- dev/prodの環境変数を整理

## 2026-05-01 23:09:57 JST

### 追加

- Meta / Threads設定ドキュメントを追加

### 内容

- Threads APIで要求する最小スコープを整理
- Threads OAuth redirect URIの設定方針を整理
- OAuth認可URL、認可コード交換、長期トークンの扱いを整理
- 投稿APIと投稿分析APIの利用方針を整理
- Meta App Reviewの準備項目と審査動画の流れを整理
- テスター設定、レート制限、ログ方針、環境変数、チェックリストを整理

## 2026-05-01 23:15:04 JST

### 追加

- Amplify / Route 53設定ドキュメントを追加
- `amplify.yml` を追加

### 内容

- `s4s.aokigk.com` を正式URLとして整理
- Route 53の `aokigk.com` Hosted Zone確認手順を整理
- Amplify Hostingの `main` / `dev` ブランチ分離を整理
- Amplify build settingsを整理
- Amplify managed certificateを使ったカスタムドメイン設定手順を整理
- SPA rewrite設定を整理
- Amplify環境変数とMeta/Stripeへ反映するURLを整理
