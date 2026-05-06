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

PostExecutorFunctionにおいてThreads APIエラー内容の確認ログを追加
詳細な外部APIエラー本文の扱いは、2026-05-06にログ方針へ合わせて修正

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

## 2026-05-05 JST（続き3）

### 追加
アクセストークン自動更新機構を実装  

TokenRefreshFunction（トークン更新Lambda）を新規作成  
EventBridge Schedule（cron）により1日1回の定期実行を設定  

thread_tokensテーブルを対象に、アクセストークンの有効期限をチェックする処理を実装  
有効期限が30日以内のトークンを対象に更新処理を実行  

Threads API（refresh_access_token）を利用した長期トークン更新処理を実装  
更新成功時に以下を更新  
- access_token  
- access_token_expires_at  
- reauth_required（falseへ更新）  

更新失敗時のフォールバック処理を実装  
reauth_required を true に更新し、再ログインが必要な状態を管理  

トークン更新処理のログ出力を強化  
- TOKEN REFRESH START  
- TOKEN REFRESH SUCCESS  
- TOKEN REFRESH FAILED  
- TOKEN REFRESH END  

---

### 変更
トークン有効期限に基づく運用設計を変更  

予約可能期間を30日先までに制限  
→ 長期トークン（約60日）に対して安全な余裕を確保  

トークン更新の閾値を30日前に設定  
→ 有効期限内で確実に更新される設計へ変更  

---

### 検証
TokenRefreshFunctionの手動実行により正常動作を確認  
thread_tokensテーブルの件数が取得されることを確認  

有効期限が十分先のトークンは更新対象外（skipped）となることを確認  
更新対象なしの場合でも正常終了することを確認  

---

### 未解決・次回対応
reauth_required を利用したフロントエンドUI改善  
（再ログイン導線の表示）  

トークン更新失敗時の通知設計（ユーザー通知）  

thread_tokensテーブルのKMS暗号化対応  

トークン更新失敗時のリトライ戦略の検討


## 2026-05-05 JST（続き4）
### 追加

予約可能日制御のフロントエンド実装を追加

カレンダーUIにおいて予約不可日のグレーアウト表示を実装
以下の条件に該当する日付を非活性化

今日より前の日付
30日を超える日付（予約可能期間外）
予約上限（3件）に達している日付

非活性日付に対して以下のUX改善を実装

ボタンのdisabled制御
視覚的に判別可能なグレーアウトスタイル適用
ホバー無効化（操作不可の明確化）

日付セルにツールチップ（title属性）を追加し、非活性理由を表示

「予約できるのは今日から30日以内です」
「この日は予約上限の3件に達しています」

日付入力フィールド（type="date"）にも制限を追加

min：当日
max：30日後

カレンダー表示と入力制御の整合性を担保

### 変更

予約可能期間の制御ロジックをフロントエンドにも適用

バックエンド制約（30日制限）に対し、UIレベルでの事前制御を追加
→ 不正入力およびエラー発生を未然に防止

### 検証

予約不可日が正しくグレーアウトされることを確認
対象日がクリック不可であることを確認

予約上限到達日が選択不可となることを確認

日付入力フィールドにおいて範囲外日付が選択できないことを確認

### 未解決・次回対応

予約可能期間30日制限を要件定義へ反映する（2026-05-06対応済み）
外部APIエラー本文をログへ出さない方針との整合性を確認する（2026-05-06対応済み）

## 2026-05-06 JST

### 修正

要件定義に予約可能期間30日以内の制限を追加

休止状態をMVP対象として扱うように課金要件の文言を整理

設定、休止、再開、退会、Threads再連携のAPI要件を追加

scheduled_posts.failure_detail の扱いを要件へ追加
failure_detailには外部APIレスポンス全文、投稿本文、アクセストークン、Cookie、Authorizationヘッダーを保存しない方針を明記

Threads APIおよびトークン更新のHTTPError処理を修正
CloudWatch Logsへ外部APIレスポンス本文を直接出力せず、ステータスコード、エラーコード、エラー種別だけを記録するように変更

