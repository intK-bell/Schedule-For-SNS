from http import HTTPStatus

from handlers.common import app_url, redirect, request_method, request_path, response


def handler(event, context):
    method = request_method(event)
    path = request_path(event)

    if method == "GET" and path == "/auth/threads/start":
        # TODO: Build Threads OAuth authorization URL with state and scopes.
        return redirect(app_url("/auth/connecting"))

    if method == "GET" and path == "/auth/threads/callback":
        # TODO: Exchange code for token, store encrypted token, issue HttpOnly session cookie.
        return redirect(app_url("/app"))

    if method == "POST" and path == "/auth/logout":
        return response(HTTPStatus.OK, {"ok": True})

    if method == "GET" and path == "/me":
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
