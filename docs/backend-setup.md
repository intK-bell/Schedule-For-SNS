# Schedule For SNS バックエンド環境設定

最終更新日: 2026-05-01 23:04:46 JST

この文書は、Schedule For SNSのAWSバックエンド環境を構築するための手順です。

## 1. AWS環境

### 方針

- AWSリージョンは `ap-northeast-1` を基本とする
- `dev` と `prod` を分離する
- Amplifyは `dev` ブランチを開発環境、`main` ブランチを本番環境にする
- SAMスタックは `schedule-for-sns-dev` と `schedule-for-sns-prod` に分ける
- DynamoDBはオンデマンド課金にする
- DynamoDB Point-in-Time Recoveryを有効にする
- LambdaはPython 3.12 / arm64を使う
- API GatewayはHTTP APIを使う
- 投稿実行と分析取得はEventBridge Schedulerを使う

### 作成される主なAWSリソース

`backend/template.yaml` で以下を作成する。

- API Gateway HTTP API
- API用Lambda
- 投稿実行Lambda
- 分析取得Lambda
- DynamoDB `users`
- DynamoDB `thread_tokens`
- DynamoDB `scheduled_posts`
- DynamoDB `subscriptions`
- DynamoDB `post_analytics`
- DynamoDB `trial_eligibility`
- DynamoDB `stripe_events`
- DynamoDB `admin_settings`
- DynamoDB `admins`

### 事前に必要なもの

- AWS CLI
- AWS SAM CLI
- AWS認証プロファイル
- デプロイ先AWSアカウント
- デプロイリージョン `ap-northeast-1`

確認コマンド:

```bash
aws sts get-caller-identity
sam --version
```

### dev環境デプロイ

`backend/samconfig.toml` の `[dev.deploy.parameters]` を確認し、`replace_me` を実値に置き換える。

その後、以下を実行する。

```bash
cd backend
sam build
sam deploy --config-env dev
```

### prod環境デプロイ

`backend/samconfig.toml` の `[prod.deploy.parameters]` を確認し、`replace_me` を本番値に置き換える。

その後、以下を実行する。

```bash
cd backend
sam build
sam deploy --config-env prod
```

### SAMパラメータ

| パラメータ | 内容 |
| --- | --- |
| `StageName` | `dev` または `prod` |
| `AppUrl` | フロントエンドURL。devはdevフロント、本番は本番フロントを指定する |
| `ThreadsClientId` | Meta AppのClient ID |
| `ThreadsClientSecret` | Meta AppのClient Secret |
| `StripeSecretKey` | Stripe Secret Key |
| `StripeWebhookSecret` | Stripe Webhook署名シークレット |
| `StripePriceId` | 税込390円/月のStripe Price ID |
| `SessionSecret` | HttpOnly Cookieセッション署名用の長いランダム文字列 |

### DynamoDB運用ルール

- Scanは禁止
- ユーザー単位・日付単位の取得はGSI Queryで行う
- 予約投稿は `scheduled_posts` の `user-date-index` を使う
- Stripe Webhookは `stripe_events` に `stripe_event_id` を保存し、二重処理を防ぐ
- 退会後のトライアル再利用防止は `trial_eligibility` に `threads_user_id` 由来のハッシュを保存する
- 運営者Threads IDは `admins` に手動登録する
- 障害・お知らせバナーは `admin_settings` に手動登録する

### IAMと権限

SAMテンプレートでは、Lambdaごとに必要なDynamoDB権限を付与する。

API Lambdaには、予約作成・編集・削除のためにEventBridge Schedulerの以下権限を付与する。

- `scheduler:CreateSchedule`
- `scheduler:DeleteSchedule`

本番化時には、SchedulerのResourceを `*` から対象スケジュールグループに絞る。

### 環境変数

フロントエンド用:

- `VITE_APP_URL`
- `VITE_API_BASE_URL`

バックエンド用:

- `STAGE_NAME`
- `APP_URL`
- `THREADS_CLIENT_ID`
- `THREADS_CLIENT_SECRET`
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_PRICE_ID`
- `SESSION_SECRET`

### 本番URL

フロントエンド:

```text
https://s4s.aokigk.com/
```

API URLはSAMデプロイ後のOutput `ApiUrl` を確認する。

### 次に設定するもの

AWS環境の次は以下を設定する。

1. Stripe Product / Price / Checkout / Webhook
2. Meta App / Threads OAuth / Redirect URI
3. Amplify Hosting dev/main連携
4. API Gatewayカスタムドメイン

Stripe設定の詳細は [stripe-setup.md](./stripe-setup.md) を参照する。

Meta / Threads設定の詳細は [meta-threads-setup.md](./meta-threads-setup.md) を参照する。

Amplify / Route 53設定の詳細は [amplify-route53-setup.md](./amplify-route53-setup.md) を参照する。