OAuthログイン成功ログでsession_idそのものを出力せず、session_idの有無だけを出力するように変更

予約可能期間の変更記録にあった「30日以降」の表現を「30日を超える日付」に修正

フロントエンドのlintエラーを修正
未使用のテスト投稿UI残骸とサンプル投稿データを削除し、予約一覧取得処理の関数宣言順と型定義を整理

### 検証

`python3 -m compileall backend/app` 成功
`npm run lint` 成功
`npm run build` 成功

### 未解決・次回対応

thread_tokensテーブルのKMS暗号化対応（2026-05-06続きで対応済み）
thread_tokensの項目名を要件上の access_token_encrypted / expires_at へ寄せるか、実装名を要件へ反映するかを最終決定する（2026-05-06続きで対応済み）
設定、休止、再開、退会APIの実装（2026-05-06続きで対応済み）
Threads再連携導線の本実装（2026-05-06続きで対応済み）

## 2026-05-06 JST（続き）

### 追加

ThreadsアクセストークンのKMS暗号化保存を実装

ThreadTokenKmsKey と alias/schedule-for-sns-{StageName}-thread-token をSAMテンプレートに追加

ApiFunction、PostExecutorFunction、TokenRefreshFunctionに必要なKMS権限を追加

thread_tokensの保存項目名を要件側へ寄せ、access_token_encrypted / expires_at を正式項目として採用

既存データ移行中の互換性確保として、旧項目 access_token / access_token_expires_at も読み取り可能にした

UsersTableへのユーザー保存をログイン時に追加

設定更新API PATCH /me/settings を実装

休止API POST /account/pause と再開API POST /account/resume を実装

退会API DELETE /account を実装
退会時は未投稿予約のScheduler削除、予約投稿削除、分析データ削除、Threadsトークン削除、現在セッション削除、subscription_status更新、trial_eligibilityの保持期限更新を行う

Threads再連携導線をフロントエンドへ接続
再連携ボタンから /auth/threads/start?reauth=1 へ遷移するように変更

設定画面の言語、タイムゾーン、休止、再開、退会操作を実APIへ接続

### 変更

予約作成、予約編集、予約削除時に休止状態とThreads再連携要否をバックエンド側でもチェックするように変更

予約投稿データに app_user_id と scheduled_date を保存するように変更

thread_tokensテーブルのパーティションキーは既存実装との互換性を優先して threads_user_id のまま維持し、要件定義にもその方針を明記

トークン更新成功時に旧項目 access_token / access_token_expires_at を削除し、access_token_encrypted / expires_at へ移行するように変更

### 検証

`python3 -m compileall backend/app` 成功
SAMテンプレートのYAML構文確認成功
`npm run lint` 成功
`npm run build` 成功

### 未解決・次回対応

退会時のStripeサブスクリプション終了処理は実装したが、Stripe本番/開発環境で実API疎通確認が必要
既存thread_tokensデータの暗号化移行は、次回トークン更新または再連携時に順次反映される

## 2026-05-06 JST（続き2）

### 追加

課金要件に、14日間無料トライアル終了後はStripeサブスクリプションがactiveでない限り主要操作を止める方針を追記

無料トライアル中でもStripe Checkoutへ進める「今すぐ登録」ボタンの要件を追加

フロントエンドに「今すぐ登録」ボタンを追加
ログイン後の通知帯、サイドバーのトライアル表示、設定画面からStripe Checkoutへ遷移できるようにした

トライアル終了時のブロックバナーを追加

### 変更

/me レスポンスに subscription_status、trial_end、has_subscription_entitlement を返すように変更

予約作成、予約編集、テスト投稿APIで、休止状態とThreads再連携要否に加えてサブスクリプション権限もチェックするように変更

PostExecutorFunctionで投稿実行時にもユーザー状態とサブスクリプション権限をチェックするように変更

