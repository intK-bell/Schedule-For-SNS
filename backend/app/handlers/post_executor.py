import os
import json
import time
import urllib.parse
import urllib.request
import boto3
from urllib.error import HTTPError

from handlers.token_store import read_access_token, read_expires_at

dynamodb = boto3.resource("dynamodb")

scheduled_posts_table = dynamodb.Table(os.environ["SCHEDULED_POSTS_TABLE"])
thread_tokens_table = dynamodb.Table(os.environ["THREAD_TOKENS_TABLE"])


def now_ts() -> int:
    return int(time.time())

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

def to_user_failure_reason(error_text: str) -> str:
    if not error_text:
        return "投稿に失敗しました。再度予約してください。"

    lowered = error_text.lower()

    if "error validating access token" in lowered or "error_code=190" in lowered:
        return "Threadsとの連携期限が切れています。再ログインしてください。"

    if "invalid oauth access token" in lowered:
        return "Threadsとの連携が無効になっています。再ログインしてください。"

    if "missing required parameter" in lowered or "invalid parameter" in lowered:
        return "投稿内容に問題がある可能性があります。本文を確認してください。"

    if "rate limit" in lowered or "error_code=4" in lowered or "error_code=17" in lowered:
        return "Threads側の制限により投稿できませんでした。時間をおいて再度予約してください。"

    if "http error 400" in lowered:
        return "投稿リクエストに問題があり、投稿できませんでした。再度予約してください。"

    return "投稿に失敗しました。再度予約してください。"

def post_to_threads(user_id: str, access_token: str, text: str) -> dict:
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
        raise Exception("Failed to create Threads container")

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
            return json.loads(res.read())
    except HTTPError as e:
        summary, detail = summarize_http_error(e, "threads_publish_error")
        print(summary)
        raise Exception(detail)


def get_access_token_by_threads_user_id(threads_user_id: str) -> str:
    token_res = thread_tokens_table.get_item(
        Key={"threads_user_id": threads_user_id}
    )

    token = token_res.get("Item")

    if not token:
        raise Exception("Threads token not found")

    if token.get("reauth_required") is True:
        raise Exception("Threads reauth required")

    expires_at = read_expires_at(token)
    if expires_at and expires_at <= now_ts():
        raise Exception("Threads token expired error_code=190")

    access_token = read_access_token(token)

    if not access_token:
        raise Exception("Access token not found")

    print("THREAD TOKEN SELECTED", {
        "threads_user_id": threads_user_id,
        "has_expires_at": bool(expires_at),
        "expires_at": expires_at,
        "reauth_required": bool(token.get("reauth_required", False)),
    })

    return access_token

def handler(event, context):
    print("POST EXECUTOR START", {
        "has_post_id": bool(event.get("post_id")),
    })

    post_id = event.get("post_id")

    if not post_id:
        return {"ok": False, "message": "post_id is required"}

    post_res = scheduled_posts_table.get_item(
        Key={"post_id": post_id}
    )

    post = post_res.get("Item")

    if not post:
        return {"ok": False, "message": "post not found"}

    try:
        scheduled_posts_table.update_item(
            Key={"post_id": post_id},
            ConditionExpression="#status = :scheduled",
            UpdateExpression="""
                SET #status = :posting,
                    updated_at = :updated_at
            """,
            ExpressionAttributeNames={
                "#status": "status",
            },
            ExpressionAttributeValues={
                ":scheduled": "scheduled",
                ":posting": "posting",
                ":updated_at": now_ts(),
            },
        )

    except scheduled_posts_table.meta.client.exceptions.ConditionalCheckFailedException:
        return {
            "ok": False,
            "message": "post is not scheduled",
        }

    try:
        threads_user_id = post["threads_user_id"]
        content = post["content"]

        access_token = get_access_token_by_threads_user_id(threads_user_id)

        result = post_to_threads(
            user_id=threads_user_id,
            access_token=access_token,
            text=content,
        )

        threads_media_id = result.get("id", "")

        scheduled_posts_table.update_item(
            Key={"post_id": post_id},
            UpdateExpression="""
                SET #status = :posted,
                    threads_media_id = :threads_media_id,
                    posted_at = :posted_at,
                    updated_at = :updated_at
            """,
            ExpressionAttributeNames={
                "#status": "status",
            },
            ExpressionAttributeValues={
                ":posted": "posted",
                ":threads_media_id": threads_media_id,
                ":posted_at": now_ts(),
                ":updated_at": now_ts(),
            },
        )

        return {
            "ok": True,
            "post_id": post_id,
            "threads_media_id": threads_media_id,
        }

    except Exception as e:
        error_text = str(e)
        user_failure_reason = to_user_failure_reason(error_text)

        print("POST EXECUTOR ERROR", {
            "post_id": post_id,
            "error": error_text,
            "user_failure_reason": user_failure_reason,
        })

        scheduled_posts_table.update_item(
            Key={"post_id": post_id},
            UpdateExpression="""
                SET #status = :failed,
                    failure_reason = :failure_reason,
                    failure_detail = :failure_detail,
                    updated_at = :updated_at
            """,
            ExpressionAttributeNames={
                "#status": "status",
            },
            ExpressionAttributeValues={
                ":failed": "failed",
                ":failure_reason": user_failure_reason,
                ":failure_detail": error_text[:1000],
                ":updated_at": now_ts(),
            },
        )

        return {
            "ok": False,
            "post_id": post_id,
            "message": user_failure_reason,
        }
