# Schedule For SNS Meta / Threads設定

最終更新日: 2026-05-01 23:09:57 JST

この文書は、Schedule For SNSでThreads OAuthとThreads APIを利用するためのMeta側設定手順です。

## 1. 方針

MVPでは、Meta App Reviewの審査範囲を広げないため、必要最小限のThreads APIスコープだけを要求する。

要求するスコープ:

- `threads_basic`
- `threads_content_publish`
- `threads_manage_insights`

要求しないスコープ:

- `threads_read_replies`
- `threads_manage_replies`
- `threads_keyword_search`
- `threads_manage_mentions`
- `threads_delete`
- `threads_location_tagging`
- `threads_profile_discovery`

## 2. Meta App作成

Meta for Developersでアプリを作成する。

確認する値:

- Threads App ID
- Threads App Secret

環境変数:

```text
THREADS_CLIENT_ID=Threads App ID
THREADS_CLIENT_SECRET=Threads App Secret
```

## 3. Redirect URI

Threads OAuthのredirect URIを設定する。

dev:

```text
https://{dev-api-id}.execute-api.ap-northeast-1.amazonaws.com/dev/auth/threads/callback
```

prod:

```text
https://{prod-api-id}.execute-api.ap-northeast-1.amazonaws.com/prod/auth/threads/callback
```

API Gatewayカスタムドメイン設定後は、独自ドメインのcallback URLへ変更する。

注意:

- OAuth開始時に渡す `redirect_uri` と、トークン交換時に渡す `redirect_uri` は完全一致させる
- Meta App Dashboardに登録するCallback URLとも一致させる

## 4. OAuth認可URL

ユーザーが「Threadsでログイン」を押したら、バックエンドでstateを生成し、以下のURLへリダイレクトする。

```text
https://threads.net/oauth/authorize
  ?client_id={THREADS_CLIENT_ID}
  &redirect_uri={THREADS_REDIRECT_URI}
  &scope=threads_basic,threads_content_publish,threads_manage_insights
  &response_type=code
  &state={CSRF_STATE}
```

`state` はCSRF対策として必ず検証する。

## 5. 認可コード交換

callbackで受け取った `code` を短期アクセストークンへ交換する。

Endpoint:

```text
POST https://graph.threads.net/oauth/access_token
```

必要パラメータ:

- `client_id`
- `client_secret`
- `code`
- `grant_type=authorization_code`
- `redirect_uri`

レスポンスで以下を受け取る。

- `access_token`
- `user_id`

参考: https://www.postman.com/meta/threads/request/34203612-109b9042-c054-44ef-b101-0490b08a6f57

## 6. 長期トークン

短期アクセストークン取得後、長期アクセストークンへ交換する。

その後、`thread_tokens` に以下を保存する。

- `app_user_id`
- `threads_user_id`
- `access_token_encrypted`
- `expires_at`
- `scopes`
- `reauth_required=false`

保存時はKMSで暗号化する。

長期トークンは期限前に更新する。

更新失敗時:

- `reauth_required=true` にする
- ログイン後に「Threads再連携が必要」ダイアログを表示する
- 再連携が完了するまで予約作成を停止する

## 7. 投稿API

投稿実行Lambdaでは、以下の順で投稿する。

1. `scheduled_posts.status` を条件付き更新で `scheduled` から `posting` に変更する
2. サブスクリプション状態、休止状態、再連携要否を確認する
3. Threads APIで投稿コンテナを作成する
4. Threads APIで投稿を公開する
5. 成功時は `posted` に更新する
6. 失敗時は `failed` に更新する

重複投稿防止のため、失敗時の自動再試行は行わない。

## 8. 投稿分析API

投稿成功後、当該投稿について以下のタイミングだけInsightsを取得する。

- 1時間後
- 24時間後
- 72時間後

投稿別Insights:

```text
GET https://graph.threads.net/{threads-media-id}/insights
```

