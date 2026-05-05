import os
import json
import time
import urllib.parse
import urllib.request
import boto3
from urllib.error import HTTPError

dynamodb = boto3.resource("dynamodb")
thread_tokens_table = dynamodb.Table(os.environ["THREAD_TOKENS_TABLE"])

REFRESH_THRESHOLD_SECONDS = 60 * 60 * 24 * 30


def now_ts() -> int:
    return int(time.time())


def refresh_threads_token(access_token: str) -> dict:
    client_secret = os.environ["THREADS_CLIENT_SECRET"]

    url = "https://graph.threads.net/refresh_access_token"

    params = urllib.parse.urlencode({
        "grant_type": "th_refresh_token",
        "access_token": access_token,
        "client_secret": client_secret,
    })

    req = urllib.request.Request(
        f"{url}?{params}",
        method="GET",
    )

    try:
        with urllib.request.urlopen(req) as res:
            return json.loads(res.read())
    except HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        print({
            "stage": "threads_token_refresh_error",
            "status_code": e.code,
            "error_body": error_body,
        })
        raise Exception(f"Threads token refresh failed: {error_body}")


def handler(event, context):
    now = now_ts()
    threshold = now + REFRESH_THRESHOLD_SECONDS

    print("TOKEN REFRESH START", {
        "threshold": threshold,
    })

    scan_res = thread_tokens_table.scan()
    items = scan_res.get("Items", [])

    refreshed = 0
    skipped = 0
    failed = 0

    for item in items:
        threads_user_id = item.get("threads_user_id")
        access_token = item.get("access_token")
        expires_at = int(item.get("access_token_expires_at", 0))

        if not threads_user_id or not access_token:
            skipped += 1
            continue

        if item.get("reauth_required") is True:
            skipped += 1
            continue

        if expires_at > threshold:
            skipped += 1
            continue

        try:
            body = refresh_threads_token(access_token)

            new_access_token = body.get("access_token")
            expires_in = int(body.get("expires_in", 0))

            if not new_access_token or not expires_in:
                raise Exception("Refresh response missing access_token or expires_in")

            thread_tokens_table.update_item(
                Key={"threads_user_id": threads_user_id},
                UpdateExpression="""
                    SET access_token = :access_token,
                        access_token_expires_at = :expires_at,
                        reauth_required = :reauth_required,
                        updated_at = :updated_at
                """,
                ExpressionAttributeValues={
                    ":access_token": new_access_token,
                    ":expires_at": now + expires_in,
                    ":reauth_required": False,
                    ":updated_at": now,
                },
            )

            refreshed += 1

            print("TOKEN REFRESH SUCCESS", {
                "threads_user_id": threads_user_id,
                "expires_in": expires_in,
            })

        except Exception as e:
            failed += 1

            print("TOKEN REFRESH FAILED", {
                "threads_user_id": threads_user_id,
                "error": str(e),
            })

            thread_tokens_table.update_item(
                Key={"threads_user_id": threads_user_id},
                UpdateExpression="""
                    SET reauth_required = :reauth_required,
                        updated_at = :updated_at
                """,
                ExpressionAttributeValues={
                    ":reauth_required": True,
                    ":updated_at": now,
                },
            )

    print("TOKEN REFRESH END", {
        "total": len(items),
        "refreshed": refreshed,
        "skipped": skipped,
        "failed": failed,
    })

    return {
        "ok": True,
        "total": len(items),
        "refreshed": refreshed,
        "skipped": skipped,
        "failed": failed,
    }