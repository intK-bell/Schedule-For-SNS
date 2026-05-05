import os
import urllib.parse
from http import HTTPStatus
import urllib.request
import json
import secrets
import time
import boto3
import stripe
from datetime import datetime, timezone

from handlers.common import app_url, redirect, request_method, request_path, response

dynamodb = boto3.resource("dynamodb")
sessions_table = dynamodb.Table(os.environ["SESSIONS_TABLE"])
scheduled_posts_table = dynamodb.Table(os.environ["SCHEDULED_POSTS_TABLE"])

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

    with urllib.request.urlopen(create_req) as res:
        create_body = json.loads(res.read())

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

    with urllib.request.urlopen(publish_req) as res:
        publish_body = json.loads(res.read())

    return publish_body

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
                print("TOKEN RESPONSE", body)

                access_token = body.get("access_token")

                # ▼ user_id取得
                user_info_url = f"https://graph.threads.net/v1.0/me?fields=id,username&access_token={access_token}"

                with urllib.request.urlopen(user_info_url) as res:
                    user_body = json.loads(res.read())
                    print("USER INFO", user_body)

                    user_id = user_body.get("id")

                session_id = secrets.token_urlsafe(32)

                expires_at = int(time.time()) + 60 * 60 * 24 * 30

                sessions_table.put_item(
                    Item={
                        "session_id": session_id,
                        "threads_user_id": user_id,
                        "access_token": access_token,
                        "created_at": int(time.time()),
                        "expires_at": expires_at,
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
        cookies = event.get("cookies") or []

        session_id = None
        for cookie in cookies:
            if cookie.startswith("session="):
                session_id = cookie.split("=", 1)[1]

        if not session_id:
            return response(HTTPStatus.UNAUTHORIZED, {"message": "Unauthorized"})

        return response(
            HTTPStatus.OK,
            {
                "app_user_id": "demo",
                "user_status": "active",
                "subscription_status": "trialing",
                "reauth_required": False,
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
            result = post_to_threads(
                user_id=session["threads_user_id"],
                access_token=session["access_token"],
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

            post_id = secrets.token_urlsafe(16)
            now = int(time.time())

            item = {
                "post_id": post_id,
                "threads_user_id": session["threads_user_id"],
                "content": content,
                "scheduled_at": scheduled_at,
                "timezone": user_timezone,
                "status": "scheduled",
                "created_at": now,
                "updated_at": now,
            }

            scheduled_posts_table.put_item(Item=item)

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

            now = int(time.time())

            update_res = scheduled_posts_table.update_item(
                Key={"post_id": post_id},
                ConditionExpression="threads_user_id = :uid AND #status = :scheduled",
                UpdateExpression="""
                    SET content = :content,
                        scheduled_at = :scheduled_at,
                        #timezone = :timezone,
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
                    ":updated_at": now,
                },
                ReturnValues="ALL_NEW",
            )

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
                    "created_at": int(updated_post["created_at"]),
                    "updated_at": int(updated_post["updated_at"]),
                },
            })

        except scheduled_posts_table.meta.client.exceptions.ConditionalCheckFailedException:
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
    
    if method == "GET" and path == "/scheduled-posts":
        return response(HTTPStatus.OK, {"items": []})

    if path.startswith("/analytics"):
        return response(HTTPStatus.OK, {"summary": {}, "items": []})

    return response(HTTPStatus.NOT_FOUND, {"message": "Not found"})
