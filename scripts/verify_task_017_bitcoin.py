"""Independent stdlib verifier for the TASK-017 Bitcoin fixture."""

import hashlib
import json
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "docs/05_QA_Validation/fixtures/FX-BTC-UTXO-001"


def _canonical_hash(value: object) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(body).hexdigest()


def _load_artifact(package: Path, provider: dict[str, object]) -> dict[str, object]:
    artifact = (package / str(provider["artifact_file"])).resolve()
    if not artifact.is_relative_to(package.resolve()) or not artifact.is_file():
        raise ValueError("provider artifact missing")
    body = artifact.read_bytes()
    if hashlib.sha256(body).hexdigest() != provider["artifact_sha256"]:
        raise ValueError("provider artifact hash mismatch")
    value = json.loads(body)
    if not isinstance(value, dict):
        raise ValueError("provider artifact must be an object")
    return value


def _rest_transaction(body: dict[str, object]) -> dict[str, object]:
    status = body["status"]
    inputs = body["vin"]
    outputs = body["vout"]
    if (
        not isinstance(status, dict)
        or not isinstance(inputs, list)
        or not isinstance(outputs, list)
    ):
        raise ValueError("invalid REST transaction")
    return {
        "transaction_id": body["txid"],
        "block_height": status["block_height"],
        "block_hash": status["block_hash"],
        "block_time": status["block_time"],
        "fee_sat": body["fee"],
        "inputs": [
            {
                "prevout": {
                    "transaction_id": item["txid"],
                    "vout": item["vout"],
                    "value_sat": item["prevout"]["value"],
                    "script_type": item["prevout"]["scriptpubkey_type"],
                    "address": item["prevout"]["scriptpubkey_address"],
                },
                "sequence": item["sequence"],
            }
            for item in inputs
        ],
        "outputs": [
            {
                "vout": index,
                "value_sat": item["value"],
                "script_type": item["scriptpubkey_type"],
                "address": item["scriptpubkey_address"],
            }
            for index, item in enumerate(outputs)
        ],
    }


def _publicnode_transaction(body: dict[str, object]) -> dict[str, object]:
    result = body["result"]
    if not isinstance(result, dict):
        raise ValueError("invalid PublicNode transaction")
    return {
        "transaction_id": result["txid"],
        "block_hash": result["blockhash"],
        "block_time": result["blocktime"],
        "inputs": [
            {
                "transaction_id": item["txid"],
                "vout": item["vout"],
                "sequence": item["sequence"],
            }
            for item in result["vin"]
        ],
        "outputs": [
            {
                "vout": item["n"],
                "value_sat": int(Decimal(str(item["value"])) * Decimal(100_000_000)),
                "address": item["address"],
            }
            for item in result["vout"]
        ],
    }


def _public_projection(root: dict[str, object]) -> dict[str, object]:
    return {
        "transaction_id": root["transaction_id"],
        "block_hash": root["block_hash"],
        "block_time": root["block_time"],
        "inputs": [
            {
                "transaction_id": item["prevout"]["transaction_id"],
                "vout": item["prevout"]["vout"],
                "sequence": item["sequence"],
            }
            for item in root["inputs"]
        ],
        "outputs": [
            {
                "vout": item["vout"],
                "value_sat": item["value_sat"],
                "address": item["address"],
            }
            for item in root["outputs"]
        ],
    }


def _rest_hop(
    body: dict[str, object],
    spent_transaction_id: str,
    spent_vout: int,
) -> dict[str, object]:
    inputs = body["vin"]
    outputs = body["vout"]
    status = body["status"]
    if (
        not isinstance(inputs, list)
        or not isinstance(outputs, list)
        or not isinstance(status, dict)
    ):
        raise ValueError("invalid REST spend transaction")
    matches = [
        (index, item)
        for index, item in enumerate(inputs)
        if item["txid"] == spent_transaction_id and item["vout"] == spent_vout
    ]
    if len(matches) != 1:
        raise ValueError("spent outpoint is not unique")
    spending_vin, spent_input = matches[0]
    return {
        "spent_transaction_id": spent_transaction_id,
        "spent_vout": spent_vout,
        "spent_value_sat": spent_input["prevout"]["value"],
        "spending_transaction_id": body["txid"],
        "spending_vin": spending_vin,
        "block_height": status["block_height"],
        "fee_sat": body["fee"],
        "created_outputs": [
            {
                "vout": index,
                "value_sat": item["value"],
                "script_type": item["scriptpubkey_type"],
                "address": item["scriptpubkey_address"],
            }
            for index, item in enumerate(outputs)
        ],
    }


def _validate_path(
    root: dict[str, object],
    hops: list[dict[str, object]],
) -> None:
    previous_transaction_id = root["transaction_id"]
    previous_outputs = root["outputs"]
    for expected_depth, hop in enumerate(hops, start=1):
        if hop["depth"] != expected_depth:
            raise ValueError("spend path depths are not contiguous")
        if hop["spent_transaction_id"] != previous_transaction_id:
            raise ValueError("spend path chain differs")
        matches = [item for item in previous_outputs if item["vout"] == hop["spent_vout"]]
        if len(matches) != 1 or matches[0]["value_sat"] != hop["spent_value_sat"]:
            raise ValueError("spend path output differs")
        previous_transaction_id = hop["spending_transaction_id"]
        previous_outputs = hop["created_outputs"]


