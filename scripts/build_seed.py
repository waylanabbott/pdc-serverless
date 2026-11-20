"""Turn data/menu.json into DynamoDB batch-write-item request files (25 items max each).

Usage: python3 scripts/build_seed.py <TableName> <ImageBaseUrl> <outDir>
Only uses the standard library, so no pip installs are needed.
"""
import json, sys, pathlib

table, image_base, out_dir = sys.argv[1], sys.argv[2].rstrip("/"), pathlib.Path(sys.argv[3])
data = json.loads((pathlib.Path(__file__).parent.parent / "data/menu.json").read_text())

def av(v):  # Python value -> DynamoDB attribute value
    if isinstance(v, bool): return {"BOOL": v}
    if isinstance(v, (int, float)): return {"N": str(v)}
    return {"S": str(v)}

rows = []
for s in data["stores"]:
    sid = s["storeId"]
    rows.append({"PK": "STORES", "SK": f"STORE#{sid}", **s})
    rows.append({"PK": f"STORE#{sid}", "SK": "META", **s})
    for order, m in enumerate(data["menus"][sid], 1):
        c = data["catalog"][m["itemId"]]
        rows.append({
            "PK": f"STORE#{sid}", "SK": f"ITEM#{m['itemId']}",
            "storeId": sid, "itemId": m["itemId"], "name": c["name"],
            "description": c["description"], "calories": c["calories"],
            "price": m["price"], "currency": s["currency"], "rating": m["rating"],
            "imageUrl": f"{image_base}/images/{c['image']}", "sortOrder": order,
            **({"tag": m["tag"]} if "tag" in m else {}),
        })

out_dir.mkdir(parents=True, exist_ok=True)
for f in out_dir.glob("batch-*.json"): f.unlink()
for i in range(0, len(rows), 25):
    req = {table: [{"PutRequest": {"Item": {k: av(v) for k, v in r.items()}}} for r in rows[i:i+25]]}
    (out_dir / f"batch-{i//25+1}.json").write_text(json.dumps(req, indent=1))
print(f"{len(rows)} rows -> {len(range(0, len(rows), 25))} batch file(s) in {out_dir}")
