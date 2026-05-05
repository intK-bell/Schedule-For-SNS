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

## 2026-05-05 JST

### 追加
Threads OAuthログインを実装  
/auth/threads/start で認可URLへリダイレクト  
/auth/threads/callback で認可コードをアクセストークンへ交換  
Threads user_id取得処理を追加  

HttpOnly Cookieによるセッション管理を実装  
ログイン後に元の画面へ戻る return_to 制御を追加（local/dev/prod対応）  
ログアウトAPI /auth/logout を実装  

フロントエンドにログイン状態判定（/me）を追加  
フロントエンドにログアウトボタンを追加  

Amplify環境変数に VITE_API_BASE_URL を追加  
ローカル環境（localhost）でのログインフローを対応  

DynamoDB SessionsTable を追加  
session_id をキーとしたセッション管理  
TTL（expires_at）設定  
Point-in-Time Recovery有効化  

ログイン時に session_id → threads_user_id をDynamoDBへ保存  
/me APIをDynamoDB参照に変更し、本物の認証判定を実装  
ログアウト時にDynamoDBからセッション削除処理を追加  

Threadsアクセストークンをセッションへ保存（暫定・未暗号化）  

Threads投稿テストAPI /threads/test-post を追加  
Threads投稿処理（コンテナ作成 → 公開）を実装  
フロントエンドにテスト投稿ボタンを追加  

DynamoDB ScheduledPostsTable を利用した予約保存API /scheduled-posts を実装  
予約投稿データの保存（status=scheduled）を実装  

予約投稿一覧取得API GET /scheduled-posts を実装  
DynamoDBからユーザー単位で予約データを取得する処理を追加  
Decimal型によるJSONシリアライズエラー対策として数値をintへ変換  

予約投稿削除API DELETE /scheduled-posts/{post_id} を実装  
threads_user_id および status 条件付きで安全に削除する処理を追加  

フロントエンドで予約投稿一覧をAPI連携へ変更  
サンプルデータを廃止し、DynamoDBの実データ表示へ移行  
ログイン後に予約一覧を自動取得する処理を追加  

予約時刻のバリデーションを追加  
過去日時の投稿を禁止  
現在時刻から5分以内の投稿を禁止  

フロントエンドでユーザーのタイムゾーンを取得し送信する処理を追加  
予約初期値を現在時刻＋10分に設定  

### 変更
認証フローを仮実装から本実装へ変更（Cookie + DynamoDBセッション）  
/me の挙動を固定レスポンスからセッションベースへ変更  
ログイン後のリダイレクト先を APP_URL 固定から動的制御へ変更  

API Gateway CORS設定に http://localhost:5173 を追加  
LambdaでOPTIONSリクエスト（CORSプリフライト）を明示的に処理するように変更  
Access-Control-Allow-Headers の設定不備を修正（YAMLインデント不備対応）  

フロントエンドの投稿ボタンをテスト投稿APIから予約保存APIへ接続準備  
予約ボタンの活性条件を整理（本文・日時・上限・ステータス）  

APIの timezone 変数名衝突を修正（文字列と datetime.timezone の衝突回避）  
/scheduled-posts に例外ハンドリングを追加し、エラー詳細をレスポンスに出力  

### 修正（不具合対応）
/scheduled-posts GET APIにてDecimal型がJSONシリアライズできず500エラーとなる問題を修正  
→ created_at / updated_at をintへ変換することで対応  

/scheduled-posts APIにおいて更新処理が存在せず、常に新規作成される問題を確認  
post_id を毎回新規生成していたため、既存データが上書きされない設計となっていた  

今後の対応方針：  
- 更新用API（PUT /scheduled-posts/{post_id}）の追加  
- 既存データの上書き処理（update_item）の実装  
- フロントエンドで post_id を保持し更新時に送信する設計へ変更  

### 検証
Threads OAuthログイン成功  
Cookie発行およびセッション保持を確認  
/me にて認証状態が正しく判定されることを確認（200 / 401）  
ログアウト後にセッション削除されることを確認  

ローカル環境およびdev環境でログインフローが成立することを確認  
Threads投稿APIにより実際に投稿されることを確認  

CORSプリフライト（OPTIONS）が正常に通過することを確認  

/scheduled-posts APIで予約データがDynamoDBに保存されることを確認  
GET APIにより保存データが取得できることを確認  
DELETE APIにより予約が削除されることを確認  

5分以内の投稿予約がバリデーションで拒否されることを確認  
フロントエンドのタイムゾーン依存で正しい時刻が保存されることを確認  

### 未解決・次回対応
1日3件制限の実装  

ThreadsアクセストークンのKMS暗号化保存  
長期トークンへの交換処理  
ユーザーテーブル（users）への保存  

EventBridge Schedulerによる予約投稿実行処理  
publish_post.py の本実装（投稿実行＋ステータス更新）  

