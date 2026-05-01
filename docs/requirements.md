# Threads予約投稿アプリ 要件定義 v0.1

## 1. 概要

Schedule For SNSとして、Threads向けのシンプルな予約投稿Webアプリを作成する。

ユーザーはThreads OAuthでログインし、カレンダーから投稿したい日を選択する。選択した日付に対して投稿時刻と投稿本文を設定し、予約投稿を作成できる。

料金は税込月額390円のみとし、14日間の無料トライアルを提供する。

## 2. 基本方針

- Threads専用の予約投稿アプリとする
- 認証はCognitoを使わず、Threads OAuth 2.0を使う
- アプリ用セッションはバックエンドで発行する
- ThreadsアクセストークンはLocalStorageに保存しない
- 予約投稿はユーザーのブラウザが閉じていても実行される
- UIはLISM CSSを使う
- AWSベースで構築する
- Meta App Reviewで通しやすくするため、MVPでは必要最小限のThreads APIスコープだけを要求する
- サービス正式名称は「Schedule For SNS」とする
- 本番URLは `https://s4s.aokigk.com/` とする
- 問い合わせ先は `aokigyoumukikaku@gmail.com` とする
- Amplifyは `main` を本番環境、`dev` を開発環境として分離する
- Stripe、Meta App、環境変数、Webhook URLも本番/開発で分離する

## 3. 技術スタック

### フロントエンド

- Amplify Hosting
- React
- Vite
- LISM CSS
- i18n対応ライブラリ

### バックエンド

- API Gateway HTTP API
- AWS Lambda Python
- DynamoDB
- EventBridge Scheduler
- AWS KMS
- Stripe
- Threads API

## 4. 認証要件

### Threads OAuthログイン

ユーザーは「Threadsでログイン」ボタンからOAuth認証を行う。

MVPで要求するThreads APIスコープ:

- `threads_basic`
- `threads_content_publish`
- `threads_manage_insights`

MVPで要求しないThreads APIスコープ:

- `threads_read_replies`
- `threads_manage_replies`
- `threads_keyword_search`
- `threads_manage_mentions`
- `threads_delete`
- `threads_location_tagging`
- `threads_profile_discovery`

Meta App Reviewでは、予約投稿と基本分析に必要な機能だけを画面上に出し、申請スコープも上記3つに絞る。

認証フロー:

1. フロントエンドが `/auth/threads/start` に遷移する
2. LambdaがThreads OAuth認可URLへリダイレクトする
3. ユーザーがThreads側で権限を許可する
4. Threads OAuth callbackで認可コードを受け取る
5. Lambdaが認可コードをアクセストークンに交換する
6. LambdaがThreads user_idを取得する
7. DynamoDBにユーザー情報とトークン情報を保存する
8. Lambdaがアプリ用セッションをHttpOnly Cookieで発行する
9. フロントエンドへログイン完了として戻す

### セッション

- HttpOnly Cookieを使う
- SameSite属性を設定する
- Secure属性を本番環境で有効にする
- セッションJWTにはThreadsアクセストークンを含めない

### Threadsアクセストークン期限

- 短期トークン取得後、長期トークンへ交換して保存する
- `thread_tokens.expires_at` に期限を保存する
- 定期Lambdaで期限が近いトークンを更新する
- 更新に失敗した場合は `reauth_required` を保存する
- 再連携が必要なユーザーにはUI上で「Threads再連携が必要」と表示する
- 再連携が必要な状態で投稿時刻を迎えた場合、投稿は失敗として扱い、失敗理由に「Threads再連携が必要」と表示する

### 休止状態

- user_statusが`paused`の場合、ログイン後に「休止中です。利用には再開が必要です」とダイアログ表示する
- 休止中は予約作成、予約編集、予約削除、分析取得、投稿実行を停止する
- 休止中でも設定画面と再開導線は利用できる
- 再開後、user_statusを`active`に戻す

## 5. 課金要件

### プラン

税込月額390円のみ。

含まれる内容:

- 14日間無料トライアル
- 1日3予約まで
- 基本分析つき
- 多言語UI
- 予約一覧
- 予約削除
- 自動投稿

