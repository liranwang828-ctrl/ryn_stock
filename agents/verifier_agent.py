import sys, os, json, argparse
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils import get_logger, fetch_with_retry, atomic_write_json
log = get_logger(__name__)
from agents.protocol import BASE, VERIFIED_PATH, FINDINGS_DIR, EXIT_OK, EXIT_FAIL

PRICE_THRESHOLD  = 0.005
VOLUME_THRESHOLD = 0.05

def pct_delta(a, b):
    """Return absolute percentage difference between two values."""
    if b == 0:
        return float("inf")
    return abs(a - b) / abs(b)

def verify_fields(primary_fields, secondary_fields):
    """Cross-validate primary fields against secondary source, flagging disputes."""
    result = {}
    for field, pdata in primary_fields.items():
        val_a = pdata["value"]
        if val_a is None:
            result[field] = {**pdata, "verified": False, "dispute_reason": "primary null"}
            continue
        if field not in secondary_fields:
            result[field] = {**pdata, "verified": True, "note": "no secondary"}
            continue
        val_b = secondary_fields[field]["value"]
        threshold = PRICE_THRESHOLD if "price" in field or field == "close" else VOLUME_THRESHOLD
        delta = pct_delta(val_a, val_b)
        if delta > threshold:
            result[field] = {**pdata, "source_a": val_a, "source_b": val_b,
                             "verified": False, "dispute_reason": f"delta {delta:.2%}"}
        else:
            result[field] = {**pdata, "source_a": val_a, "source_b": val_b, "verified": True}
    return result

def main():
    """Parse args, verify fields against secondary source, and write verified JSON."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--field", default=None)
    parser.add_argument("--round", type=int, default=0)
    args = parser.parse_args()

    primary   = json.load(open(os.path.join(BASE, "data_raw_primary.json"), encoding="utf-8"))
    secondary = json.load(open(os.path.join(BASE, "data_raw_secondary.json"), encoding="utf-8"))
    sec_avail = secondary.get("secondary_available", False)
    sec_fields = secondary["fields"] if sec_avail else {}

    if args.field:
        pf = {args.field: primary["fields"].get(args.field, {"value": None})}
        sf = {args.field: sec_fields.get(args.field, {})} if sec_avail else {}
        verified = verify_fields(pf, sf)
        out = {"msg_type": "verify_response", "from": "VerifierAgent",
               "target_field": args.field,
               "result": "verified" if verified[args.field]["verified"] else "disputed",
               "detail": verified[args.field],
               "timestamp": datetime.now(timezone.utc).isoformat()}
        os.makedirs(FINDINGS_DIR, exist_ok=True)
        atomic_write_json(out, os.path.join(FINDINGS_DIR, f"verifier_r{args.round}_{args.field}.json"), indent=2)
    else:
        verified_fields = verify_fields(primary["fields"], sec_fields)
        out = {"symbol": primary["symbol"],
               "timestamp": datetime.now(timezone.utc).isoformat(),
               "secondary_available": sec_avail,
               "fields": verified_fields}
        atomic_write_json(out, VERIFIED_PATH, indent=2)

if __name__ == "__main__":
    main()
