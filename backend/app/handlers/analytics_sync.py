import json
import os
import time
import urllib.parse
import urllib.request
from http import HTTPStatus
from urllib.error import HTTPError

import boto3

from handlers.common import response
from handlers.token_store import read_access_token, read_expires_at

dynamodb = boto3.resource("dynamodb")

scheduled_posts_table = dynamodb.Table(os.environ["SCHEDULED_POSTS_TABLE"])
post_analytics_table = dynamodb.Table(os.environ["POST_ANALYTICS_TABLE"])
thread_tokens_table = dynamodb.Table(os.environ["THREAD_TOKENS_TABLE"])
users_table = dynamodb.Table(os.environ["USERS_TABLE"])

TRIAL_SECONDS = 60 * 60 * 24 * 14
INSIGHT_METRICS = ["views", "likes", "replies", "reposts", "quotes", "shares"]
VALID_STAGES = {"1h", "24h", "72h"}


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


def has_subscription_entitlement(user: dict) -> bool:
    status = user.get("subscription_status", "trialing")
    if status == "active":
        return True
    if status != "trialing":
        return False
    trial_started_at = int(user.get("trial_started_at") or user.get("created_at") or now_ts())
    trial_end = int(user.get("trial_end") or trial_started_at + TRIAL_SECONDS)
    return trial_end > now_ts()


def get_access_token(threads_user_id: str) -> str:
    token = thread_tokens_table.get_item(Key={"threads_user_id": threads_user_id}).get("Item")
    if not token:
        raise Exception("Threads token not found")
    if token.get("reauth_required") is True:
        raise Exception("Threads reauth required")

    expires_at = read_expires_at(token)
    if expires_at and expires_at <= now_ts():
        raise Exception("Threads token expired")

    access_token = read_access_token(token)
    if not access_token:
        raise Exception("Access token not found")
    return access_token


def insight_value(metric_item: dict) -> int:
    values = metric_item.get("values") or []
    if values:
        value = values[-1].get("value", 0)
    else:
        value = metric_item.get("value", 0)

    if isinstance(value, dict):
        return int(sum(int(item or 0) for item in value.values()))
    return int(value or 0)


def fetch_post_insights(threads_media_id: str, access_token: str) -> dict[str, int]:
    params = urllib.parse.urlencode({
        "metric": ",".join(INSIGHT_METRICS),
        "access_token": access_token,
    })
    url = f"https://graph.threads.net/v1.0/{threads_media_id}/insights?{params}"

    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req) as res:
            body = json.loads(res.read())
    except HTTPError as e:
        summary, detail = summarize_http_error(e, "threads_insights_error")
        print(summary)
        raise Exception(detail)

    metrics = {metric: 0 for metric in INSIGHT_METRICS}
    for item in body.get("data", []):
        name = item.get("name")
        if name in metrics:
            metrics[name] = insight_value(item)

    return metrics


def handler(event, context):
    post_id = event.get("post_id")
    analytics_stage = event.get("analytics_stage", "manual")

    if not post_id:
        return response(HTTPStatus.BAD_REQUEST, {"message": "post_id is required"})
    if analytics_stage not in VALID_STAGES and analytics_stage != "manual":
        return response(HTTPStatus.BAD_REQUEST, {"message": "Invalid analytics_stage"})

    post = scheduled_posts_table.get_item(Key={"post_id": post_id}).get("Item")
    if not post:
        return response(HTTPStatus.NOT_FOUND, {"message": "post not found"})
    if post.get("status") != "posted":
        return response(HTTPStatus.OK, {"ok": True, "skipped": "post_not_posted"})

    threads_media_id = post.get("threads_media_id")
    if not threads_media_id:
        return response(HTTPStatus.OK, {"ok": True, "skipped": "missing_threads_media_id"})

    app_user_id = post.get("app_user_id") or post["threads_user_id"]
    user = users_table.get_item(Key={"app_user_id": app_user_id}).get("Item") or {}
    if user.get("user_status", "active") != "active":
        return response(HTTPStatus.OK, {"ok": True, "skipped": "user_not_active"})
    if not has_subscription_entitlement(user):
        return response(HTTPStatus.OK, {"ok": True, "skipped": "subscription_inactive"})

    access_token = get_access_token(post["threads_user_id"])
    metrics = fetch_post_insights(threads_media_id, access_token)
    fetched_at = now_ts()
    engagement_total = (
        metrics["likes"]
        + metrics["replies"]
        + metrics["reposts"]
        + metrics["quotes"]
        + metrics["shares"]
    )

    post_analytics_table.put_item(
        Item={
            "post_id": post_id,
            "analytics_stage": analytics_stage,
            "app_user_id": app_user_id,
            "threads_user_id": post["threads_user_id"],
            "threads_media_id": threads_media_id,
            "view_count": metrics["views"],
            "like_count": metrics["likes"],
            "reply_count": metrics["replies"],
            "repost_count": metrics["reposts"],
            "quote_count": metrics["quotes"],
            "share_count": metrics["shares"],
            "engagement_total": engagement_total,
            "fetched_at": fetched_at,
        }
    )

    return response(HTTPStatus.OK, {
        "ok": True,
        "post_id": post_id,
        "analytics_stage": analytics_stage,
        "metrics": metrics,
        "engagement_total": engagement_total,
    })