### Stripe

- Stripe Checkoutでサブスクリプション登録を行う
- Stripe Billing Portalで支払い方法変更を行う
- Stripe Webhookでサブスクリプション状態を同期する
- 有効なサブスクリプションまたは無料トライアル中のユーザーのみ予約投稿できる
- ユーザー向け表示価格は税込390円/月とする
- 無料トライアル中は残り日数と残り時間を表示する
- 無料トライアル終了前のメール通知や外部通知は行わない
- 設定画面からStripe Billing Portalへ遷移できるキャンセル導線を用意する
- 課金開始日、次回請求日、現在のサブスクリプション状態を設定画面に表示する
- 無料トライアルは同一ユーザーにつき1回のみ利用可能とする
- 退会後の再登録で14日無料トライアルを繰り返し利用できないようにする
- 解約だけの導線は設けず、ユーザー操作としては退会を基本導線にする
- 退会時はStripeサブスクリプションを終了し、削除対象データを削除する
- 将来的に休止機能を設ける場合、休止中は予約投稿実行と分析取得を停止する
- Threadsログインだけではメールアドレスを取得しない
- Stripe Checkoutで顧客メールアドレスを取得する
- 領収書、支払い失敗通知などはStripe側メール機能で送信する

Stripe設定チェックリスト:

- Product名を「Schedule For SNS」にする
- Priceを税込390円/月にする
- Recurring intervalをmonthlyにする
- Trial periodを14 daysにする
- Checkout modeをsubscriptionにする
- Customer Portalを有効化する
- Customer Portalでは支払い方法変更を許可する
- 成功URLを `https://s4s.aokigk.com/` 配下に設定する
- キャンセルURLを `https://s4s.aokigk.com/` 配下に設定する
- Webhook endpointを本番API Gatewayの `/stripe/webhook` に設定する
- Webhook署名シークレットをLambda環境変数に設定する
- Webhook eventで `checkout.session.completed` を購読する
- Webhook eventで `customer.subscription.created` を購読する
- Webhook eventで `customer.subscription.updated` を購読する
- Webhook eventで `customer.subscription.deleted` を購読する
- Webhook eventで `invoice.payment_succeeded` を購読する
- Webhook eventで `invoice.payment_failed` を購読する

対象ステータス:

- trialing
- active
- past_due
- canceled
- unpaid

予約作成を許可するステータス:

- trialing
- active

## 6. 投稿予約要件

### 予約作成

ユーザーはカレンダーから日付を選択し、投稿時刻と投稿本文を入力して予約を作成できる。

制限:

- 1ユーザーあたり1日最大3件まで
- 過去日時への予約は不可
- 現在時刻から5分以内の日時には予約不可
- 投稿本文の空文字は不可
- 投稿本文はThreads APIの制限に従う
- サブスクリプションが有効でない場合は予約作成不可
- 休止中のユーザーは予約作成不可
- Threads再連携が必要なユーザーは予約作成不可
- 予約確定前に、投稿日時、タイムゾーン、投稿本文の確認表示を行う
- 予約済み投稿は投稿前であれば編集できる
- 予約済み投稿は投稿前であれば削除できる
- 編集時も1日3件制限、5分以内禁止、サブスクリプション状態、休止状態、Threads再連携要否を再チェックする

### タイムゾーン

- 初期値はブラウザのタイムゾーンを使う
- ユーザー設定としてタイムゾーンを保存する
- 設定画面からタイムゾーンを変更できる
- 1日3件制限はユーザーのタイムゾーン基準で判定する

### 予約削除

- 投稿前の予約は削除できる
- 削除時はEventBridge Schedulerのスケジュールも削除する
- 投稿済みの投稿は削除対象外とする
- ユーザー退会時は未投稿の予約をキャンセルし、関連するEventBridge Schedulerを削除する

### 予約編集

