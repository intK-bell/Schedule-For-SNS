# Schedule For SNS Stripe設定

最終更新日: 2026-05-01 23:07:36 JST

この文書は、Schedule For SNSのStripe設定手順です。

## 1. 商品と価格

Stripe Dashboardで商品を作成する。

商品:

- Product name: `Schedule For SNS`
- Description: `Threads予約投稿と基本分析`

価格:

- Price: `390`
- Currency: `JPY`
- Tax behavior: 税込表示に合わせる
- Billing period: `Monthly`
- Type: `Recurring`

作成後、Price IDを控える。

```text
STRIPE_PRICE_ID=price_xxx
```

## 2. Checkout

Checkoutはサブスクリプションモードで作成する。

アプリ側でCheckout Sessionを作るときの方針:

- `mode=subscription`
- `line_items[0].price=STRIPE_PRICE_ID`
- `line_items[0].quantity=1`
- `subscription_data.trial_period_days=14`
- `success_url=https://s4s.aokigk.com/billing/success`
- `cancel_url=https://s4s.aokigk.com/billing/cancel`
- 顧客メールアドレスをStripe Checkoutで取得する

無料トライアルはStripe CheckoutのSubscription trialで実装する。

参考: https://docs.stripe.com/payments/checkout/free-trials

## 3. Customer Portal

Stripe Billing Portalを有効化する。

Schedule For SNSでは、ユーザー操作として「解約だけ」は設けず、退会を基本導線にする。

Customer Portalで許可する操作:

- 支払い方法の変更
- 請求情報の確認
- 請求書/領収書の確認

Customer Portalでサブスクリプション解約をユーザーへ直接出すかは、実装方針とStripe設定で最終確認する。

現時点のアプリ方針:

- 退会はアプリ設定画面から行う
- 退会時にアプリ側でStripeサブスクリプションを終了する
- 退会時に投稿本文、分析データ、Threadsトークン等を削除する
- `threads_user_id` 由来のハッシュのみ、無料トライアル再利用防止のため保持する

## 4. Webhook

Webhook endpointを作成する。

dev:

```text
https://{dev-api-id}.execute-api.ap-northeast-1.amazonaws.com/dev/stripe/webhook
```

prod:

```text
https://{prod-api-id}.execute-api.ap-northeast-1.amazonaws.com/prod/stripe/webhook
```

API Gatewayカスタムドメインを設定後は、独自ドメインのWebhook URLへ変更する。

Webhook署名シークレットを控える。

```text
STRIPE_WEBHOOK_SECRET=whsec_xxx
```

## 5. 購読するWebhookイベント

最低限購読するイベント:

- `checkout.session.completed`
- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`
- `invoice.payment_succeeded`
- `invoice.payment_failed`

検討イベント:

- `customer.subscription.paused`
- `customer.subscription.resumed`
- `customer.subscription.trial_will_end`
- `invoice.payment_action_required`

Schedule For SNSでは無料トライアル終了前のアプリ独自通知は行わないため、`customer.subscription.trial_will_end` はMVP必須ではない。

ただし、Stripe側のイベントとして受け取れるようにしておくと、将来通知や管理ログに使える。

参考: https://docs.stripe.com/billing/subscriptions/webhooks

## 6. Webhook処理ルール

Stripe Webhookは同じイベントが複数回送られる可能性がある。

アプリ側では以下を必ず行う。

1. Stripe署名を検証する
2. `event.id` を取得する
3. `stripe_events` に `event.id` が存在するか確認する
4. 存在する場合は処理済みとして何もしない
5. 存在しない場合のみ処理する
6. 処理後に `stripe_events` へ保存する

これにより、サブスクリプション状態更新や退会処理の二重実行を防ぐ。

## 7. サブスクリプション状態の扱い

予約作成を許可する状態:

- `trialing`
- `active`

予約作成を許可しない状態:

- `paused`
- `past_due`
- `canceled`
- `unpaid`
- `incomplete`

投稿実行時にもサブスクリプション状態を確認する。

投稿実行時に有効でない場合:

- 投稿しない
- scheduled_posts.statusを`failed`にする
- failure_reasonに「サブスクリプションが有効ではありません」を保存する

分析取得時に有効でない場合:

- 分析取得しない

## 8. メール通知

Threads OAuthだけではユーザーのメールアドレスを取得しない。

メールはStripe Checkoutで取得する。

アプリ独自の無料トライアル終了前通知は行わない。

Stripe側で送る可能性があるメール:

- 領収書
- 支払い失敗通知
- 請求関連メール

Stripe Dashboardでメール設定を確認する。

## 9. 環境変数

dev:

```text
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
STRIPE_PRICE_ID=price_xxx
```

prod:

```text
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
STRIPE_PRICE_ID=price_xxx
```

## 10. Stripe設定チェックリスト

- [ ] Product名を `Schedule For SNS` にする
- [ ] 価格を税込390円/月にする
- [ ] Recurring monthlyにする
- [ ] Price IDを控える
- [ ] Checkoutをsubscription modeで作る
- [ ] Trial periodを14 daysにする
- [ ] Customer Portalを有効化する
- [ ] Webhook endpointをdev/prodで作る
- [ ] Webhook署名シークレットを控える
- [ ] `checkout.session.completed` を購読する
- [ ] `customer.subscription.created` を購読する
- [ ] `customer.subscription.updated` を購読する
- [ ] `customer.subscription.deleted` を購読する
- [ ] `invoice.payment_succeeded` を購読する
- [ ] `invoice.payment_failed` を購読する
- [ ] Stripeメール設定を確認する
- [ ] dev/prodでSecret Keyを分ける
- [ ] dev/prodでWebhook Secretを分ける
- [ ] dev/prodでPrice IDを分けるか確認する
