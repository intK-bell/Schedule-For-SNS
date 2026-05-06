# Schedule For SNS Amplify / Route 53設定

最終更新日: 2026-05-01 23:15:04 JST

この文書は、Schedule For SNSをAmplify Hostingで公開し、Route 53の `aokigk.com` から `s4s.aokigk.com` を割り当てるための手順です。

## 1. 前提

正式URL:

```text
https://s4s.aokigk.com/
```

前提:

- Route 53に `aokigk.com` のHosted Zoneがある
- Amplify Hostingを使う
- `main` ブランチを本番環境にする
- `dev` ブランチを開発環境にする

注意:

- `aokigk.com` のHosted Zoneが必要
- `aokigl.com` のHosted Zoneでは `s4s.aokigk.com` は管理できない

## 2. Route 53確認

AWS Consoleで確認する。

1. Route 53を開く
2. Hosted zonesを開く
3. `aokigk.com` が存在することを確認する
4. Hosted zone IDを控える

`aokigk.com` が存在しない場合:

1. Hosted zoneを作成する
2. Domain nameに `aokigk.com` を指定する
3. Public hosted zoneを選択する
4. 作成されたNSレコードをドメインレジストラ側に設定する

## 3. Amplifyアプリ作成

AWS ConsoleでAmplify Hostingを開く。

1. Amplifyを開く
2. New appを選択する
3. GitHubなどのリポジトリを接続する
4. ブランチ `main` を接続する
5. Build settingsを確認する
6. Deployする

ビルドコマンド:

```bash
npm ci
npm run build
```

出力ディレクトリ:

```text
dist
```

## 4. Amplify build settings

Amplifyのbuild settings例:

```yaml
version: 1
frontend:
  phases:
    preBuild:
      commands:
        - npm ci
    build:
      commands:
        - npm run build
  artifacts:
    baseDirectory: dist
    files:
      - '**/*'
  cache:
    paths:
      - node_modules/**/*
```

この内容は必要に応じて `amplify.yml` としてプロジェクトルートに置く。

## 5. dev/mainブランチ分離

ブランチ方針:

| ブランチ | 用途 | URL |
| --- | --- | --- |
| `main` | 本番 | `https://s4s.aokigk.com/` |
| `dev` | 開発 | Amplify標準URL、または `dev.s4s.aokigk.com` |

まずは本番 `main` に `s4s.aokigk.com` を割り当てる。

開発環境URLは、Amplify標準URLでもよい。

必要になったら以下を追加する。

```text
https://dev.s4s.aokigk.com/
```

## 6. カスタムドメイン追加

Amplify Consoleで設定する。

1. Amplifyアプリを開く
2. Hosting > Custom domainsを開く
3. Add domainを選択する
4. Root domainに `aokigk.com` を入力する
5. Route 53管理ドメインとして表示されることを確認する
6. Configure domainを選択する
7. Root domainや `www` が不要ならExclude rootを選択する
8. Subdomainに `s4s` を設定する
9. Branchに `main` を割り当てる
10. Amplify managed certificateを選択する
11. Add domainを選択する

AmplifyがRoute 53に必要なDNSレコードを自動作成する。

証明書発行とDNS反映には時間がかかることがある。

参考: https://docs.aws.amazon.com/amplify/latest/userguide/to-add-a-custom-domain-managed-by-amazon-route-53.html

## 7. SPAリダイレクト設定

React/ViteのSPAなので、直接URLへアクセスしたときに404にならないようにRewrites and redirectsを設定する。

設定例:

| Source address | Target address | Type |
| --- | --- | --- |
| `/<*>` | `/index.html` | `200 (Rewrite)` |

## 8. 環境変数

AmplifyのEnvironment variablesに設定する。

本番 `main`:

```text
VITE_APP_URL=https://s4s.aokigk.com
VITE_API_BASE_URL=https://{prod-api}
```

開発 `dev`:

```text
VITE_APP_URL=https://dev.s4s.aokigk.com
VITE_API_BASE_URL=https://{dev-api}
```

開発URLにAmplify標準URLを使う場合、`VITE_APP_URL` はAmplify標準URLにする。

## 9. OAuth / Stripeに反映するURL

本番URLが確定したら、以下にも反映する。

Meta App:

```text
https://{prod-api}/prod/auth/threads/callback
```

Stripe Checkout:

```text
success_url=${APP_URL}/billing/success
cancel_url=${APP_URL}/billing/cancel
```

dev環境では `APP_URL` をdevフロントURLにする。本番URLを指定すると、Stripeサンドボックスの確認後でも本番画面へ戻ってしまう。

Stripe Webhook:

```text
https://{prod-api}/prod/stripe/webhook
```

API Gatewayにカスタムドメインを設定した場合は、API URLを独自ドメインへ置き換える。

## 10. 確認チェックリスト

- [ ] Route 53に `aokigk.com` Hosted Zoneがある
- [ ] Amplifyアプリを作成した
- [ ] `main` ブランチを接続した
- [ ] `dev` ブランチを接続した
- [ ] Build commandが `npm run build` になっている
- [ ] Output directoryが `dist` になっている
- [ ] `s4s.aokigk.com` をmainブランチへ割り当てた
- [ ] Amplify managed certificateが発行された
- [ ] DNS verificationが完了した
- [ ] `https://s4s.aokigk.com/` でアクセスできる
- [ ] SPA rewriteを設定した
- [ ] Amplify環境変数を設定した
- [ ] Meta AppのCallback URLと整合している
- [ ] Stripe Checkout URLと整合している
