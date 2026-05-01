from http import HTTPStatus

from handlers.common import response


def handler(event, context):
    # TODO:
    # 1. Conditionally update scheduled_posts.status from scheduled to posting.
    # 2. Re-check subscription/user status and reauth_required.
    # 3. Publish via Threads API.
    # 4. Mark posted or failed. Do not auto-retry to avoid duplicate posts.
    return response(HTTPStatus.OK, {"ok": True, "stage": "publish_post"})
