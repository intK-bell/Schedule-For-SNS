import os
import urllib.parse
from http import HTTPStatus
import urllib.request
import json
import secrets
import time
import hashlib
import base64
import boto3
import stripe
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from boto3.dynamodb.conditions import Attr
from urllib.error import HTTPError

from handlers.common import app_url, redirect, request_method, request_path, response
from handlers.token_store import encrypt_access_token, read_access_token, read_expires_at

dynamodb = boto3.resource("dynamodb")
users_table = dynamodb.Table(os.environ["USERS_TABLE"])
sessions_table = dynamodb.Table(os.environ["SESSIONS_TABLE"])
scheduled_posts_table = dynamodb.Table(os.environ["SCHEDULED_POSTS_TABLE"])
thread_tokens_table = dynamodb.Table(os.environ["THREAD_TOKENS_TABLE"])
subscriptions_table = dynamodb.Table(os.environ["SUBSCRIPTIONS_TABLE"])
post_analytics_table = dynamodb.Table(os.environ["POST_ANALYTICS_TABLE"])
trial_eligibility_table = dynamodb.Table(os.environ["TRIAL_ELIGIBILITY_TABLE"])
stripe_events_table = dynamodb.Table(os.environ["STRIPE_EVENTS_TABLE"])
admins_table = dynamodb.Table(os.environ["ADMINS_TABLE"])
scheduler = boto3.client("scheduler")

ALLOWED_RETURN_TO = {
    "http://localhost:5173",
    "https://dev-s4s.aokigk.com",
    "https://s4s.aokigk.com",
}

SUPPORTED_LOCALES = {"ja", "en", "zh", "fil", "vi"}
SUPPORTED_TIMEZONES = {
    "Asia/Tokyo",
    "America/Los_Angeles",
    "Europe/London",
    "Asia/Manila",
    "Asia/Ho_Chi_Minh",
}
TRIAL_ENDING_SUBSCRIPTION_STATUSES = {"trialing", "active"}
TRIAL_SECONDS = 60 * 60 * 24 * 14
BOOTSTRAP_ADMIN_THREADS_USER_ID = os.environ.get("BOOTSTRAP_ADMIN_THREADS_USER_ID", "")

def safe_return_to(value: str | None) -> str:
    normalized = value.rstrip("/") if value else None
    configured_app_url = os.environ.get("APP_URL", "").rstrip("/")

    if normalized and normalized in ALLOWED_RETURN_TO | {configured_app_url}:
        return normalized
    return app_url("/")

def allowed_cors_origin(event) -> str:
    origin = event_header(event, "origin")
    configured_app_url = os.environ.get("APP_URL", "").rstrip("/")
    allowed_origins = ALLOWED_RETURN_TO | {configured_app_url}

    if origin and origin.rstrip("/") in allowed_origins:
        return origin.rstrip("/")

    return configured_app_url or "http://localhost:5173"

def get_cookie(event, name: str) -> str | None:
    # HTTP API v2 では event["cookies"] に入ることが多い
    for cookie in event.get("cookies") or []:
        if cookie.startswith(f"{name}="):
            return cookie.split("=", 1)[1]

    # 念のため headers.cookie も見る
    cookie_header = event.get("headers", {}).get("cookie") or ""
    for part in cookie_header.split(";"):
        part = part.strip()
        if part.startswith(f"{name}="):
            return part.split("=", 1)[1]

    return None

def trial_key_hash(threads_user_id: str) -> str:
    secret = os.environ["SESSION_SECRET"]
    return hashlib.sha256(f"{secret}:{threads_user_id}".encode("utf-8")).hexdigest()

def get_authenticated_session(event) -> dict | None:
    session_id = get_cookie(event, "session")

    if not session_id:
        return None

    session_res = sessions_table.get_item(Key={"session_id": session_id})
    session = session_res.get("Item")

    if session:
        session["session_id"] = session_id

    return session

def default_user(app_user_id: str) -> dict:
    now = int(time.time())
    return {
        "app_user_id": app_user_id,
        "threads_user_id": app_user_id,
        "display_name": "",
        "locale": "ja",
        "timezone": "Asia/Tokyo",
        "subscription_status": "trialing",
        "trial_end": now + 60 * 60 * 24 * 14,
        "user_status": "active",
        "created_at": now,
        "updated_at": now,
    }

def get_user(app_user_id: str) -> dict:
    user_res = users_table.get_item(Key={"app_user_id": app_user_id})
    user = user_res.get("Item")
    return user or default_user(app_user_id)

def get_trial_eligibility(threads_user_id: str) -> dict | None:
    trial_res = trial_eligibility_table.get_item(
        Key={"trial_key_hash": trial_key_hash(threads_user_id)}
    )
    return trial_res.get("Item")

def trial_already_used(threads_user_id: str) -> bool:
    trial = get_trial_eligibility(threads_user_id)
    return bool(trial and trial.get("trial_used"))

def get_token(threads_user_id: str) -> dict | None:
    token_res = thread_tokens_table.get_item(Key={"threads_user_id": threads_user_id})
    return token_res.get("Item")

def token_requires_reauth(token: dict | None) -> bool:
    if not token:
        return True
    if token.get("reauth_required") is True:
        return True

    try:
        access_token = read_access_token(token)
    except Exception as e:
        print("THREAD TOKEN DECRYPT ERROR", {
            "threads_user_id": token.get("threads_user_id"),
            "error": str(e),
        })
        return True

    if not access_token:
        return True
    return read_expires_at(token) <= int(time.time())

def has_subscription_entitlement(user: dict) -> bool:
    status = user.get("subscription_status", "trialing")
    if status == "active":
        return True

    if status != "trialing":
        return False

    return trial_end_for_user(user) > int(time.time())

def effective_subscription_status(user: dict) -> str:
    status = user.get("subscription_status", "trialing")
    if status == "trialing" and not has_subscription_entitlement(user):
        return "trial_expired"
    return status

def trial_started_at_for_user(user: dict) -> int:
    if user.get("trial_started_at"):
        return int(user["trial_started_at"])

    trial = get_trial_eligibility(user.get("threads_user_id", user["app_user_id"]))
    if trial and trial.get("first_trial_started_at"):
        return int(trial["first_trial_started_at"])

    return int(user.get("created_at") or int(time.time()))

def trial_end_for_user(user: dict) -> int:
    if user.get("trial_entitlement_ended_at"):
        return int(user["trial_entitlement_ended_at"])

    if user.get("trial_end"):
        return int(user["trial_end"])

    trial = get_trial_eligibility(user.get("threads_user_id", user["app_user_id"]))
    if trial and trial.get("trial_entitlement_ended_at"):
        return int(trial["trial_entitlement_ended_at"])
    if trial and trial.get("trial_end"):
        return int(trial["trial_end"])

    return trial_started_at_for_user(user) + TRIAL_SECONDS

