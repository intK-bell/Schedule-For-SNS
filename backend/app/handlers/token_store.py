import base64
import os

import boto3

kms = boto3.client("kms")

TOKEN_ENCRYPTION_CONTEXT = {
    "purpose": "threads_access_token",
}


def encrypt_access_token(access_token: str) -> str:
    result = kms.encrypt(
        KeyId=os.environ["THREAD_TOKEN_KMS_KEY_ID"],
        Plaintext=access_token.encode("utf-8"),
        EncryptionContext=TOKEN_ENCRYPTION_CONTEXT,
    )
    return base64.b64encode(result["CiphertextBlob"]).decode("ascii")


def decrypt_access_token(access_token_encrypted: str) -> str:
    result = kms.decrypt(
        CiphertextBlob=base64.b64decode(access_token_encrypted),
        EncryptionContext=TOKEN_ENCRYPTION_CONTEXT,
    )
    return result["Plaintext"].decode("utf-8")


def read_access_token(token_item: dict | None) -> str | None:
    if not token_item:
        return None

    encrypted = token_item.get("access_token_encrypted")
    if encrypted:
        return decrypt_access_token(encrypted)

    # Temporary backward compatibility for tokens saved before KMS encryption.
    return token_item.get("access_token")


def read_expires_at(token_item: dict | None) -> int:
    if not token_item:
        return 0

    return int(token_item.get("expires_at") or token_item.get("access_token_expires_at") or 0)
