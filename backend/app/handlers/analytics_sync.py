from http import HTTPStatus

from handlers.common import response


def handler(event, context):
    # TODO:
    # Fetch post insights only at 1h, 24h, and 72h stages for the target post.
    # Skip if subscription is invalid, user is paused/suspended, or Threads reauth is required.
    return response(HTTPStatus.OK, {"ok": True, "stage": "analytics_sync"})