投稿履歴一覧のAPI連携  
投稿失敗時のエラーハンドリング強化  
投稿APIのレート制限対応  

本番環境でのCookie属性最適化（SameSite/Domain）

## 2026-05-05 JST（続き）

### 追加
EventBridge Schedulerによる自動投稿基盤を実装  

PostExecutorFunction（投稿実行Lambda）を新規作成  
scheduled_posts.status を利用した二重投稿防止ロジックを実装（scheduled → posting → posted）  

EventBridge Scheduler連携を実装  
POST /scheduled-posts 実行時に単発スケジュール（at式）を作成  
scheduler_name を scheduled_posts に保存  

Scheduler実行時に post_id を引き渡し、投稿LambdaでThreads投稿を実行する構成を実装  

IAM Role（SchedulerInvokeRole）を追加  
EventBridge SchedulerからLambdaをinvokeするための権限を設定  

API Lambdaに以下の権限を追加  
- scheduler:CreateSchedule  
- scheduler:DeleteSchedule  
- scheduler:GetSchedule  
- iam:PassRole（SchedulerInvokeRoleの引き渡し用）  

### 変更
/scheduled-posts 作成処理を拡張  
→ DynamoDB保存後にEventBridge Schedulerを作成する処理を追加  

Scheduler作成失敗時のエラーハンドリングを追加  
→ 予約作成を失敗として扱い、エラーメッセージを返却  

### 検証
EventBridge Schedulerにスケジュールが作成されることを確認  
scheduler_name がDynamoDBに保存されることを確認  
iam:PassRoleエラーを解消し、CreateScheduleが成功することを確認  

### 未解決・次回対応
自動投稿（PostExecutorFunction）の実行結果確認  
Threadsへの投稿成功・失敗の検証  

DELETE時のScheduler削除処理  
PUT時のScheduler差し替え処理  

failure_reasonのフロント表示対応  

sessionsテーブルからのアクセストークン取得を暫定実装しているため  
thread_tokensテーブルへの分離およびKMS暗号化対応

## 2026-05-05 JST（続き2）
### 追加

自動投稿の実行確認およびトラブルシュート機構を実装

PostExecutorFunctionにおいてThreads APIエラー内容の詳細ログ出力を追加
HTTPErrorのレスポンス本文をCloudWatch Logsへ出力することで原因特定を可能に

Threadsアクセストークンを短期トークンから長期トークン（約60日）へ交換する処理を実装
ログイン時にaccess_token_expires_atを計算しDynamoDBへ保存

投稿失敗時の状態管理を強化
scheduled_posts に以下の項目を追加

failure_reason（ユーザー表示用）
failure_detail（内部ログ用）

failure_reasonをユーザー向けメッセージへ変換するロジックを実装
（トークン期限切れ・投稿内容エラー・レート制限などを分類）

フロントエンドにfailure_reasonの表示を追加
予約一覧で失敗理由をユーザーに可視化

予約投稿更新API PUT /scheduled-posts/{post_id} を実装
EventBridge Schedulerの差し替え処理を追加

新Scheduler作成
DynamoDB更新
旧Scheduler削除

DELETE時のScheduler削除処理を実装
予約キャンセル時にEventBridge Schedulerも削除するように変更

thread_tokensテーブルを新規追加
Threadsアクセストークン管理をsessionsテーブルから分離

ログイン時にthread_tokensへ以下を保存

access_token
access_token_expires_at
reauth_required
updated_at

PostExecutorFunctionにてthread_tokensテーブルからアクセストークンを取得する処理を実装
sessionsテーブル依存を解消

### 変更

アクセストークン管理をsessionsテーブルからthread_tokensテーブルへ移行
sessionsはセッション管理専用とし、責務を分離

PostExecutorFunctionのトークン取得ロジックをscan方式からget_item方式へ変更
（threads_user_idをPKとした単一取得へ最適化）

エラーハンドリングを強化
Threads APIエラーをそのまま返却するのではなく、ユーザー向けメッセージへ変換

### 検証

EventBridge Schedulerにより指定時刻にLambdaが起動することを確認
PostExecutorFunctionが正常にThreads投稿を実行することを確認

長期トークンを利用した投稿が成功することを確認
トークン期限切れ時にfailure_reasonが適切に表示されることを確認

PUTによる予約変更時にSchedulerが正しく差し替えられることを確認
DELETEによる予約キャンセル時にSchedulerが削除されることを確認

フロントエンドにおいて失敗理由がユーザーに表示されることを確認

### 未解決・次回対応

アクセストークンの自動更新（refresh処理）の実装
token期限切れ前の更新Lambdaの設計

reauth_requiredフラグを利用したUI改善
（再ログイン導線の追加）

thread_tokensテーブルのKMS暗号化対応

投稿失敗時のリトライ機構の検討
（手動再投稿 or 自動リトライ）

投稿可能期間制限（トークン期限考慮）の実装