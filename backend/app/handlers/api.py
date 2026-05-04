import os
import urllib.parse
from http import HTTPStatus
import urllib.request
import json
import secrets

from handlers.common import app_url, redirect, request_method, request_path, response

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

    if method == "GET" and path == "/auth/threads/start":
        client_id = os.environ["THREADS_CLIENT_ID"]
        redirect_uri = "https://api-dev.s4s.aokigk.com/auth/threads/callback"

        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": "threads_basic,threads_content_publish,threads_manage_insights",
            "response_type": "code",
            "state": "dev",
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

                print("LOGIN SUCCESS", {
                    "user_id": user_id,
                    "session_id": session_id,
                })

                return redirect(
                    app_url("/"),
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

    if method == "POST" and path == "/billing/checkout":
        # TODO: Create Stripe Checkout Session in subscription mode with 14-day trial.
        return response(HTTPStatus.OK, {"checkout_url": app_url("/billing/mock-checkout")})

    if method == "POST" and path == "/billing/portal":
        # TODO: Create Stripe Billing Portal session for payment method management.
        return response(HTTPStatus.OK, {"portal_url": app_url("/billing/mock-portal")})

    if method == "POST" and path == "/stripe/webhook":
        # TODO: Verify Stripe signature and store stripe_event_id before processing.
        return response(HTTPStatus.OK, {"received": True})

    if path.startswith("/scheduled-posts"):
        return response(HTTPStatus.OK, {"items": []})

    if path.startswith("/analytics"):
        return response(HTTPStatus.OK, {"summary": {}, "items": []})

    return response(HTTPStatus.NOT_FOUND, {"message": "Not found"})