取得メトリクス:

- `views`
- `likes`
- `replies`
- `reposts`
- `quotes`
- `shares`

参考: https://www.postman.com/meta/threads/request/9mq87f4/get-post-insights

## 9. App Review

一般公開前にMeta App Reviewが必要になる可能性が高い。

提出時に用意するもの:

- サービス概要説明
- 使用するスコープごとの理由
- 審査用テストアカウント
- 審査動画
- OAuthログイン手順
- 予約投稿作成手順
- 投稿成功後の分析画面
- 設定画面のThreads再連携状態

スコープごとの説明:

| スコープ | 利用目的 |
| --- | --- |
| `threads_basic` | ThreadsユーザーID取得、トークン交換・更新、基本的なアカウント連携確認 |
| `threads_content_publish` | ユーザーが予約した本文を指定時刻にThreadsへ投稿するため |
| `threads_manage_insights` | 投稿成功後の基本分析を表示するため |

審査動画で見せる流れ:

1. Schedule For SNSを開く
2. Threadsでログインする
3. 課金状態またはトライアル状態を確認する
4. カレンダーで日付を選ぶ
5. 投稿本文と時刻を入力する
6. 予約前確認画面を表示する
7. 予約を作成する
8. 予約一覧で予約済み投稿を確認する
9. 投稿後の分析画面を確認する
10. 設定画面でThreads連携状態を確認する

## 10. テスター設定

App Review前の開発中は、Meta Appのテスターとして利用者を追加する。

確認事項:

- 開発者アカウントでMeta Appにアクセスできる
- テスト用ThreadsアカウントをApp Testerへ追加する
- テスター側で招待を承認する
- Threads側で連携許可ができる

## 11. レート制限

Threads APIのレート制限は、エンドポイント、アプリ、ユーザーアクセストークン、Meta側内部制限に依存する。

Schedule For SNSでは以下で負荷を抑える。

- 投稿はユーザーが予約した時刻だけ実行する
- 分析取得は投稿ごとに1時間後、24時間後、72時間後のみ
- 429や制限系エラーはfailedまたは分析スキップとして扱う
- 自動再試行で重複投稿を起こさない

## 12. ログ方針

CloudWatch Logsに以下を出力しない。

- Threadsアクセストークン
- Threads App Secret
- 投稿本文
- Authorizationヘッダー
- Cookie

ログに出してよいもの:

- `app_user_id`
- `post_id`
- 処理ステージ
- エラーコード
- 外部APIのエラー分類

## 13. 環境変数

dev:

```text
THREADS_CLIENT_ID=dev Threads App ID
THREADS_CLIENT_SECRET=dev Threads App Secret
THREADS_REDIRECT_URI=https://{dev-api}/dev/auth/threads/callback
```

prod:

```text
THREADS_CLIENT_ID=prod Threads App ID
THREADS_CLIENT_SECRET=prod Threads App Secret
THREADS_REDIRECT_URI=https://{prod-api}/prod/auth/threads/callback
```

## 14. Meta設定チェックリスト

- [ ] Meta for Developersでアプリを作成する
- [ ] Threads APIを有効化する
- [ ] Threads App IDを控える
- [ ] Threads App Secretを控える
- [ ] dev callback URLを登録する
- [ ] prod callback URLを登録する
- [ ] OAuthで要求するスコープを3つに限定する
- [ ] テスト用ThreadsアカウントをApp Testerに追加する
- [ ] テスター側で招待を承認する
- [ ] OAuthログインが成功することを確認する
- [ ] 短期トークン交換が成功することを確認する
- [ ] 長期トークン交換が成功することを確認する
- [ ] トークン更新が成功することを確認する
- [ ] text投稿が成功することを確認する
- [ ] 投稿Insightsが取得できることを確認する
- [ ] App Review用説明文を作成する
- [ ] App Review用審査動画を作成する