def end_app_trial_for_account(app_user_id: str, now: int, reason: str) -> dict:
    user = get_user(app_user_id)
    threads_user_id = user.get("threads_user_id", app_user_id)

    try:
        trial_eligibility_table.update_item(
            Key={"trial_key_hash": trial_key_hash(threads_user_id)},
            UpdateExpression="""
                SET trial_end = :trial_end,
                    trial_entitlement_ended_at = :ended_at,
                    trial_ended_reason = :reason,
                    updated_at = :updated_at
            """,
            ExpressionAttributeValues={
                ":trial_end": now,
                ":ended_at": now,
                ":reason": reason,
                ":updated_at": now,
            },
        )
    except Exception as e:
        print("TRIAL ENTITLEMENT END UPDATE ERROR", {
            "app_user_id": app_user_id,
            "threads_user_id": threads_user_id,
            "error": str(e),
        })

    return {
        "trial_end": now,
        "trial_entitlement_ended_at": now,
        "trial_ended_reason": reason,
    }

def event_header(event, name: str) -> str | None:
    headers = event.get("headers") or {}
    target = name.lower()
    for key, value in headers.items():
        if key.lower() == target:
            return value
    return None

def request_body_bytes(event) -> bytes:
    body = event.get("body") or ""
    if event.get("isBase64Encoded"):
        return base64.b64decode(body)
    return body.encode("utf-8")

def stripe_field(value, name: str):
    if isinstance(value, dict):
        return value.get(name)
    return getattr(value, name, None)

def persist_stripe_subscription(
    *,
    app_user_id: str,
    stripe_customer_id: str | None,
    subscription,
    fallback_status: str | None = None,
) -> None:
    now = int(time.time())
    subscription_id = stripe_field(subscription, "id")
    status = stripe_field(subscription, "status") or fallback_status or "incomplete"
    current_period_end = stripe_field(subscription, "current_period_end")
    trial_end = stripe_field(subscription, "trial_end")

    item = {
        "app_user_id": app_user_id,
        "status": status,
        "updated_at": now,
    }

    if stripe_customer_id:
        item["stripe_customer_id"] = stripe_customer_id
    if subscription_id:
        item["stripe_subscription_id"] = subscription_id
    if current_period_end:
        item["current_period_end"] = int(current_period_end)
    if trial_end:
        item["trial_end"] = int(trial_end)

    existing = subscriptions_table.get_item(Key={"app_user_id": app_user_id}).get("Item")
    if existing and existing.get("created_at"):
        item["created_at"] = int(existing["created_at"])
    else:
        item["created_at"] = now

    subscriptions_table.put_item(Item={**(existing or {}), **item})

    user_updates = {
        "subscription_status": status,
        "stripe_customer_id": stripe_customer_id,
        "stripe_subscription_id": subscription_id,
    }

    if current_period_end:
        user_updates["current_period_end"] = int(current_period_end)
    if trial_end:
        user_updates["stripe_trial_end"] = int(trial_end)
    if status in TRIAL_ENDING_SUBSCRIPTION_STATUSES:
        user_updates.update(end_app_trial_for_account(app_user_id, now, "subscribed"))
    if status == "active":
        user_updates["user_status"] = "active"

    write_user(app_user_id, {key: value for key, value in user_updates.items() if value})

def get_user_context(event) -> tuple[dict | None, dict | None, dict | None]:
    session = get_authenticated_session(event)
    if not session:
        return None, None, None

    app_user_id = session.get("app_user_id") or session["threads_user_id"]
    user = get_user(app_user_id)
    token = get_token(session["threads_user_id"])
    return session, user, token

def user_guard(
    event,
    *,
    require_active: bool = False,
    require_threads_ready: bool = False,
    require_subscription: bool = False,
):
    session, user, token = get_user_context(event)

    if not session:
        return None, None, None, response(HTTPStatus.UNAUTHORIZED, {"message": "Unauthorized"})

    if user.get("user_status") == "deleted":
        return None, None, None, response(HTTPStatus.FORBIDDEN, {"message": "退会済みのアカウントです"})

    if require_active and user.get("user_status") != "active":
        return None, None, None, response(HTTPStatus.FORBIDDEN, {"message": "休止中は操作できません"})

    if require_threads_ready and token_requires_reauth(token):
        return None, None, None, response(HTTPStatus.BAD_REQUEST, {"message": "Threads再連携が必要です。再ログインしてください。"})

    if require_subscription and not has_subscription_entitlement(user):
        return None, None, None, response(HTTPStatus.PAYMENT_REQUIRED, {"message": "無料トライアルが終了しました。月額390円の登録が必要です"})

    return session, user, token, None

def developer_guard(event):
    session, user, token, error_response = user_guard(event)
    if error_response:
        return None, None, None, error_response

    if not is_admin_threads_user(session["threads_user_id"]):
        return None, None, None, response(HTTPStatus.FORBIDDEN, {"message": "Forbidden"})

    return session, user, token, None

def is_admin_threads_user(threads_user_id: str) -> bool:
    admin = admins_table.get_item(
        Key={"admin_threads_user_id": threads_user_id}
    ).get("Item")
    if admin and admin.get("enabled", True) is not False:
        return True

    # Bootstrap fallback until the admins table is populated in each environment.
    return bool(BOOTSTRAP_ADMIN_THREADS_USER_ID and threads_user_id == BOOTSTRAP_ADMIN_THREADS_USER_ID)

def scan_all(table, **kwargs) -> list[dict]:
    items = []
    while True:
        res = table.scan(**kwargs)
        items.extend(res.get("Items", []))
        last_key = res.get("LastEvaluatedKey")
        if not last_key:
            return items
        kwargs["ExclusiveStartKey"] = last_key

def metric_int(item: dict, *keys: str) -> int:
    for key in keys:
        if key in item and item.get(key) is not None:
            return int(item.get(key) or 0)
    return 0

def normalize_analytics(item: dict | None) -> dict | None:
    if not item:
        return None

    metrics = {
        "views": metric_int(item, "view_count", "views"),
        "likes": metric_int(item, "like_count", "likes"),
        "replies": metric_int(item, "reply_count", "replies"),
        "reposts": metric_int(item, "repost_count", "reposts"),
        "quotes": metric_int(item, "quote_count", "quotes"),
        "shares": metric_int(item, "share_count", "shares"),
    }
    engagement = metric_int(item, "engagement_total")
    if not engagement:
        engagement = metrics["likes"] + metrics["replies"] + metrics["reposts"] + metrics["quotes"] + metrics["shares"]

    return {
        "metrics": metrics,
        "engagement": engagement,
        "analytics_stage": item.get("analytics_stage", ""),
        "analytics_fetched_at": int(item.get("fetched_at", 0) or 0),
    }

def latest_analytics_by_post(app_user_id: str) -> dict[str, dict]:
    analytics_items = scan_all(
        post_analytics_table,
        FilterExpression=Attr("app_user_id").eq(app_user_id),
    )
    latest = {}
    for item in analytics_items:
        post_id = item.get("post_id")
        if not post_id:
            continue

        fetched_at = int(item.get("fetched_at", 0) or 0)
        current = latest.get(post_id)
        if not current or fetched_at >= int(current.get("fetched_at", 0) or 0):
            latest[post_id] = item

    return latest

def write_user(app_user_id: str, updates: dict) -> dict:
    now = int(time.time())
    current = get_user(app_user_id)
    item = {
        **current,
        **updates,
        "app_user_id": app_user_id,
        "threads_user_id": updates.get("threads_user_id", current.get("threads_user_id", app_user_id)),
        "updated_at": now,
    }

    if not item.get("created_at"):
        item["created_at"] = now

    users_table.put_item(Item=item)
    return item

