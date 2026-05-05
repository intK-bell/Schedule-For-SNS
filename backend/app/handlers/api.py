import os
import urllib.parse
from http import HTTPStatus
import urllib.request
import json
import secrets
import time
import boto3
import stripe
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from boto3.dynamodb.conditions import Attr
from urllib.error import HTTPError

from handlers.common import app_url, redirect, request_method, request_path, response

dynamodb = boto3.resource("dynamodb")
sessions_table = dynamodb.Table(os.environ["SESSIONS_TABLE"])
scheduled_posts_table = dynamodb.Table(os.environ["SCHEDULED_POSTS_TABLE"])
thread_tokens_table = dynamodb.Table(os.environ["THREAD_TOKENS_TABLE"])
scheduler = boto3.client("scheduler")

ALLOWED_RETURN_TO = [
    "http://localhost:5173",
    "https://dev.dbbr2u09r9szv.amplifyapp.com",
    "https://s4s.aokigk.com",
]

def safe_return_to(value: str | None) -> str:
    if value in ALLOWED_RETURN_TO:
        return value
    return app_url("/")

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
        error_body = e.read().decode("utf-8", errors="replace")
        print({
            "stage": "threads_create_error",
            "status_code": e.code,
            "error_body": error_body,
        })
        raise

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
        error_body = e.read().decode("utf-8", errors="replace")
        print({
            "stage": "threads_publish_error",
            "status_code": e.code,
            "error_body": error_body,
        })
        raise

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
                "Access-Control-Allow-Origin": "http://localhost:5173",
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Allow-Headers": "content-type, authorization",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            },
        )

    if method == "GET" and path == "/auth/threads/start":
        client_id = os.environ["THREADS_CLIENT_ID"]
        redirect_uri = "https://api-dev.s4s.aokigk.com/auth/threads/callback"

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
        redirect_uri = "https://api-dev.s4s.aokigk.com/auth/threads/callback"

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
                    print("USER INFO", user_body)

                    user_id = user_body.get("id")

                session_id = secrets.token_urlsafe(32)

                expires_at = int(time.time()) + 60 * 60 * 24 * 30

                now = int(time.time())

                sessions_table.put_item(
                    Item={
                        "session_id": session_id,
                        "threads_user_id": user_id,
                        "created_at": now,
                        "expires_at": expires_at,
                    }
                )

                thread_tokens_table.put_item(
                    Item={
                        "threads_user_id": user_id,
                        "access_token": access_token,
                        "access_token_expires_at": access_token_expires_at,
                        "reauth_required": False,
                        "updated_at": now,
                    }
                )

                print("LOGIN SUCCESS", {
                    "user_id": user_id,
                    "session_id": session_id,
                })

                return_to = safe_return_to(query.get("state"))

                return redirect(
                    return_to,
                    cookies=[
                        f"session={session_id}; HttpOnly; Secure; Path=/; SameSite=None"
                    ],
                )

        except Exception as e:
            error_body = ""
            if hasattr(e, "read"):
                error_body = e.read().decode("utf-8")

            print("TOKEN ERROR", str(e), error_body)

            return response(500, {
                "message": "Token exchange failed",
                "detail": error_body,
            })
        
    if method == "POST" and path == "/auth/logout":
        return response(
            HTTPStatus.OK,
            {"ok": True},
            headers={
                "Set-Cookie": "session=; HttpOnly; Secure; Path=/; Max-Age=0; SameSite=None"
            },
        )

    if method == "GET" and path == "/me":
        session_id = get_cookie(event, "session")

        if not session_id:
            return response(HTTPStatus.UNAUTHORIZED, {"message": "Unauthorized"})

        session_res = sessions_table.get_item(Key={"session_id": session_id})
        session = session_res.get("Item")

        if not session:
            return response(HTTPStatus.UNAUTHORIZED, {"message": "Unauthorized"})

        token_res = thread_tokens_table.get_item(
            Key={"threads_user_id": session["threads_user_id"]}
        )

        token = token_res.get("Item")

        reauth_required = False

        if not token:
            reauth_required = True
        elif token.get("reauth_required") is True:
            reauth_required = True

        return response(
            HTTPStatus.OK,
            {
                "app_user_id": session["threads_user_id"],
                "user_status": "active",
                "subscription_status": "trialing",
                "reauth_required": reauth_required,
            },
        )
    
    if method == "POST" and path == "/threads/test-post":
        session_id = get_cookie(event, "session")

        if not session_id:
            return response(HTTPStatus.UNAUTHORIZED, {"message": "Unauthorized"})

        session_res = sessions_table.get_item(Key={"session_id": session_id})
        session = session_res.get("Item")

        if not session:
            return response(HTTPStatus.UNAUTHORIZED, {"message": "Unauthorized"})

        body = json.loads(event.get("body") or "{}")
        text = body.get("text", "").strip()

        if not text:
            return response(HTTPStatus.BAD_REQUEST, {"message": "Text is required"})

        try:
            token_res = thread_tokens_table.get_item(
                Key={"threads_user_id": session["threads_user_id"]}
            )

            token = token_res.get("Item")

            if not token or not token.get("access_token"):
                return response(HTTPStatus.BAD_REQUEST, {
                    "message": "Threads連携情報が見つかりません。再ログインしてください。"
                })

            if token.get("reauth_required") is True:
                return response(HTTPStatus.BAD_REQUEST, {
                    "message": "Threads再連携が必要です。再ログインしてください。"
                })

            result = post_to_threads(
                user_id=session["threads_user_id"],
                access_token=token["access_token"],
                text=text,
            )

            return response(HTTPStatus.OK, {
                "ok": True,
                "result": result,
            })

        except Exception as e:
            error_body = ""
            if hasattr(e, "read"):
                error_body = e.read().decode("utf-8")

            print("THREADS POST ERROR", str(e), error_body)

            return response(HTTPStatus.INTERNAL_SERVER_ERROR, {
                "message": "Threads post failed",
                "detail": error_body or str(e),
            })

    if method == "POST" and path == "/billing/checkout":
        stripe.api_key = os.environ["STRIPE_SECRET_KEY"]

        checkout_session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[
                {
                    "price": os.environ["STRIPE_PRICE_ID"],
                    "quantity": 1,
                }
            ],
            subscription_data={
                "trial_period_days": 14,
            },
            success_url=app_url("/billing/success"),
            cancel_url=app_url("/billing/cancel"),
        )

        return response(HTTPStatus.OK, {"checkout_url": checkout_session.url})

    if method == "POST" and path == "/billing/portal":
        # TODO: Create Stripe Billing Portal session for payment method management.
        return response(HTTPStatus.OK, {"portal_url": app_url("/billing/mock-portal")})

    if method == "POST" and path == "/stripe/webhook":
        # TODO: Verify Stripe signature and store stripe_event_id before processing.
        return response(HTTPStatus.OK, {"received": True})

    if method == "POST" and path == "/scheduled-posts":
        try:
            session_id = get_cookie(event, "session")

            if not session_id:
                return response(HTTPStatus.UNAUTHORIZED, {"message": "Unauthorized"})

            session_res = sessions_table.get_item(Key={"session_id": session_id})
            session = session_res.get("Item")

            if not session:
                return response(HTTPStatus.UNAUTHORIZED, {"message": "Unauthorized"})

            body = json.loads(event.get("body") or "{}")
            print("SCHEDULE BODY", body)

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
                "threads_user_id": session["threads_user_id"],
                "content": content,
                "scheduled_at": scheduled_at,
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

            session_id = get_cookie(event, "session")

            if not session_id:
                return response(HTTPStatus.UNAUTHORIZED, {"message": "Unauthorized"})

            session_res = sessions_table.get_item(Key={"session_id": session_id})
            session = session_res.get("Item")

            if not session:
                return response(HTTPStatus.UNAUTHORIZED, {"message": "Unauthorized"})

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

            session_id = get_cookie(event, "session")

            if not session_id:
                return response(HTTPStatus.UNAUTHORIZED, {"message": "Unauthorized"})

            session_res = sessions_table.get_item(Key={"session_id": session_id})
            session = session_res.get("Item")

            if not session:
                return response(HTTPStatus.UNAUTHORIZED, {"message": "Unauthorized"})

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
            session_id = get_cookie(event, "session")

            if not session_id:
                return response(HTTPStatus.UNAUTHORIZED, {"message": "Unauthorized"})

            session_res = sessions_table.get_item(Key={"session_id": session_id})
            session = session_res.get("Item")

            if not session:
                return response(HTTPStatus.UNAUTHORIZED, {"message": "Unauthorized"})

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

            normalized_items = []
            for item in items:
                normalized_items.append({
                    "post_id": item["post_id"],
                    "threads_user_id": item["threads_user_id"],
                    "content": item["content"],
                    "scheduled_at": item["scheduled_at"],
                    "timezone": item.get("timezone", "Asia/Tokyo"),
                    "status": item.get("status", "scheduled"),
                    "failure_reason": item.get("failure_reason", ""),
                    "created_at": int(item.get("created_at", 0)),
                    "updated_at": int(item.get("updated_at", 0)),
                })

            return response(HTTPStatus.OK, {
                "items": normalized_items,
            })

        except Exception as e:
            print("SCHEDULE LIST ERROR", repr(e))
            return response(HTTPStatus.INTERNAL_SERVER_ERROR, {
                "message": "Schedule list failed",
                "detail": str(e),
            })

    if path.startswith("/analytics"):
        return response(HTTPStatus.OK, {"summary": {}, "items": []})

    return response(HTTPStatus.NOT_FOUND, {"message": "Not found"})
