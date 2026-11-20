"""
Paradise Donut Company - store menu API
IS 531 Serverless Project - Waylan Abbott

Routes (API Gateway HTTP API -> this Lambda):
  GET /stores               -> every store (Query PK = "STORES")
  GET /items?store=<id>     -> one store's items (Query PK = "STORE#<id>")

Both routes use DynamoDB Query (never Scan). The boto3 Table resource
deserializes DynamoDB's typed format ({"S": "Glazed"}) into plain values.
"""
import json
import os
import re
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key

TABLE = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "*")
STORE_ID = re.compile(r"^[a-z0-9-]{1,40}$")


def _json_default(value):
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    raise TypeError(f"Not serializable: {type(value)}")


def _response(status, body):
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
            "Cache-Control": "max-age=60",
        },
        "body": json.dumps(body, default=_json_default),
    }


def _query_all(pk):
    """Query one partition, following pagination."""
    items, kwargs = [], {"KeyConditionExpression": Key("PK").eq(pk)}
    while True:
        page = TABLE.query(**kwargs)
        items.extend(page["Items"])
        if "LastEvaluatedKey" not in page:
            return items
        kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]


def list_stores():
    stores = _query_all("STORES")
    return _response(200, {"stores": [
        {k: v for k, v in s.items() if k not in ("PK", "SK")} for s in stores
    ]})


def list_items(store_id):
    if not store_id or not STORE_ID.match(store_id):
        return _response(400, {"error": "Pass a valid ?store= value, e.g. ?store=provo"})

    # ---- The DynamoDB Query that loads one store's menu ----
    rows = _query_all(f"STORE#{store_id}")

    store = next((r for r in rows if r["SK"] == "META"), None)
    items = [{k: v for k, v in r.items() if k not in ("PK", "SK")}
             for r in rows if r["SK"].startswith("ITEM#")]
    if store is None and not items:
        return _response(404, {"error": f"Store '{store_id}' not found"})

    items.sort(key=lambda i: (i.get("sortOrder", 999), i.get("name", "")))
    meta = {k: v for k, v in (store or {}).items() if k not in ("PK", "SK")}
    return _response(200, {"store": meta, "count": len(items), "items": items})


def handler(event, context):
    path = event.get("rawPath", "")
    params = event.get("queryStringParameters") or {}
    print(json.dumps({"path": path, "params": params}))

    try:
        if path.endswith("/stores"):
            return list_stores()
        if path.endswith("/items"):
            return list_items((params.get("store") or "").strip().lower())
        return _response(404, {"error": "Not found"})
    except Exception as exc:  # surfaced in CloudWatch + error alarm
        print(f"ERROR: {exc!r}")
        raise