- 投稿前の予約は編集できる
- 編集できる項目は投稿日時、タイムゾーン、投稿本文とする
- 編集時は、新しいSchedulerを作成してからDynamoDBの予約内容を更新し、その後に古いSchedulerを削除する
- 新しいScheduler作成に失敗した場合、予約内容は変更せず元の予約を維持する
- DynamoDB更新に失敗した場合、新しく作成したSchedulerを削除して元の予約を維持する
- 古いScheduler削除に失敗した場合でも、投稿Lambda側のpost_idとstatus条件付き更新により二重投稿を防ぐ

## 7. 自動投稿要件

指定時刻になるとEventBridge Schedulerが投稿用Lambdaを起動する。

投稿フロー:

1. EventBridge Schedulerが投稿用Lambdaを起動する
2. Lambdaがscheduled_postsから予約情報を取得する
3. Lambdaがthread_tokensからアクセストークンを取得して復号する
4. LambdaがThreads APIで投稿コンテナを作成する
5. LambdaがThreads APIで投稿を公開する
6. 成功時はscheduled_posts.statusをpostedへ更新する
7. 失敗時はscheduled_posts.statusをfailedへ更新し、failure_reasonを保存する

投稿重複防止:

- 投稿Lambdaは実行開始時にscheduled_posts.statusを条件付き更新で`posting`へ変更する
- statusが`scheduled`でない投稿は処理しない
- 同じpost_idのLambdaが複数回起動しても二重投稿しない
- Threads APIで投稿公開後にthreads_media_idを保存する
- 失敗時の自動再試行は行わない
- 投稿実行時にもサブスクリプション状態、休止状態、Threads再連携要否を確認する
- サブスクリプションが無効、休止中、またはThreads再連携が必要な場合は投稿せずfailedにする

## 8. 投稿分析要件

MVP時点で基本分析を搭載する。

### 投稿別分析

投稿済みの投稿ごとに、取得可能な範囲で以下を表示する。

- 投稿日時
- 投稿本文
- いいね数
- 返信数
- リポスト数
- 引用数
- シェア数
- 閲覧数
- 合計エンゲージメント

### 集計分析

保存した投稿別の累計値をもとに以下を表示する。

- 投稿数
- 合計いいね数
- 合計返信数
- 合計リポスト数
- 合計シェア数
- 平均エンゲージメント

### ランキング

- 反応が良かった投稿
- 返信が多かった投稿

### 分析同期

- 投稿成功後、当該投稿について1時間後、24時間後、72時間後の3回だけ分析指標を取得する
- 投稿ごとに分析取得用のEventBridge Schedulerを作成するか、定期Lambdaで取得対象時刻の投稿だけを処理する
- MVPでは上記3回以外の自動分析取得は行わない
- サブスクリプションが無効、休止中、またはThreads再連携が必要な場合は分析取得しない
- 取得した指標をpost_analyticsへ保存する
- 投稿別指標は累計値として保存する

## 9. 多言語対応要件

対応言語:

- 日本語
- 英語
- 中国語
- フィリピン語
- ベトナム語

言語選択:

- 初回表示時はブラウザ言語から自動判定する
- ユーザー設定で手動変更できる
- 言語設定はusersテーブルに保存する

## 10. 画面要件

### ログイン画面

- Threadsでログインボタン
- 言語切替
- 料金と無料トライアルの簡単な説明

### 課金画面

- 月額390円の説明
- 14日間無料トライアルの説明
- Stripe Checkoutへ進むボタン

### メイン画面

- カレンダー
- 選択日の予約件数
- 投稿時刻入力
- 投稿本文入力
- 予約ボタン
- 1日3件の残り枠表示

### 予約一覧画面

- 予約済み
- 投稿済み
- 失敗
- キャンセル済み
- 削除ボタン
- 編集ボタン
- 失敗した投稿には失敗マークと失敗理由を表示する
- 失敗した投稿から同じ本文で新しい予約を作成できる

### 分析画面

- 投稿別分析
- 集計分析
- 反応の良い投稿ランキング

### 設定画面

- 言語設定
- タイムゾーン設定
- Threads連携状態
- サブスクリプション状態
- Stripe Billing Portalリンク
- トライアル残り日数・残り時間
- 課金開始日
- 次回請求日
- 退会
- ログアウト
- 特定商取引法に基づく表記
- 利用規約
- プライバシーポリシー