def verify(package: Path = PACKAGE) -> str:
    replay = json.loads((package / "raw-replay.json").read_text(encoding="utf-8"))
    request = json.loads((package / "analysis-request.json").read_text(encoding="utf-8"))
    expected = json.loads((package / "expected.json").read_text(encoding="utf-8"))
    tx = replay["transaction"]
    root_artifacts = {
        item["provider_id"]: _load_artifact(package, item) for item in tx["providers"]
    }
    root = _rest_transaction(root_artifacts["mempool.space"])
    supporting = _rest_transaction(root_artifacts["blockstream.info"])
    if root != supporting:
        raise ValueError("root provider projections differ")
    if _publicnode_transaction(root_artifacts["publicnode.bitcoin"]) != _public_projection(root):
        raise ValueError("PublicNode projection differs")
    replay_root = {key: tx[key] for key in root}
    if replay_root != root:
        raise ValueError("root replay differs from artifacts")

    derived_hops: list[dict[str, object]] = []
    for hop_index, hop in enumerate(replay["spend_path"]):
        hop_artifacts = {
            item["provider_id"]: _load_artifact(package, item) for item in hop["providers"]
        }
        mempool = _rest_hop(
            hop_artifacts["mempool.space"],
            hop["spent_transaction_id"],
            hop["spent_vout"],
        )
        blockstream = _rest_hop(
            hop_artifacts["blockstream.info"],
            hop["spent_transaction_id"],
            hop["spent_vout"],
        )
        if mempool != blockstream:
            raise ValueError("spend provider projections differ")
        mempool["depth"] = hop_index + 1
        replay_hop = {key: hop[key] for key in mempool}
        if replay_hop != mempool:
            raise ValueError("spend replay differs from artifacts")
        derived_hops.append(mempool)
    _validate_path(root, derived_hops)

    inputs = root["inputs"]
    outputs = root["outputs"]
    input_sum = sum(item["prevout"]["value_sat"] for item in inputs)
    output_sum = sum(item["value_sat"] for item in outputs)
    if input_sum - output_sum != root["fee_sat"]:
        raise ValueError("fee equation mismatch")
    outpoints = [(item["prevout"]["transaction_id"], item["prevout"]["vout"]) for item in inputs]
    if len(outpoints) != len(set(outpoints)):
        raise ValueError("duplicate spent outpoint")
    start_vout = request["inputs"]["start_vout"]
    max_hops = request["inputs"]["max_hops"]
    if start_vout not in {item["vout"] for item in outputs}:
        raise ValueError("start_vout does not exist")
    if not derived_hops:
        raise ValueError("confirmed fixture requires spend-path evidence")
    path = [
        item
        for item in derived_hops
        if item["depth"] <= max_hops and (item["depth"] > 1 or item["spent_vout"] == start_vout)
    ]
    fact = {
        "transaction_id": root["transaction_id"],
        "network": request["inputs"]["network"],
        "block_height": root["block_height"],
        "block_hash": root["block_hash"],
        "input_count": len(inputs),
        "output_count": len(outputs),
        "input_sum_sat": input_sum,
        "output_sum_sat": output_sum,
        "fee_sat": input_sum - output_sum,
        "spent_outpoints": [
            {
                "transaction_id": item["prevout"]["transaction_id"],
                "vout": item["prevout"]["vout"],
                "value_sat": item["prevout"]["value_sat"],
            }
            for item in inputs
        ],
        "created_utxos": [
            {
                "transaction_id": root["transaction_id"],
                "vout": item["vout"],
                "value_sat": item["value_sat"],
                "script_type": item["script_type"],
                "address": item["address"],
            }
            for item in outputs
        ],
        "start_outpoint": {
            "transaction_id": root["transaction_id"],
            "vout": start_vout,
        },
        "max_hops": max_hops,
        "spend_path": [
            {
                "depth": item["depth"],
                "spent_outpoint": {
                    "transaction_id": item["spent_transaction_id"],
                    "vout": item["spent_vout"],
                    "value_sat": item["spent_value_sat"],
                },
                "spending_transaction_id": item["spending_transaction_id"],
                "spending_vin": item["spending_vin"],
                "created_outpoints": [
                    {
                        "transaction_id": item["spending_transaction_id"],
                        "vout": output["vout"],
                        "value_sat": output["value_sat"],
                    }
                    for output in item["created_outputs"]
                ],
            }
            for item in path
        ],
        "frontier_outpoints": [
            {
                "transaction_id": path[-1]["spending_transaction_id"],
                "vout": output["vout"],
                "value_sat": output["value_sat"],
            }
            for output in path[-1]["created_outputs"]
        ],
    }
    if fact != expected["expected_results"][0]["value"]:
        raise ValueError("expected fact mismatch")
    return _canonical_hash(fact)


def main() -> None:
    first = verify()
    second = verify()
    if first != second:
        raise ValueError("Bitcoin verifier is not deterministic")
    print(f"PASS TASK-017 independent verifier twice · {first}")


if __name__ == "__main__":
    main()