def cancel_scheduler_if_present(post: dict):
    scheduler_name = post.get("scheduler_name")
    if not scheduler_name:
        return

    try:
        delete_schedule(scheduler_name)
    except Exception as e:
        print("DELETE SCHEDULER ERROR", {
            "post_id": post.get("post_id"),
            "scheduler_name": scheduler_name,
            "error": str(e),
        })

def cancel_scheduled_posts_for_pause(threads_user_id: str, now: int):
    posts = scan_all(
        scheduled_posts_table,
        FilterExpression=Attr("threads_user_id").eq(threads_user_id) & Attr("status").eq("scheduled"),
    )

    for post in posts:
        cancel_scheduler_if_present(post)
        scheduled_posts_table.update_item(
            Key={"post_id": post["post_id"]},
            ConditionExpression="#status = :scheduled",
            UpdateExpression="""
                SET #status = :canceled,
                    failure_reason = :failure_reason,
                    updated_at = :updated_at
            """,
            ExpressionAttributeNames={
                "#status": "status",
            },
            ExpressionAttributeValues={
                ":scheduled": "scheduled",
                ":canceled": "canceled",
                ":failure_reason": "休止により予約をキャンセルしました",
                ":updated_at": now,
            },
        )

def cancel_stripe_subscription_for_account(
    app_user_id: str,
    now: int,
    fallback_stripe_subscription_id: str | None = None,
) -> tuple[str, bool, str | None]:
    subscription = subscriptions_table.get_item(Key={"app_user_id": app_user_id}).get("Item")
    stripe_subscription_id = (subscription or {}).get("stripe_subscription_id") or fallback_stripe_subscription_id
    stripe_cancel_requires_admin_review = False
    stripe_cancel_error = None

    if stripe_subscription_id and (subscription or {}).get("status") != "canceled":
        try:
            stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
            stripe.Subscription.delete(stripe_subscription_id)
        except Exception as e:
            stripe_cancel_requires_admin_review = True
            stripe_cancel_error = str(e)[:1000]
            print("STRIPE SUBSCRIPTION CANCEL ERROR", {
                "app_user_id": app_user_id,
                "stripe_subscription_id": stripe_subscription_id,
                "error": str(e),
            })

    status = "cancel_pending_admin_review" if stripe_cancel_requires_admin_review else "canceled"
    subscription_item = {
        **(subscription or {"app_user_id": app_user_id}),
        "app_user_id": app_user_id,
        "status": status,
        "updated_at": now,
        "requires_admin_review": stripe_cancel_requires_admin_review,
        "admin_review_reason": "stripe_subscription_cancel_failed" if stripe_cancel_requires_admin_review else "",
    }
    if stripe_subscription_id:
        subscription_item["stripe_subscription_id"] = stripe_subscription_id

    if stripe_cancel_requires_admin_review:
        subscription_item["stripe_cancel_failed_at"] = now
        subscription_item["stripe_cancel_error"] = stripe_cancel_error or "unknown_error"
    else:
        subscription_item.pop("stripe_cancel_failed_at", None)
        subscription_item.pop("stripe_cancel_error", None)

    subscriptions_table.put_item(Item=subscription_item)
    return status, stripe_cancel_requires_admin_review, stripe_cancel_error

def summarize_http_error(error: HTTPError, stage: str) -> tuple[dict, str]:
    raw_body = error.read().decode("utf-8", errors="replace")
    error_code = None
    error_type = None

    try:
        parsed = json.loads(raw_body)
        error_payload = parsed.get("error", parsed)
        error_code = error_payload.get("code")
        error_type = error_payload.get("type")
    except Exception:
        pass

    summary = {
        "stage": stage,
        "status_code": error.code,
        "error_code": error_code,
        "error_type": error_type,
    }

    detail = f"{stage} failed status_code={error.code}"
    if error_code is not None:
        detail = f"{detail} error_code={error_code}"

    return summary, detail