### 法務文書の表示

- ログイン前フッターから特定商取引法に基づく表記、利用規約、プライバシーポリシーを確認できる
- Stripe Checkoutへ進む前に特定商取引法に基づく表記、利用規約、プライバシーポリシーへのリンクを表示する
- 設定画面から特定商取引法に基づく表記、利用規約、プライバシーポリシーを確認できる

### 障害・お知らせバナー

- Threads API、Stripe、AWS、本サービスの障害やメンテナンス情報を表示する簡易バナーを用意する
- バナーはログイン後の画面上部に表示する
- 必要に応じてログイン前画面にも表示できるようにする

## 11. API要件

### 認証

- `GET /auth/threads/start`
- `GET /auth/threads/callback`
- `POST /auth/logout`
- `GET /me`

### 課金

- `POST /billing/checkout`
- `POST /billing/portal`
- `POST /stripe/webhook`

### 予約投稿

- `GET /scheduled-posts`
- `POST /scheduled-posts`
- `PUT /scheduled-posts/{post_id}`
- `DELETE /scheduled-posts/{post_id}`

### 分析

- `GET /analytics/summary`
- `GET /analytics/posts`

## 12. データ設計案

### users

- app_user_id
- threads_user_id
- display_name
- locale
- timezone
- stripe_customer_id
- subscription_status
- user_status
- created_at
- updated_at

### thread_tokens

- app_user_id
- threads_user_id
- access_token_encrypted
- expires_at
- scopes
- reauth_required
- updated_at

### trial_eligibility

- trial_key_hash
- app_user_id
- threads_user_id
- stripe_customer_id
- trial_used
- first_trial_started_at
- deleted_at
- retained_until

退会後も14日無料トライアルの繰り返し利用を防ぐため、復元不能な形の最小限の識別情報を保持する。保持対象は、無料トライアル利用済み判定、不正利用防止、請求・監査対応に必要な情報に限定する。

MVPでは `threads_user_id` をもとに `trial_key_hash` を作成して保持する。

### scheduled_posts

- post_id
- app_user_id
- threads_media_id
- scheduled_at
- scheduled_date
- timezone
- content
- status
- scheduler_name
- failure_reason
- created_at
- updated_at

### subscriptions

- app_user_id
- stripe_customer_id
- stripe_subscription_id
- status
- current_period_end
- trial_end
- created_at
- updated_at

### stripe_events

- stripe_event_id
- event_type
- processed_at

Stripe Webhookは同じイベントが複数回届く可能性があるため、`stripe_event_id` を保存して二重処理を防ぐ。

### admin_settings

- setting_key
- setting_value
- updated_at

障害・お知らせバナーなど、運営者が手動で変更する設定を保存する。

### admins

- admin_threads_user_id
- role
- created_at
- updated_at

運営者IDはDynamoDBで管理する。MVPでは手動登録でよい。

### post_analytics

- post_id
- app_user_id
- threads_media_id
- like_count
- reply_count
- repost_count
- quote_count
- share_count
- view_count
- engagement_total
- analytics_stage
- fetched_at

## 13. ステータス定義

### scheduled_posts.status

- scheduled
- posting
- posted
- failed
- canceled

### subscription_status

- trialing
- active
- paused
- past_due
- canceled
- unpaid
- incomplete

### user_status

- active
- paused
- suspended
- deleted

## 14. セキュリティ要件

- ThreadsアクセストークンはKMSで暗号化して保存する
- ThreadsアクセストークンをLocalStorageに保存しない
- アプリ用セッションはHttpOnly Cookieで管理する
- Stripe Webhookは署名検証を行う
- APIは認証済みユーザーのみアクセスできる
- ユーザーは自分の予約投稿と分析データのみ取得できる
- DynamoDB Point-in-Time Recoveryを有効化する
- 運営者向け手動運用でユーザー停止、投稿停止、課金状態確認ができるようにする

## 15. MVP範囲

初期リリースで実装するもの:

- Threads OAuthログイン
- HttpOnly Cookieセッション
- Stripe月額390円サブスクリプション
- 税込390円/月の価格表示
- 14日間無料トライアル
- トライアル残り日数・残り時間のカウントダウン表示
- 退会後の無料トライアル再利用防止
- サブスクリプション状態による予約制限
- 投稿実行時のサブスクリプション状態チェック
- 休止状態では予約投稿実行と分析取得を停止
- カレンダー予約
- 1日3件の予約制限
- 現在時刻から5分以内の予約禁止
- 予約確定前プレビュー
- 予約一覧
- 予約編集
- 予約削除
- EventBridge Schedulerによる自動投稿
- 投稿失敗時の自動再試行なし
- 失敗投稿から同じ本文で新規予約作成
- 二重投稿防止
- Stripe Webhookの二重処理防止
- 障害・お知らせバナー
- 運営者向け手動運用
- DynamoDB Point-in-Time Recovery
- dev/prod環境分離
- 基本分析
- 5言語対応
- LISM CSSによるUI

初期リリースでは実装しないもの:

- 画像投稿
- 複数SNS対応
- チーム機能
- 投稿テンプレート
- AI文章生成
- CSV/PDFエクスポート
- Cognito連携

## 16. 気になる点・確認事項

### Threads API権限

Threads APIの投稿権限と分析取得権限はMeta側の仕様と審査に依存する。実装前に必要スコープ、App Review要否、取得可能な分析指標を確認する。

### 分析指標

現在のThreads API仕様では、投稿別Insightsでviews、likes、replies、reposts、quotes、sharesが取得対象になる。アカウントInsightsではviews、likes、replies、reposts、quotes、clicks、followers_count、follower_demographicsが取得対象になる。ただし、実際の取得可否は権限、App Review、アカウント状態、Meta側仕様変更に依存する。取得不可の指標はUIで非表示にする前提にする。

### 分析権限

Threads分析取得にはthreads_manage_insightsスコープが必要になる想定。OAuth認可時に投稿権限とあわせて要求する。

### Meta App Review

MVPでは審査に引っかかる範囲を広げないため、Threads OAuthで要求するスコープをthreads_basic、threads_content_publish、threads_manage_insightsに限定する。返信管理、キーワード検索、メンション管理、削除、位置情報、プロフィール探索などの権限は要求しない。

Meta App Review用に、以下を用意する。

- サービス概要説明文
- Threadsログイン手順
- 予約投稿作成手順
- 投稿分析画面の説明
- 要求スコープごとの利用目的説明
- 審査用テストアカウント
- 審査動画の台本
- 審査動画の撮影チェックリスト

### 集計分析

投稿別Insightsは累計値として返るため、MVPでは累計値を中心に表示する。日別増分や時系列推移はMVPでは必須にしない。

### 分析取得タイミング

投稿分析は、投稿成功後の1時間後、24時間後、72時間後に当該投稿だけ取得する。それ以外の自動取得は行わない。これによりThreads APIのレート制限とAWS実行コストを抑える。

### Threads APIレート制限

Threads APIのレート制限は、使用するエンドポイント、アプリ、ユーザーアクセストークン、Meta側の内部制限に依存する。投稿やInsights取得はユーザーのThreadsアクセストークンで呼び出すため、実質的には「ユーザーごとの利用」と「アプリ全体の利用」の両方を意識して設計する。429や制限系エラーが返った場合は、該当投稿の取得をスキップし、必要に応じて次回取得タイミングで再試行する。

### Threads API費用

Threads API自体の呼び出しには、現時点ではMetaからのAPI従量課金は想定しない。ただし、APIを叩くために発生するAWS側の費用、つまりLambda、EventBridge Scheduler、DynamoDB、API Gateway、CloudWatchの費用は本サービス運営者が負担する。

### フォロワー属性

follower_demographicsは取得対象だが、フォロワー数などの条件で返らない可能性がある。MVPでは必須表示にせず、取得できる場合だけ表示する。

### 390円の収益性

税込390円は競合サービスよりかなり安い。Stripe手数料、消費税、AWSコストを考えると薄利のため、初期は検証価格として扱う。

### 税務・請求