ログイン時にtrial_endを保持し、既存ユーザーのtrial_endを再ログインでリセットしないように変更

Stripe Checkout作成時にclient_reference_idとmetadataへapp_user_id / threads_user_idを設定するように変更

### 検証

`python3 -m compileall backend/app` 成功
SAMテンプレートのYAML構文確認成功
`npm run lint` 成功
`npm run build` 成功

### 未解決・次回対応

Stripe Webhookでcheckout.session.completed、customer.subscription.*を受け取り、subscription_status、trial_end、current_period_endを同期する実装が必要

## 2026-05-06 JST（続き3）

### 修正

既存ユーザーにtrial_endが未保存の場合、無料トライアル終了扱いになる問題を修正

trial_end未保存時はtrial_started_at、なければcreated_atから14日後を無料トライアル終了日時として補完するように変更

trial開始日の補完優先順位を、users.trial_started_at、trial_eligibility.first_trial_started_at、users.created_at、現在時刻の順に変更

ログイン時に既存ユーザーのtrial_started_atとtrial_endを保持し、再ログインでトライアル期間がリセットされないように整理

### 追加

/me レスポンスに trial_started_at を追加

フロントエンドで無料トライアルの開始日時と終了日時を表示

期限切れバナーにも無料トライアルの開始日時と終了日時を表示

要件定義に無料トライアル開始日時・終了日時の表示と、既存ユーザー向けのtrial_end補完方針を追加

要件定義に無料トライアル開始日時の補完優先順位を追記

### 検証

`python3 -m compileall backend/app` 成功
`npm run lint` 成功
`npm run build` 成功

## 2026-05-06 JST（続き4）

### 変更

無料トライアルを同一Threadsアカウントにつき1回だけに制限する方針を明確化

`trial_eligibility.trial_used` がtrueのThreadsアカウントでは、Stripe Checkout作成時に新しい14日トライアルを付与しないように変更

初回トライアル資格レコードに `trial_end` を保持し、既存ユーザー補完と退会後の再登録判定で参照できるように変更

Stripe Checkout APIレスポンスに `trial_included` を追加

### ドキュメント

要件定義に、無料トライアルは初回Threadsログイン時または初回トライアル資格レコード作成時に開始することを追記

要件定義に、退会後に同じThreadsアカウントで再登録しても再トライアルを付与しないことを追記

### 検証

`python3 -m compileall backend/app` 成功
`npm run lint` 成功
`npm run build` 成功
`git diff --check` 成功

## 2026-05-06 JST（続き5）

### 変更

dev環境の `AppUrl` を本番URLからdevフロントURLへ変更

Stripe Checkoutの `success_url` / `cancel_url` が環境ごとの `APP_URL` から作られる方針をドキュメントへ明記

devでStripeサンドボックス確認後に本番画面へ戻らないように整理

### 検証

`python3 -m json.tool backend/env/dev.example.json` 成功
`sam validate --template-file template.yaml --config-file samconfig.toml --config-env dev` 成功
`git diff --check` 成功

## 2026-05-06 JST（続き6）

### 修正

Stripe Checkout完了後も `/me` が `subscription_status=trialing` のままになる問題に対応

`/stripe/webhook` でStripe署名検証、`stripe_event_id` による二重処理防止、`checkout.session.completed` と `customer.subscription.*` の同期を実装

Webhook処理で `subscriptions` と `users.subscription_status` を更新するように変更

フロントエンドでサブスクリプションが `active` の場合は「今すぐ登録」ボタンを表示しないように変更

Meta App Review向け通知帯から重複していた「今すぐ登録」ボタンを削除

### ドキュメント

Stripe Webhookで `/me` の課金状態を最新化する方針を要件定義とStripe設定手順へ追記

### 検証

`python3 -m compileall backend/app` 成功
`npm run lint` 成功
`npm run build` 成功
`sam validate --template-file template.yaml --config-file samconfig.toml --config-env dev` 成功
`git diff --check` 成功