def post_to_threads(user_id: str, access_token: str, text: str) -> dict:
    # 1. 投稿コンテナ作成
    create_url = f"https://graph.threads.net/v1.0/{user_id}/threads"

    create_data = urllib.parse.urlencode({
        "media_type": "TEXT",
        "text": text,
        "access_token": access_token,
    }).encode()

    create_req = urllib.request.Request(
        create_url,
        data=create_data,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    try:
        with urllib.request.urlopen(create_req) as res:
            create_body = json.loads(res.read())
    except HTTPError as e:
        summary, detail = summarize_http_error(e, "threads_create_error")
        print(summary)
        raise Exception(detail)

    creation_id = create_body.get("id")

    if not creation_id:
        raise Exception(f"Failed to create Threads container: {create_body}")

    # 2. 投稿公開
    publish_url = f"https://graph.threads.net/v1.0/{user_id}/threads_publish"

    publish_data = urllib.parse.urlencode({
        "creation_id": creation_id,
        "access_token": access_token,
    }).encode()

    publish_req = urllib.request.Request(
        publish_url,
        data=publish_data,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    try:
        with urllib.request.urlopen(publish_req) as res:
            publish_body = json.loads(res.read())
    except HTTPError as e:
        summary, detail = summarize_http_error(e, "threads_publish_error")
        print(summary)
        raise Exception(detail)

    return publish_body

DAILY_SCHEDULE_LIMIT = 3

def local_day_utc_range(scheduled_dt: datetime, user_timezone: str) -> tuple[str, str]:
    try:
        tz = ZoneInfo(user_timezone)
    except Exception:
        tz = ZoneInfo("Asia/Tokyo")

    local_dt = scheduled_dt.astimezone(tz)
    local_day_start = local_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    local_day_end = local_day_start + timedelta(days=1)

    utc_start = local_day_start.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    utc_end = local_day_end.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    return utc_start, utc_end


def count_scheduled_posts_on_day(
    threads_user_id: str,
    scheduled_dt: datetime,
    user_timezone: str,
    exclude_post_id: str | None = None,
) -> int:
    day_start, day_end = local_day_utc_range(scheduled_dt, user_timezone)

    filter_expression = (
        Attr("threads_user_id").eq(threads_user_id)
        & Attr("status").eq("scheduled")
        & Attr("scheduled_at").gte(day_start)
        & Attr("scheduled_at").lt(day_end)
    )

    if exclude_post_id:
        filter_expression = filter_expression & Attr("post_id").ne(exclude_post_id)

    scan_res = scheduled_posts_table.scan(
        FilterExpression=filter_expression,
    )

    return len(scan_res.get("Items", []))

def local_scheduled_date(scheduled_dt: datetime, user_timezone: str) -> str:
    try:
        tz = ZoneInfo(user_timezone)
    except Exception:
        tz = ZoneInfo("Asia/Tokyo")

    return scheduled_dt.astimezone(tz).date().isoformat()

def to_scheduler_time(scheduled_at: str) -> str:
    dt = datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

def create_schedule(scheduler_name: str, post_id: str, scheduled_at: str):
    scheduler.create_schedule(
        Name=scheduler_name,
        GroupName=os.environ.get("SCHEDULER_GROUP_NAME", "default"),
        ScheduleExpression=f"at({to_scheduler_time(scheduled_at)})",
        FlexibleTimeWindow={"Mode": "OFF"},
        Target={
            "Arn": os.environ["POST_EXECUTOR_FUNCTION_ARN"],
            "RoleArn": os.environ["SCHEDULER_INVOKE_ROLE_ARN"],
            "Input": json.dumps({"post_id": post_id}),
        },
    )


def delete_schedule(scheduler_name: str):
    scheduler.delete_schedule(
        Name=scheduler_name,
        GroupName=os.environ.get("SCHEDULER_GROUP_NAME", "default"),
    )

def handler(event, context):
    method = request_method(event)
    path = request_path(event)

    print("DEBUG EVENT", {
        "method": method,
        "path": path,
        "rawPath": event.get("rawPath"),
        "pathValue": event.get("path"),
        "routeKey": event.get("routeKey"),
    })

    if method == "OPTIONS":
        return response(
            HTTPStatus.NO_CONTENT,
            {},
            headers={
                "Access-Control-Allow-Origin": allowed_cors_origin(event),
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Allow-Headers": "content-type, authorization",
                "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
            },
        )

    if method == "GET" and path == "/auth/threads/start":
        client_id = os.environ["THREADS_CLIENT_ID"]
        redirect_uri = os.environ["THREADS_REDIRECT_URI"]

        query = event.get("queryStringParameters") or {}
        return_to = safe_return_to(query.get("return_to"))

        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": "threads_basic,threads_content_publish,threads_manage_insights",
            "response_type": "code",
            "state": return_to,
        }

        threads_auth_url = "https://threads.net/oauth/authorize?" + urllib.parse.urlencode(params)

        return redirect(threads_auth_url)

    if method == "GET" and path == "/auth/threads/callback":
        query = event.get("queryStringParameters") or {}
        code = query.get("code")

        if not code:
            return response(400, {"message": "Missing code"})

        client_id = os.environ["THREADS_CLIENT_ID"]
        client_secret = os.environ["THREADS_CLIENT_SECRET"]
        redirect_uri = os.environ["THREADS_REDIRECT_URI"]

        print("OAUTH CONFIG", {
            "client_id": client_id,
            "client_secret_len": len(client_secret),
            "redirect_uri": redirect_uri,
        })

        token_url = "https://graph.threads.net/oauth/access_token"

        data = urllib.parse.urlencode({
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code": code,
        }).encode()

        req = urllib.request.Request(
            token_url,
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        try:
            with urllib.request.urlopen(req) as res:
                body = json.loads(res.read())
                print("TOKEN RESPONSE", {
                    "has_access_token": bool(body.get("access_token")),
                    "user_id": body.get("user_id"),
                })

                access_token = body.get("access_token")

                # ▼ 短期トークンを長期トークンへ交換
                long_token_url = "https://graph.threads.net/access_token"

                long_token_params = urllib.parse.urlencode({
                    "grant_type": "th_exchange_token",
                    "client_secret": client_secret,
                    "access_token": access_token,
                })

                with urllib.request.urlopen(f"{long_token_url}?{long_token_params}") as long_res:
                    long_body = json.loads(long_res.read())

                print("LONG TOKEN RESPONSE", {
                    "has_access_token": bool(long_body.get("access_token")),
                    "expires_in": long_body.get("expires_in"),
                })

                access_token = long_body.get("access_token")
                expires_in = int(long_body.get("expires_in", 0))
                access_token_expires_at = int(time.time()) + expires_in

                # ▼ user_id取得
                user_info_url = f"https://graph.threads.net/v1.0/me?fields=id,username&access_token={access_token}"

                with urllib.request.urlopen(user_info_url) as res:
                    user_body = json.loads(res.read())
                    print("USER INFO", {
                        "has_id": bool(user_body.get("id")),
                        "has_username": bool(user_body.get("username")),
                    })

                    user_id = user_body.get("id")
                    username = user_body.get("username", "")

                session_id = secrets.token_urlsafe(32)
                app_user_id = user_id

                expires_at = int(time.time()) + 60 * 60 * 24 * 30

                now = int(time.time())

                existing_user = get_user(app_user_id)
                trial_started_at = trial_started_at_for_user(existing_user)
                trial_end = trial_end_for_user(existing_user)
                write_user(app_user_id, {
                    "threads_user_id": user_id,
                    "display_name": username,
                    "locale": existing_user.get("locale", "ja"),
                    "timezone": existing_user.get("timezone", "Asia/Tokyo"),
                    "subscription_status": existing_user.get("subscription_status", "trialing"),
                    "trial_started_at": trial_started_at,
                    "trial_end": int(trial_end),
                    "user_status": "active",
                })

                sessions_table.put_item(
                    Item={
                        "session_id": session_id,
                        "app_user_id": app_user_id,
                        "threads_user_id": user_id,
                        "created_at": now,
                        "expires_at": expires_at,
                    }
                )

                thread_tokens_table.put_item(
                    Item={
                        "app_user_id": app_user_id,
                        "threads_user_id": user_id,
                        "access_token_encrypted": encrypt_access_token(access_token),
                        "expires_at": access_token_expires_at,
                        "scopes": [
                            "threads_basic",
                            "threads_content_publish",
                            "threads_manage_insights",
                        ],
                        "reauth_required": False,
                        "updated_at": now,
                    }
                )

                try:
                    trial_eligibility_table.put_item(
                        Item={
                            "trial_key_hash": trial_key_hash(user_id),
                            "app_user_id": app_user_id,
                            "threads_user_id": user_id,
                            "trial_used": True,
                            "first_trial_started_at": now,
                            "trial_end": now + TRIAL_SECONDS,
                            "retained_until": now + 60 * 60 * 24 * 365 * 3,
                        },
                        ConditionExpression="attribute_not_exists(trial_key_hash)",
                    )
                except trial_eligibility_table.meta.client.exceptions.ConditionalCheckFailedException:
                    pass

                print("LOGIN SUCCESS", {
                    "user_id": user_id,
                    "has_session_id": bool(session_id),
                })

                return_to = safe_return_to(query.get("state"))

                return redirect(
                    return_to,
                    cookies=[
                        f"session={session_id}; HttpOnly; Secure; Path=/; SameSite=None"
                    ],
                )

        except HTTPError as e:
            summary, detail = summarize_http_error(e, "threads_oauth_callback_error")
            print("TOKEN ERROR", summary)

            return response(500, {
                "message": "Token exchange failed",
                "detail": detail,
            })

        except Exception as e:
            print("TOKEN ERROR", {
                "stage": "threads_oauth_callback_error",
                "error_type": type(e).__name__,
            })

            return response(500, {
                "message": "Token exchange failed",
                "detail": "threads_oauth_callback_error failed",
            })
        
    if method == "POST" and path == "/auth/logout":
        session_id = get_cookie(event, "session")
        if session_id:
            sessions_table.delete_item(Key={"session_id": session_id})

        return response(
            HTTPStatus.OK,
            {"ok": True},
            headers={
                "Set-Cookie": "session=; HttpOnly; Secure; Path=/; Max-Age=0; SameSite=None"
            },
        )

    if method == "GET" and path == "/me":
        session, user, token, error_response = user_guard(event)
        if error_response:
            return error_response

        reauth_required = token_requires_reauth(token)

        return response(
            HTTPStatus.OK,
            {
                "app_user_id": user["app_user_id"],
                "threads_user_id": session["threads_user_id"],
                "is_developer": is_admin_threads_user(session["threads_user_id"]),
                "locale": user.get("locale", "ja"),
                "timezone": user.get("timezone", "Asia/Tokyo"),
                "user_status": user.get("user_status", "active"),
                "subscription_status": effective_subscription_status(user),
                "trial_started_at": trial_started_at_for_user(user),
                "trial_end": trial_end_for_user(user),
                "has_subscription_entitlement": has_subscription_entitlement(user),
                "reauth_required": reauth_required,
                "token_expires_at": read_expires_at(token),
            },
        )

    if method == "PATCH" and path == "/me/settings":
        session, user, token, error_response = user_guard(event)
        if error_response:
            return error_response

        body = json.loads(event.get("body") or "{}")
        locale = body.get("locale", user.get("locale", "ja"))
        user_timezone = body.get("timezone", user.get("timezone", "Asia/Tokyo"))

        if locale not in SUPPORTED_LOCALES:
            return response(HTTPStatus.BAD_REQUEST, {"message": "Unsupported locale"})

        if user_timezone not in SUPPORTED_TIMEZONES:
            return response(HTTPStatus.BAD_REQUEST, {"message": "Unsupported timezone"})

        updated = write_user(user["app_user_id"], {
            "locale": locale,
            "timezone": user_timezone,
        })

        return response(HTTPStatus.OK, {
            "ok": True,
            "locale": updated["locale"],
            "timezone": updated["timezone"],
        })

    if method == "POST" and path == "/account/pause":
        session, user, token, error_response = user_guard(event)
        if error_response:
            return error_response

        now = int(time.time())
        cancel_scheduled_posts_for_pause(session["threads_user_id"], now)
        subscription_status, stripe_cancel_requires_admin_review, stripe_cancel_error = cancel_stripe_subscription_for_account(
            user["app_user_id"],
            now,
            user.get("stripe_subscription_id"),
        )

        user_updates = {
            "user_status": "paused",
            "paused_at": now,
            "subscription_status": subscription_status,
            **end_app_trial_for_account(user["app_user_id"], now, "paused"),
        }
        if stripe_cancel_requires_admin_review:
            user_updates.update({
                "requires_admin_review": True,
                "admin_review_reason": "stripe_subscription_cancel_failed",
                "stripe_cancel_failed_at": now,
                "stripe_cancel_error": stripe_cancel_error or "unknown_error",
            })

        updated = write_user(user["app_user_id"], {
            **user_updates,
        })
        return response(HTTPStatus.OK, {
            "ok": True,
            "user_status": updated["user_status"],
            "subscription_status": effective_subscription_status(updated),
            "has_subscription_entitlement": has_subscription_entitlement(updated),
        })

    if method == "POST" and path == "/account/resume":
        session, user, token, error_response = user_guard(event)
        if error_response:
            return error_response

        updated = write_user(user["app_user_id"], {"user_status": "active"})
        return response(HTTPStatus.OK, {"ok": True, "user_status": updated["user_status"]})

    if method == "DELETE" and path == "/account":
        session, user, token, error_response = user_guard(event)
        if error_response:
            return error_response

        app_user_id = user["app_user_id"]
        threads_user_id = session["threads_user_id"]
        now = int(time.time())

        posts_res = scheduled_posts_table.scan(
            FilterExpression=Attr("threads_user_id").eq(threads_user_id),
        )
        for post in posts_res.get("Items", []):
            if post.get("status") == "scheduled":
                cancel_scheduler_if_present(post)
            scheduled_posts_table.delete_item(Key={"post_id": post["post_id"]})

        analytics_res = post_analytics_table.scan(
            FilterExpression=Attr("app_user_id").eq(app_user_id),
        )
        for item in analytics_res.get("Items", []):
            post_analytics_table.delete_item(
                Key={
                    "post_id": item["post_id"],
                    "analytics_stage": item["analytics_stage"],
                }
            )

        _, stripe_cancel_requires_admin_review, stripe_cancel_error = cancel_stripe_subscription_for_account(
            app_user_id,
            now,
            user.get("stripe_subscription_id"),
        )

        thread_tokens_table.delete_item(Key={"threads_user_id": threads_user_id})
        sessions_table.delete_item(Key={"session_id": session["session_id"]})

        user_item = {
            "app_user_id": app_user_id,
            "threads_user_id": threads_user_id,
            "locale": user.get("locale", "ja"),
            "timezone": user.get("timezone", "Asia/Tokyo"),
            "subscription_status": "canceled",
            "user_status": "deleted",
            **end_app_trial_for_account(app_user_id, now, "deleted"),
            "created_at": int(user.get("created_at", now)),
            "updated_at": now,
            "deleted_at": now,
        }

        if stripe_cancel_requires_admin_review:
            user_item.update({
                "requires_admin_review": True,
                "admin_review_reason": "stripe_subscription_cancel_failed",
                "stripe_cancel_failed_at": now,
                "stripe_cancel_error": stripe_cancel_error or "unknown_error",
            })

        users_table.put_item(Item=user_item)

        trial_eligibility_table.update_item(
            Key={"trial_key_hash": trial_key_hash(threads_user_id)},
            UpdateExpression="""
                SET deleted_at = :deleted_at,
                    retained_until = :retained_until,
                    updated_at = :updated_at
            """,
            ExpressionAttributeValues={
                ":deleted_at": now,
                ":retained_until": now + 60 * 60 * 24 * 365 * 3,
                ":updated_at": now,
            },
        )

        return response(
            HTTPStatus.OK,
            {"ok": True},
            headers={
                "Set-Cookie": "session=; HttpOnly; Secure; Path=/; Max-Age=0; SameSite=None"
            },
        )

    if method == "GET" and path == "/developer/dashboard":
        session, user, token, error_response = developer_guard(event)
        if error_response:
            return error_response

        users = scan_all(users_table)
        subscriptions = scan_all(subscriptions_table)

        active_users = [item for item in users if item.get("user_status") != "deleted"]
        trial_users = [
            item for item in active_users
            if effective_subscription_status(item) == "trialing"
        ]
        subscribed_users = [
            item for item in active_users
            if item.get("subscription_status") == "active"
        ]

        review_items = []
        for item in subscriptions:
            if item.get("requires_admin_review") is not True:
                continue

            app_user_id = item.get("app_user_id", "")
            user_item = next((candidate for candidate in users if candidate.get("app_user_id") == app_user_id), {})
            review_items.append({
                "app_user_id": app_user_id,
                "threads_user_id": user_item.get("threads_user_id", ""),
                "display_name": user_item.get("display_name", ""),
                "status": item.get("status", ""),
                "reason": item.get("admin_review_reason", ""),
                "stripe_subscription_id": item.get("stripe_subscription_id", ""),
                "stripe_cancel_failed_at": int(item.get("stripe_cancel_failed_at", 0) or 0),
                "stripe_cancel_error": item.get("stripe_cancel_error", ""),
                "updated_at": int(item.get("updated_at", 0) or 0),
            })

        review_items.sort(
            key=lambda item: item.get("stripe_cancel_failed_at") or item.get("updated_at") or 0,
            reverse=True,
        )

        subscribed_count = len(subscribed_users)
        trial_count = len(trial_users)
        total_signup_count = len(active_users)
        conversion_base_count = trial_count + subscribed_count
        cvr = round((subscribed_count / conversion_base_count) * 100, 1) if conversion_base_count else 0

        return response(HTTPStatus.OK, {
            "metrics": {
                "total_users": total_signup_count,
                "trial_users": trial_count,
                "subscribed_users": subscribed_count,
                "conversion_base_users": conversion_base_count,
                "cvr": cvr,
                "admin_review_items": len(review_items),
                "subscriptions_total": len(subscriptions),
                "subscriptions_requiring_review": len([
                    item for item in subscriptions
                    if item.get("requires_admin_review") is True
                ]),
            },
            "admin_review_items": review_items[:100],
        })

    if method == "POST" and path == "/developer/admin-review/resolve":
        session, user, token, error_response = developer_guard(event)
        if error_response:
            return error_response

        body = json.loads(event.get("body") or "{}")
        app_user_id = body.get("app_user_id")
        if not app_user_id:
            return response(HTTPStatus.BAD_REQUEST, {"message": "app_user_id is required"})

        now = int(time.time())
        subscription = subscriptions_table.get_item(Key={"app_user_id": app_user_id}).get("Item")
        if not subscription:
            return response(HTTPStatus.NOT_FOUND, {"message": "subscription not found"})

        subscriptions_table.update_item(
            Key={"app_user_id": app_user_id},
            UpdateExpression="""
                SET requires_admin_review = :requires_admin_review,
                    #status = :status,
                    admin_review_resolved_at = :resolved_at,
                    admin_review_resolved_by = :resolved_by,
                    updated_at = :updated_at
            """,
            ExpressionAttributeNames={
                "#status": "status",
            },
            ExpressionAttributeValues={
                ":requires_admin_review": False,
                ":status": "canceled",
                ":resolved_at": now,
                ":resolved_by": session["threads_user_id"],
                ":updated_at": now,
            },
        )

        users_table.update_item(
            Key={"app_user_id": app_user_id},
            UpdateExpression="""
                SET requires_admin_review = :requires_admin_review,
                    admin_review_resolved_at = :resolved_at,
                    admin_review_resolved_by = :resolved_by,
                    updated_at = :updated_at
            """,
            ExpressionAttributeValues={
                ":requires_admin_review": False,
                ":resolved_at": now,
                ":resolved_by": session["threads_user_id"],
                ":updated_at": now,
            },
        )

        return response(HTTPStatus.OK, {
            "ok": True,
            "app_user_id": app_user_id,
        })
    
    if method == "POST" and path == "/threads/test-post":
        session, user, token, error_response = user_guard(event, require_active=True, require_threads_ready=True, require_subscription=True)
        if error_response:
            return error_response

        body = json.loads(event.get("body") or "{}")
        text = body.get("text", "").strip()

        if not text:
            return response(HTTPStatus.BAD_REQUEST, {"message": "Text is required"})

        try:
            access_token = read_access_token(token)

            result = post_to_threads(
                user_id=session["threads_user_id"],
                access_token=access_token,
                text=text,
            )

            return response(HTTPStatus.OK, {
                "ok": True,
                "result": result,
            })

        except Exception as e:
            print("THREADS POST ERROR", {
                "stage": "threads_test_post_error",
                "error": str(e),
            })

            return response(HTTPStatus.INTERNAL_SERVER_ERROR, {
                "message": "Threads post failed",
                "detail": str(e),
            })

    if method == "POST" and path == "/billing/checkout":
        session, user, token, error_response = user_guard(event)
        if error_response:
            return error_response

        stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
        include_trial = not trial_already_used(session["threads_user_id"])

        subscription_data = {
            "metadata": {
                "app_user_id": user["app_user_id"],
                "threads_user_id": session["threads_user_id"],
            },
        }

        if include_trial:
            subscription_data["trial_period_days"] = 14

        checkout_session = stripe.checkout.Session.create(
            mode="subscription",
            client_reference_id=user["app_user_id"],
            metadata={
                "app_user_id": user["app_user_id"],
                "threads_user_id": session["threads_user_id"],
            },
            line_items=[
                {
                    "price": os.environ["STRIPE_PRICE_ID"],
                    "quantity": 1,
                }
            ],
            subscription_data=subscription_data,
            success_url=app_url("/?billing=success"),
            cancel_url=app_url("/?billing=cancel"),
        )

        return response(HTTPStatus.OK, {
            "checkout_url": checkout_session.url,
            "trial_included": include_trial,
        })

    if method == "POST" and path == "/billing/portal":
        session, user, token, error_response = user_guard(event)
        if error_response:
            return error_response

        stripe_customer_id = user.get("stripe_customer_id")
        if not stripe_customer_id:
            return response(HTTPStatus.BAD_REQUEST, {"message": "Stripe customer not found"})

        stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
        portal_session = stripe.billing_portal.Session.create(
            customer=stripe_customer_id,
            return_url=app_url("/"),
        )

        return response(HTTPStatus.OK, {"portal_url": portal_session.url})

    if method == "POST" and path == "/stripe/webhook":
        stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
        signature = event_header(event, "stripe-signature")

        if not signature:
            return response(HTTPStatus.BAD_REQUEST, {"message": "Missing Stripe signature"})

        try:
            stripe_event = stripe.Webhook.construct_event(
                request_body_bytes(event),
                signature,
                os.environ["STRIPE_WEBHOOK_SECRET"],
            )
        except ValueError:
            return response(HTTPStatus.BAD_REQUEST, {"message": "Invalid Stripe payload"})
        except stripe.error.SignatureVerificationError:
            return response(HTTPStatus.BAD_REQUEST, {"message": "Invalid Stripe signature"})

        event_id = stripe_field(stripe_event, "id")
        event_type = stripe_field(stripe_event, "type")

        if not event_id or not event_type:
            return response(HTTPStatus.BAD_REQUEST, {"message": "Invalid Stripe event"})

        try:
            stripe_events_table.put_item(
                Item={
                    "stripe_event_id": event_id,
                    "event_type": event_type,
                    "received_at": int(time.time()),
                },
                ConditionExpression="attribute_not_exists(stripe_event_id)",
            )
        except stripe_events_table.meta.client.exceptions.ConditionalCheckFailedException:
            return response(HTTPStatus.OK, {"received": True, "duplicate": True})

        data = stripe_field(stripe_event, "data") or {}
        event_object = stripe_field(data, "object") or {}

        try:
            if event_type == "checkout.session.completed":
                app_user_id = stripe_field(event_object, "client_reference_id")
                metadata = stripe_field(event_object, "metadata") or {}
                app_user_id = app_user_id or stripe_field(metadata, "app_user_id")
                stripe_customer_id = stripe_field(event_object, "customer")
                subscription_id = stripe_field(event_object, "subscription")

                if app_user_id and subscription_id:
                    subscription = stripe.Subscription.retrieve(subscription_id)
                    persist_stripe_subscription(
                        app_user_id=app_user_id,
                        stripe_customer_id=stripe_customer_id,
                        subscription=subscription,
                    )

            if event_type in {
                "customer.subscription.created",
                "customer.subscription.updated",
                "customer.subscription.deleted",
            }:
                metadata = stripe_field(event_object, "metadata") or {}
                app_user_id = stripe_field(metadata, "app_user_id")
                status = stripe_field(event_object, "status")

                if app_user_id:
                    persist_stripe_subscription(
                        app_user_id=app_user_id,
                        stripe_customer_id=stripe_field(event_object, "customer"),
                        subscription=event_object,
                        fallback_status=status,
                    )
        except Exception:
            stripe_events_table.delete_item(Key={"stripe_event_id": event_id})
            raise

        return response(HTTPStatus.OK, {"received": True})

    if method == "POST" and path == "/scheduled-posts":
        try:
            session, user, token, error_response = user_guard(event, require_active=True, require_threads_ready=True, require_subscription=True)
            if error_response:
                return error_response

            body = json.loads(event.get("body") or "{}")
            print("SCHEDULE BODY", {
                "has_content": bool(body.get("content")),
                "has_scheduled_at": bool(body.get("scheduled_at")),
                "timezone": body.get("timezone"),
            })

            content = body.get("content", "").strip()
            scheduled_at = body.get("scheduled_at")
            user_timezone = body.get("timezone", "Asia/Tokyo")

            if not content:
                return response(HTTPStatus.BAD_REQUEST, {"message": "Content is required"})

            if not scheduled_at:
                return response(HTTPStatus.BAD_REQUEST, {"message": "scheduled_at is required"})

            try:
                scheduled_dt = datetime.fromisoformat(
                    scheduled_at.replace("Z", "+00:00")
                )
            except ValueError:
                return response(HTTPStatus.BAD_REQUEST, {"message": "Invalid scheduled_at"})

            now_dt = datetime.now(timezone.utc)

            if scheduled_dt <= now_dt:
                return response(HTTPStatus.BAD_REQUEST, {"message": "Past datetime is not allowed"})

            if (scheduled_dt - now_dt).total_seconds() < 5 * 60:
                return response(
                    HTTPStatus.BAD_REQUEST,
                    {"message": "Reservation must be at least 5 minutes later"},
                )
            
            max_schedule_dt = now_dt + timedelta(days=30)

            if scheduled_dt > max_schedule_dt:
                return response(
                    HTTPStatus.BAD_REQUEST,
                    {"message": "予約できるのは30日先までです"},
                )
            
            day_count = count_scheduled_posts_on_day(
                threads_user_id=session["threads_user_id"],
                scheduled_dt=scheduled_dt,
                user_timezone=user_timezone,
            )

            if day_count >= 3:
                return response(400, {"message": "1日3件までです"})

            if day_count >= DAILY_SCHEDULE_LIMIT:
                return response(
                    HTTPStatus.BAD_REQUEST,
                    {"message": "この日は予約上限の3件に達しています"},
                )

            post_id = secrets.token_urlsafe(16)
            scheduler_name = f"s4s-post-{post_id}"
            now = int(time.time())

            item = {
                "post_id": post_id,
                "app_user_id": user["app_user_id"],
                "threads_user_id": session["threads_user_id"],
                "content": content,
                "scheduled_at": scheduled_at,
                "scheduled_date": local_scheduled_date(scheduled_dt, user_timezone),
                "timezone": user_timezone,
                "status": "scheduled",
                "scheduler_name": scheduler_name,
                "created_at": now,
                "updated_at": now,
            }

            scheduled_posts_table.put_item(Item=item)

            try:
                create_schedule(
                    scheduler_name=scheduler_name,
                    post_id=post_id,
                    scheduled_at=scheduled_at,
                )
            except Exception as e:
                print("CREATE SCHEDULE ERROR", repr(e))

                return response(HTTPStatus.INTERNAL_SERVER_ERROR, {
                    "message": "Schedule creation failed",
                    "detail": str(e),
                })

            return response(HTTPStatus.OK, {
                "ok": True,
                "post": item,
            })

        except Exception as e:
            print("SCHEDULE POST ERROR", repr(e))
            return response(HTTPStatus.INTERNAL_SERVER_ERROR, {
                "message": "Schedule post failed",
                "detail": str(e),
            })
    
    if method == "PUT" and path.startswith("/scheduled-posts/"):
        new_scheduler_name = None

        try:
            post_id = path.split("/")[-1]

            session, user, token, error_response = user_guard(event, require_active=True, require_threads_ready=True, require_subscription=True)
            if error_response:
                return error_response

            body = json.loads(event.get("body") or "{}")

            content = body.get("content", "").strip()
            scheduled_at = body.get("scheduled_at")
            user_timezone = body.get("timezone", "Asia/Tokyo")

            if not content:
                return response(HTTPStatus.BAD_REQUEST, {"message": "Content is required"})

            if not scheduled_at:
                return response(HTTPStatus.BAD_REQUEST, {"message": "scheduled_at is required"})

            try:
                scheduled_dt = datetime.fromisoformat(
                    scheduled_at.replace("Z", "+00:00")
                )
            except ValueError:
                return response(HTTPStatus.BAD_REQUEST, {"message": "Invalid scheduled_at"})

            now_dt = datetime.now(timezone.utc)

            if scheduled_dt <= now_dt:
                return response(HTTPStatus.BAD_REQUEST, {"message": "Past datetime is not allowed"})

            if (scheduled_dt - now_dt).total_seconds() < 5 * 60:
                return response(
                    HTTPStatus.BAD_REQUEST,
                    {"message": "Reservation must be at least 5 minutes later"},
                )
            
            max_schedule_dt = now_dt + timedelta(days=30)

            if scheduled_dt > max_schedule_dt:
                return response(
                    HTTPStatus.BAD_REQUEST,
                    {"message": "予約できるのは30日先までです"},
                )

            # ▼ 既存post取得
            old_res = scheduled_posts_table.get_item(Key={"post_id": post_id})
            old_post = old_res.get("Item")

            if not old_post:
                return response(404, {"message": "Post not found"})

            if old_post["threads_user_id"] != session["threads_user_id"]:
                return response(403, {"message": "Forbidden"})

            if old_post["status"] != "scheduled":
                return response(400, {"message": "更新できる状態ではありません"})

            day_count = count_scheduled_posts_on_day(
                threads_user_id=session["threads_user_id"],
                scheduled_dt=scheduled_dt,
                user_timezone=user_timezone,
                exclude_post_id=post_id,
            )

            if day_count >= DAILY_SCHEDULE_LIMIT:
                return response(
                    HTTPStatus.BAD_REQUEST,
                    {"message": "この日は予約上限の3件に達しています"},
                )

            old_scheduler_name = old_post.get("scheduler_name")
            new_scheduler_name = f"s4s-post-{post_id}-{int(time.time())}"
            now = int(time.time())

            # ▼ ① 先に新Scheduler作成
            create_schedule(
                scheduler_name=new_scheduler_name,
                post_id=post_id,
                scheduled_at=scheduled_at,
            )

            try:
                # ▼ ② DynamoDB更新
                update_res = scheduled_posts_table.update_item(
                    Key={"post_id": post_id},
                    ConditionExpression="threads_user_id = :uid AND #status = :scheduled",
                    UpdateExpression="""
                        SET content = :content,
                            scheduled_at = :scheduled_at,
                            scheduled_date = :scheduled_date,
                            #timezone = :timezone,
                            scheduler_name = :scheduler_name,
                            updated_at = :updated_at
                    """,
                    ExpressionAttributeNames={
                        "#status": "status",
                        "#timezone": "timezone",
                    },
                    ExpressionAttributeValues={
                        ":uid": session["threads_user_id"],
                        ":scheduled": "scheduled",
                        ":content": content,
                        ":scheduled_at": scheduled_at,
                        ":scheduled_date": local_scheduled_date(scheduled_dt, user_timezone),
                        ":timezone": user_timezone,
                        ":scheduler_name": new_scheduler_name,
                        ":updated_at": now,
                    },
                    ReturnValues="ALL_NEW",
                )

            except Exception:
                # Dynamo更新に失敗したら、新しく作ったSchedulerを消す
                try:
                    delete_schedule(new_scheduler_name)
                except Exception as delete_new_error:
                    print("DELETE NEW SCHEDULER ERROR", {
                        "scheduler_name": new_scheduler_name,
                        "error": str(delete_new_error),
                    })
                raise

            # ▼ ③ 古いScheduler削除
            if old_scheduler_name:
                try:
                    delete_schedule(old_scheduler_name)
                except Exception as delete_old_error:
                    print("DELETE OLD SCHEDULER ERROR", {
                        "scheduler_name": old_scheduler_name,
                        "error": str(delete_old_error),
                    })

            updated_post = update_res["Attributes"]

            return response(HTTPStatus.OK, {
                "ok": True,
                "post": {
                    "post_id": updated_post["post_id"],
                    "threads_user_id": updated_post["threads_user_id"],
                    "content": updated_post["content"],
                    "scheduled_at": updated_post["scheduled_at"],
                    "scheduled_date": updated_post.get("scheduled_date"),
                    "timezone": updated_post["timezone"],
                    "status": updated_post["status"],
                    "scheduler_name": updated_post.get("scheduler_name"),
                    "created_at": int(updated_post["created_at"]),
                    "updated_at": int(updated_post["updated_at"]),
                },
            })

        except scheduled_posts_table.meta.client.exceptions.ConditionalCheckFailedException:
            if new_scheduler_name:
                try:
                    delete_schedule(new_scheduler_name)
                except Exception:
                    pass

            return response(
                HTTPStatus.BAD_REQUEST,
                {"message": "更新できる予約が見つからないか、すでに投稿済みです"},
            )

        except Exception as e:
            print("SCHEDULE UPDATE ERROR", repr(e))
            return response(HTTPStatus.INTERNAL_SERVER_ERROR, {
                "message": "Schedule update failed",
                "detail": str(e),
            })
        
    if method == "DELETE" and path.startswith("/scheduled-posts/"):
        try:
            post_id = path.split("/")[-1]

            session, user, token, error_response = user_guard(event, require_active=True)
            if error_response:
                return error_response

            # ▼ ① post取得
            post_res = scheduled_posts_table.get_item(Key={"post_id": post_id})
            post = post_res.get("Item")

            if not post:
                return response(404, {"message": "Post not found"})

            if post["threads_user_id"] != session["threads_user_id"]:
                return response(403, {"message": "Forbidden"})

            if post["status"] != "scheduled":
                return response(400, {"message": "削除できる状態ではありません"})

            scheduler_name = post.get("scheduler_name")

            # ▼ ② Scheduler削除（失敗しても続行）
            if scheduler_name:
                try:
                    delete_schedule(scheduler_name)
                except Exception as e:
                    print("DELETE SCHEDULER ERROR", {
                        "scheduler_name": scheduler_name,
                        "error": str(e),
                    })

            # ▼ ③ Dynamo更新（canceled）
            scheduled_posts_table.update_item(
                Key={"post_id": post_id},
                UpdateExpression="""
                    SET #status = :canceled,
                        updated_at = :updated_at
                """,
                ExpressionAttributeNames={
                    "#status": "status",
                },
                ExpressionAttributeValues={
                    ":canceled": "canceled",
                    ":updated_at": int(time.time()),
                },
            )

            return response(HTTPStatus.OK, {
                "ok": True,
                "post_id": post_id,
            })

        except Exception as e:
            print("SCHEDULE DELETE ERROR", repr(e))
            return response(HTTPStatus.INTERNAL_SERVER_ERROR, {
                "message": "Schedule delete failed",
                "detail": str(e),
            })
    
    if method == "GET" and path == "/scheduled-posts":
        try:
            session, user, token, error_response = user_guard(event)
            if error_response:
                return error_response

            scan_res = scheduled_posts_table.scan(
                FilterExpression="threads_user_id = :uid",
                ExpressionAttributeValues={
                    ":uid": session["threads_user_id"],
                },
            )

            items = scan_res.get("Items", [])

            items.sort(
                key=lambda item: item.get("scheduled_at", ""),
                reverse=True,
            )

            analytics_by_post = latest_analytics_by_post(user["app_user_id"])
            normalized_items = []
            for item in items:
                latest_analytics = normalize_analytics(analytics_by_post.get(item["post_id"]))
                normalized = {
                    "post_id": item["post_id"],
                    "app_user_id": item.get("app_user_id", item["threads_user_id"]),
                    "threads_user_id": item["threads_user_id"],
                    "content": item["content"],
                    "scheduled_at": item["scheduled_at"],
                    "scheduled_date": item.get("scheduled_date"),
                    "timezone": item.get("timezone", "Asia/Tokyo"),
                    "status": item.get("status", "scheduled"),
                    "failure_reason": item.get("failure_reason", ""),
                    "created_at": int(item.get("created_at", 0)),
                    "updated_at": int(item.get("updated_at", 0)),
                }
                if latest_analytics:
                    normalized.update(latest_analytics)
                normalized_items.append(normalized)

            return response(HTTPStatus.OK, {
                "items": normalized_items,
            })

        except Exception as e:
            print("SCHEDULE LIST ERROR", repr(e))
            return response(HTTPStatus.INTERNAL_SERVER_ERROR, {
                "message": "Schedule list failed",
                "detail": str(e),
            })

    if method == "GET" and path == "/analytics":
        session, user, token, error_response = user_guard(event)
        if error_response:
            return error_response

        posts = scan_all(
            scheduled_posts_table,
            FilterExpression=Attr("threads_user_id").eq(session["threads_user_id"]),
        )
        analytics_by_post = latest_analytics_by_post(user["app_user_id"])

        summary = {
            "views": 0,
            "likes": 0,
            "replies": 0,
            "reposts": 0,
            "quotes": 0,
            "shares": 0,
            "engagement": 0,
            "posted_posts": len([post for post in posts if post.get("status") == "posted"]),
            "analyzed_posts": 0,
        }
        items = []

        for post in posts:
            if post.get("status") != "posted":
                continue

            normalized_analytics = normalize_analytics(analytics_by_post.get(post["post_id"]))
            if not normalized_analytics:
                continue

            metrics = normalized_analytics["metrics"]
            summary["views"] += metrics["views"]
            summary["likes"] += metrics["likes"]
            summary["replies"] += metrics["replies"]
            summary["reposts"] += metrics["reposts"]
            summary["quotes"] += metrics["quotes"]
            summary["shares"] += metrics["shares"]
            summary["engagement"] += normalized_analytics["engagement"]
            summary["analyzed_posts"] += 1

            items.append({
                "post_id": post["post_id"],
                "content": post.get("content", ""),
                "scheduled_at": post.get("scheduled_at", ""),
                "posted_at": int(post.get("posted_at", 0) or 0),
                **normalized_analytics,
            })

        items.sort(key=lambda item: item.get("engagement", 0), reverse=True)

        return response(HTTPStatus.OK, {
            "summary": summary,
            "items": items,
        })

    return response(HTTPStatus.NOT_FOUND, {"message": "Not found"})