日本向けに月額課金するため、税込価格表示、インボイス対応、特定商取引法表記を用意する。特定商取引法に基づく表記、利用規約、プライバシーポリシーは、既存サービスでStripe審査を通過している文面をベースに、本サービス向けへ調整する。

### タイムゾーン

1日3件制限はタイムゾーンの扱いが重要。初期値はユーザーのブラウザタイムゾーンを使い、設定画面で選択可能にする。予約制限はユーザー設定のタイムゾーンを基準に判定する。

### 投稿失敗時

Threads APIエラー、トークン期限切れ、権限失効、Scheduler実行失敗に備えて、失敗理由を保存する。UIでは失敗した投稿に失敗マークを表示し、ユーザーが失敗に気づけるようにする。重複投稿防止を優先し、失敗時の自動再試行は行わない。

### Threads再連携チェック

- ログイン後にThreads連携状態とトークン期限を確認する
- 再連携が必要な場合はダイアログで通知する
- 再連携が完了するまで予約作成を停止する
- 再連携が必要な状態で投稿時刻を迎えた予約は投稿せずfailedにする

### Stripe Webhookの二重処理防止

Stripe Webhookは同じイベントが複数回送信されることがある。`stripe_event_id` を保存し、処理済みイベントは再処理しない。これにより、退会、課金状態更新、サブスクリプション終了などが二重に実行されることを防ぐ。

### 退会とデータ削除

- ユーザーは設定画面から退会できる
- 退会時はStripeサブスクリプションを終了する
- 未投稿の予約はキャンセルし、EventBridge Schedulerを削除する
- Threadsアクセストークン、投稿本文、分析データ、通常プロフィール情報は削除対象とする
- 請求・監査・不正利用防止・無料トライアル再利用防止に必要な最小限の情報は、`threads_user_id` 由来の復元不能なハッシュとして保持する
- 保持期間は既存サービスの方針に合わせ、原則として削除実施日から3年間とする
- 保持期間経過後は削除または匿名化する

### EventBridge Scheduler削除漏れ対策

- 投稿削除時は対応するSchedulerを削除する
- 退会時は未投稿予約のSchedulerをすべて削除する
- 投稿成功後は対応するSchedulerを削除済みまたは完了扱いにする
- Scheduler削除に失敗した場合でも、投稿Lambda側の条件付き更新で二重投稿を防ぐ
- Scheduler削除失敗は内部ログに記録し、投稿本文やトークンは出力しない

### ログ設計

- CloudWatch LogsにThreadsアクセストークンを出力しない
- CloudWatch Logsに投稿本文を出力しない
- Stripe署名ヘッダー、Cookie、Authorizationヘッダーを出力しない
- エラー時はpost_id、app_user_id、エラーコード、処理ステージのみを記録する
- 外部APIレスポンス全文はログに出さず、必要なエラーコードと分類だけを保存する

### AWSコスト見積もり

最大利用時の前提:

- 1ユーザーあたり1日3投稿
- 30日換算で1ユーザーあたり月90投稿
- 投稿実行で1回のEventBridge Scheduler実行
- 分析取得は投稿ごとに1時間後、24時間後、72時間後の3回
- 合計で1投稿あたり最大4回のバックグラウンド実行

1ユーザーあたり月間バックグラウンド実行数:

- 投稿実行: 90回
- 分析取得: 270回
- 合計: 360回

ユーザー数別の概算:

| 有料ユーザー数 | 月間投稿数 | Scheduler/Lambda実行数 | EventBridge Scheduler費用目安 |
| --- | ---: | ---: | ---: |
| 1,000 | 90,000 | 360,000 | 無料枠内想定 |
| 10,000 | 900,000 | 3,600,000 | 無料枠内想定 |
| 50,000 | 4,500,000 | 18,000,000 | 約4 USD/月 |
| 100,000 | 9,000,000 | 36,000,000 | 約22 USD/月 |

EventBridge Schedulerは月1,400万回の呼び出し無料枠があるため、投稿と分析取得だけなら約38,888ユーザーまでは無料枠内に収まる想定。

DynamoDBの概算:

