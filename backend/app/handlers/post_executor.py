import os
import json
import time
import urllib.parse
import urllib.request
import boto3
from urllib.error import HTTPError

dynamodb = boto3.resource("dynamodb")

scheduled_posts_table = dynamodb.Table(os.environ["SCHEDULED_POSTS_TABLE"])
sessions_table = dynamodb.Table(os.environ["SESSIONS_TABLE"])


def now_ts() -> int:
    return int(time.time())


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
        error_body = e.read().decode("utf-8", errors="replace")
        print({
            "stage": "threads_create_error",
            "status_code": e.code,
            "error_body": error_body,
        })
        raise Exception(f"Threads create failed: {error_body}")

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
        error_body = e.read().decode("utf-8", errors="replace")
        print({
            "stage": "threads_publish_error",
            "status_code": e.code,
            "error_body": error_body,
        })
        raise Exception(f"Threads publish failed: {error_body}")


def get_access_token_by_threads_user_id(threads_user_id: str) -> str:
    # MVP用：sessions_table から threads_user_id に紐づく token を探す
    # 将来的には thread_tokens_table に分離する
    scan_res = sessions_table.scan(
        FilterExpression="threads_user_id = :uid",
        ExpressionAttributeValues={
            ":uid": threads_user_id,
        },
    )

    items = scan_res.get("Items", [])

    if not items:
        raise Exception("Session token not found")

    items.sort(
        key=lambda item: int(item.get("created_at", 0)),
        reverse=True,
    )

    latest_session = items[0]

    print("TOKEN SESSION SELECTED", {
        "created_at": int(latest_session.get("created_at", 0)),
        "has_access_token_expires_at": bool(latest_session.get("access_token_expires_at")),
        "access_token_expires_at": int(latest_session.get("access_token_expires_at", 0)),
    })

    access_token = latest_session.get("access_token")

    if not access_token:
        raise Exception("Access token not found")

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
        print("POST EXECUTOR ERROR", {
            "post_id": post_id,
            "error": str(e),
        })

        scheduled_posts_table.update_item(
            Key={"post_id": post_id},
            UpdateExpression="""
                SET #status = :failed,
                    failure_reason = :failure_reason,
                    updated_at = :updated_at
            """,
            ExpressionAttributeNames={
                "#status": "status",
            },
            ExpressionAttributeValues={
                ":failed": "failed",
                ":failure_reason": str(e),
                ":updated_at": now_ts(),
            },
        )

        return {
            "ok": False,
            "post_id": post_id,
            "message": str(e),
        }