- 1投稿あたり、予約作成、投稿状態更新、分析保存などで約6 write unitsを想定
- 1投稿あたり、投稿取得、トークン取得、分析対象取得などで約6 read unitsを想定
- 1ユーザーあたり月90投稿なので、約540 write units/月、約540 read units/月

ユーザー数別のDynamoDBリクエスト概算:

| 有料ユーザー数 | 月間Write Units | 月間Read Units | DynamoDB費用目安 |
| --- | ---: | ---: | ---: |
| 1,000 | 540,000 | 540,000 | 低額 |
| 10,000 | 5,400,000 | 5,400,000 | 数USD規模 |
| 50,000 | 27,000,000 | 27,000,000 | 数十USD規模 |
| 100,000 | 54,000,000 | 54,000,000 | 100USD未満目安 |

上記は投稿・分析バックグラウンド処理中心の概算であり、管理画面の表示回数、CloudWatch Logs、API Gateway、Lambda実行時間、KMS復号、DynamoDB item size、GSI数により増減する。390円税込の低単価プランのため、実装時はDynamoDB Scanを禁止し、GSIで必要な範囲だけQueryする。

DynamoDB Point-in-Time Recovery費用:

- PITRは有効化する
- PITRはテーブルサイズに対する月額課金が発生する
- MVPは投稿本文と分析数値中心で1アイテムサイズが小さいため、初期費用インパクトは小さい想定
- ただし投稿本文を長期保持するほどストレージとPITR費用が増えるため、退会時削除と不要データ削除を徹底する

### 収支見積もり

前提:

- 価格は税込390円/月
- 消費税10%を控除する
- Stripe Paymentsは国内カード3.6%を想定する
- Stripe BillingはBilling volumeの0.7%を想定する
- 1 USD = 156.54円でAWS費用を円換算する
- 1ユーザーあたり最大利用、月90投稿、分析取得270回を想定する
- 広告費、開発費、人件費、返金、チャージバック、法人運営費、会計費用は含めない

1ユーザーあたりの月次概算:

| 項目 | 金額 |
| --- | ---: |
| ユーザー支払額 | 390.00円 |
| 消費税相当 | -35.45円 |
| 税抜売上 | 354.55円 |
| Stripe Payments 3.6% | -14.04円 |
| Stripe Billing 0.7% | -2.73円 |
| AWS変動費前の粗利 | 337.78円 |

ユーザー数別の月次粗利概算:

| 有料ユーザー数 | 税込売上 | AWS変動費前粗利 | AWS概算費用 | プロダクト粗利 |
| --- | ---: | ---: | ---: | ---: |
| 100 | 39,000円 | 33,778円 | 1,177円 | 32,601円 |
| 500 | 195,000円 | 168,888円 | 1,295円 | 167,593円 |
| 1,000 | 390,000円 | 337,775円 | 1,443円 | 336,332円 |
| 3,000 | 1,170,000円 | 1,013,326円 | 2,037円 | 1,011,289円 |
| 5,000 | 1,950,000円 | 1,688,877円 | 2,888円 | 1,685,989円 |
| 10,000 | 3,900,000円 | 3,377,755円 | 5,861円 | 3,371,893円 |
| 30,000 | 11,700,000円 | 10,133,264円 | 17,752円 | 10,115,512円 |
| 50,000 | 19,500,000円 | 16,888,773円 | 30,269円 | 16,858,504円 |
| 100,000 | 39,000,000円 | 33,777,545円 | 62,814円 | 33,714,732円 |

この見積もりでは、AWS費用は売上に対してかなり小さい。収益性の主な論点は、AWS費用よりも、ユーザー獲得単価、無料トライアルから有料化する転換率、Stripe手数料、消費税、返金・不審請求、開発・運用人件費になる。

## 17. 次の作業

1. Threads APIのOAuth、投稿、分析API仕様を確認する
2. AWS構成をIaCで定義する
3. フロントエンドの雛形を作成する
4. LISM CSSを導入する
5. Lambda/API Gateway/DynamoDBの雛形を作成する
6. Threads OAuthログインを実装する
7. Stripe CheckoutとWebhookを実装する
8. 予約投稿作成とEventBridge Scheduler連携を実装する
9. 投稿分析同期を実装する
