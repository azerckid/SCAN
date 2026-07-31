"""Strict TASK-016 DeFi lending replay parsing and raw-first fact reconstruction."""

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic.experimental.missing_sentinel import MISSING
from pydantic_core import PydanticCustomError

from scan_tool.domain._types import (
    Address,
    BlockNumber,
    ContractDatetime,
    ContractModel,
    FixtureId,
    JsonObject,
    NonEmptyUniqueList,
    TransactionHash,
)

ArtifactRef = str
ProviderId = str
ProviderRole = Literal["PRIMARY", "VERIFY"]

AAVE_V3_POOL = "0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2"
LIQUIDATION_CALL_TOPIC0 = "0xe413a321e8681d831f4dbccbca790d2952b56f977908e45be37335533e005286"
TRANSFER_TOPIC0 = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
EXPECTED_PROVIDERS = {
    "PROVIDER-ETHEREUM-PUBLICNODE": ("PRIMARY", "https://ethereum.publicnode.com"),
    "PROVIDER-ETHEREUM-THIRDWEB": ("VERIFY", "https://ethereum.rpc.thirdweb.com"),
}
CAPABILITY_METHODS = {
    "transaction": "eth_getTransactionByHash",
    "receipt": "eth_getTransactionReceipt",
    "block": "eth_getBlockByNumber",
}


class DefiLendingIncomplete(ValueError):
    """Raised when a required lending leg or artifact is unavailable."""


class ObservationWindow(ContractModel):
    start_block: BlockNumber
    end_block: BlockNumber

    @model_validator(mode="after")
    def window_is_ordered(self) -> "ObservationWindow":
        if self.end_block < self.start_block:
            raise PydanticCustomError("invalid_input", "observation window end must follow start")
        return self


class LendingObservationArtifacts(ContractModel):
    transaction: ArtifactRef | MISSING = MISSING
    receipt: ArtifactRef | MISSING = MISSING
    block: ArtifactRef | MISSING = MISSING

    @model_validator(mode="after")
    def artifact_refs_are_content_addressed(self) -> "LendingObservationArtifacts":
        for name in self.model_fields_set:
            value = getattr(self, name)
            if not isinstance(value, str) or not value.startswith("artifact://sha256/"):
                raise PydanticCustomError(
                    "invalid_input", f"{name} must be a content-addressed artifact reference"
                )
            sha256 = value.removeprefix("artifact://sha256/")
            if len(sha256) != 64 or any(char not in "0123456789abcdef" for char in sha256):
                raise PydanticCustomError("invalid_input", f"{name} artifact SHA-256 is invalid")
        return self


class LendingRawObservation(ContractModel):
    provider_id: ProviderId
    provider_role: ProviderRole
    artifacts: LendingObservationArtifacts


class DefiLendingReplay(ContractModel):
    schema_version: Literal["0.1"]
    fixture_id: FixtureId
    status: Literal["candidate", "verifying", "confirmed"]
    capture_status: Literal["complete", "partial"]
    captured_at: ContractDatetime
    network_calls: int = Field(ge=0)
    chain_id: Literal[1]
    protocol: Literal["aave_v3"]
    pool: Address
    subject_address: Address
    subject_roles: NonEmptyUniqueList[Literal["liquidator", "borrower", "receiver", "supplier"]]
    observation_window: ObservationWindow
    seed_transaction_hash: TransactionHash
    block_tag: str = Field(pattern=r"^0x(?:0|[1-9a-f][0-9a-f]*)$")
    methods: list[str] = Field(min_length=1)
    raw_observations: list[LendingRawObservation] = Field(min_length=2, max_length=2)
    reconciled_facts: JsonObject
    remaining_gate: list[str]

    @model_validator(mode="after")
    def observations_are_dual_role(self) -> "DefiLendingReplay":
        if self.captured_at > datetime.now(UTC) + timedelta(minutes=5):
            raise PydanticCustomError("invalid_input", "capture timestamp cannot be in the future")
        roles = [item.provider_role for item in self.raw_observations]
        if set(roles) != {"PRIMARY", "VERIFY"} or len(roles) != 2:
            raise PydanticCustomError(
                "reconciliation_failed", "PRIMARY and VERIFY observations are required"
            )
        return self


def parse_defi_lending_replay(raw_bytes: bytes) -> DefiLendingReplay:
    """Parse one reviewed DeFi lending replay package."""
    return DefiLendingReplay.model_validate_json(raw_bytes)


def reconstruct_lending_flow_facts(
    package: Path,
    replay: DefiLendingReplay,
) -> dict[str, object]:
    """Re-decode Aave V3 LiquidationCall and Transfer-matched value legs."""
    providers = _load_provider_pins(package / "provider-replay.json")
    _validate_provider_diversity(providers)
    capture_meta = _load_capture_meta(package / "artifacts" / "capture-meta.json")
    _validate_capture_meta(capture_meta, providers, replay)

    decoded_by_role: dict[ProviderRole, dict[str, object]] = {}
    selected_logs_by_role: dict[ProviderRole, dict[str, object]] = {}
    for observation in replay.raw_observations:
        provider = providers.get(observation.provider_id)
        if provider is None or provider.get("role") != observation.provider_role:
            raise ValueError("raw observation provider role does not match its provider pin")
        facts, selected_logs = _decode_lending_observation(package, observation, provider, replay)
        decoded_by_role[observation.provider_role] = facts
        selected_logs_by_role[observation.provider_role] = selected_logs

    if set(decoded_by_role) != {"PRIMARY", "VERIFY"}:
        raise DefiLendingIncomplete("PRIMARY and VERIFY observations are required")
    if decoded_by_role["PRIMARY"] != decoded_by_role["VERIFY"]:
        raise ValueError("cross-provider immutable lending facts differ")
    if selected_logs_by_role["PRIMARY"] != selected_logs_by_role["VERIFY"]:
        raise ValueError("cross-provider selected raw lending logs differ")
    return decoded_by_role["PRIMARY"]


def _decode_lending_observation(
    package: Path,
    observation: LendingRawObservation,
    provider: dict[str, object],
    replay: DefiLendingReplay,
) -> tuple[dict[str, object], dict[str, object]]:
    pins = provider.get("raw_sha256")
    if not isinstance(pins, dict):
        raise DefiLendingIncomplete(f"{observation.provider_role} pins are unavailable")
    transaction = _load_pinned_artifact(package, observation.artifacts, pins, "transaction")
    receipt = _load_pinned_artifact(package, observation.artifacts, pins, "receipt")
    block = _load_pinned_artifact(package, observation.artifacts, pins, "block")

    tx = _mapping(transaction.get("result"), "transaction result")
    if _lower(tx.get("hash")) != replay.seed_transaction_hash:
        raise ValueError("lending transaction hash mismatch")
    if _lower(tx.get("blockNumber")) != replay.block_tag:
        raise ValueError("lending transaction block mismatch")
    tx_block_hash = _lower(tx.get("blockHash"))

    receipt_result = _mapping(receipt.get("result"), "receipt result")
    if _lower(receipt_result.get("transactionHash")) != replay.seed_transaction_hash:
        raise ValueError("lending receipt transaction mismatch")
    if _lower(receipt_result.get("blockNumber")) != replay.block_tag:
        raise ValueError("lending receipt block mismatch")
    if receipt_result.get("status") != "0x1":
        raise ValueError("lending transaction was not successful")
    if _lower(receipt_result.get("blockHash")) != tx_block_hash:
        raise ValueError("lending transaction/receipt block hash mismatch")

    block_result = _mapping(block.get("result"), "block result")
    if _lower(block_result.get("number")) != replay.block_tag:
        raise ValueError("lending block response mismatch")
    if _lower(block_result.get("hash")) != tx_block_hash:
        raise ValueError("lending block hash reconciliation failed")
    tx_index = _parse_hex_index(tx.get("transactionIndex"), "transaction transactionIndex")
    receipt_tx_index = _parse_hex_index(
        receipt_result.get("transactionIndex"), "receipt transactionIndex"
    )
    if tx_index != receipt_tx_index:
        raise ValueError("lending transaction/receipt transactionIndex mismatch")
    block_transactions = block_result.get("transactions")
    if (
        not isinstance(block_transactions, list)
        or tx_index >= len(block_transactions)
        or _lower(block_transactions[tx_index]) != replay.seed_transaction_hash
    ):
        raise ValueError("lending transaction is not bound to the fetched block")

    block_number = int(replay.block_tag, 16)
    if not (
        replay.observation_window.start_block <= block_number <= replay.observation_window.end_block
    ):
        raise ValueError("lending seed transaction is outside the observation window")

    logs = receipt_result.get("logs")
    if not isinstance(logs, list):
        raise ValueError("lending receipt logs are malformed")
    binding = {
        "transaction_hash": replay.seed_transaction_hash,
        "block_hash": tx_block_hash,
        "block_number": replay.block_tag,
        "transaction_index": tx_index,
    }
    liquidation = _select_liquidation_log(logs, replay, binding)
    event = _decode_liquidation_call(liquidation, replay, block_number)
    transfers = _decode_transfers(logs, binding)
    debt_leg = _match_transfer(
        transfers,
        asset=str(event["debt_asset"]),
        amount=str(event["debt_to_cover_raw"]),
        subject=replay.subject_address,
        direction="out",
        preferred_to="0x5ee5bf7ae06d1be5997a1a72006fe6c607ec6de8",
    )
    collateral_leg = _match_transfer(
        transfers,
        asset=str(event["collateral_asset"]),
        amount=str(event["liquidated_collateral_amount_raw"]),
        subject=replay.subject_address,
        direction="in",
        preferred_from="0x0b925ed163218f6662a35e0f0371ac234f9e9371",
    )
    outflow = _match_subsequent_outflow(
        transfers,
        subject=replay.subject_address,
        asset=str(event["collateral_asset"]),
        seed_tx=replay.seed_transaction_hash,
        after_log_index=int(collateral_leg["log_index"]),
    )

    observed_roles = sorted(
        {"liquidator"} if event["liquidator"] == replay.subject_address else set()
    )
    if event["user"] == replay.subject_address:
        observed_roles = sorted(set(observed_roles) | {"borrower"})
    request_roles = sorted(replay.subject_roles)
    if observed_roles != request_roles:
        raise ValueError("observed subject roles do not match request subject_roles")

    facts = {
        "protocol": "aave_v3",
        "pool": replay.pool,
        "chain_id": 1,
        "subject_address": replay.subject_address,
        "subject_roles": list(replay.subject_roles),
        "events": [event],
        "net_asset_ledger": [
            {
                "asset_address": debt_leg["token"],
                "raw_amount": debt_leg["amount"],
                "direction": "out",
                "counterparty": debt_leg["to"]
                if debt_leg["from"] == replay.subject_address
                else debt_leg["from"],
                "leg_kind": "liquidation_debt",
                "matched_transfer_log_index": debt_leg["log_index"],
                "classification": "confirmed_fact",
            },
            {
                "asset_address": collateral_leg["token"],
                "raw_amount": collateral_leg["amount"],
                "direction": "in",
                "counterparty": collateral_leg["from"]
                if collateral_leg["to"] == replay.subject_address
                else collateral_leg["to"],
                "leg_kind": "liquidation_collateral",
                "matched_transfer_log_index": collateral_leg["log_index"],
                "classification": "confirmed_fact",
            },
        ],
        "subsequent_outflow": outflow,
        "attribution": {
            "attack_vs_normal": "not_assessed",
            "service_attribution": "not_assessed",
            "criminality": "not_assessed",
        },
    }
    selected_logs = {
        "liquidation": _selected_log_signature(liquidation),
        "debt_transfer": debt_leg["raw_log"],
        "collateral_transfer": collateral_leg["raw_log"],
        "subsequent_outflow": outflow.pop("raw_log"),
    }
    return facts, selected_logs


def _select_liquidation_log(
    logs: list[object],
    replay: DefiLendingReplay,
    binding: dict[str, object],
) -> dict[str, object]:
    matches: list[dict[str, object]] = []
    for item in logs:
        if not isinstance(item, dict):
            continue
        topics = item.get("topics")
        if not isinstance(topics, list) or not topics:
            continue
        if _lower(topics[0]) != LIQUIDATION_CALL_TOPIC0:
            continue
        if _lower(item.get("address")) != replay.pool:
            continue
        if _lower(item.get("transactionHash")) != replay.seed_transaction_hash:
            continue
        _validate_selected_log_binding(item, binding, "LiquidationCall")
        matches.append(item)
    if len(matches) != 1:
        raise ValueError("expected exactly one Aave V3 LiquidationCall in scope")
    return matches[0]


def _decode_liquidation_call(
    log: dict[str, object],
    replay: DefiLendingReplay,
    block_number: int,
) -> dict[str, object]:
    topics = log.get("topics")
    if not isinstance(topics, list) or len(topics) != 4:
        raise ValueError("LiquidationCall topics are malformed")
    for topic in topics:
        _validate_fixed_hex(topic, 32, "LiquidationCall topic")
    data_hex = log.get("data")
    _validate_fixed_hex(data_hex, 128, "LiquidationCall data")
    assert isinstance(data_hex, str)
    data = bytes.fromhex(data_hex[2:])
    liquidator = "0x" + data[76:96].hex()
    receive_a_token_raw = int.from_bytes(data[96:128], "big")
    if receive_a_token_raw not in {0, 1}:
        raise ValueError("LiquidationCall receiveAToken ABI bool is noncanonical")
    receive_a_token = bool(receive_a_token_raw)
    if receive_a_token:
        raise DefiLendingIncomplete("receiveAToken liquidations require additional aToken evidence")
    tx_index = log.get("transactionIndex")
    log_index = log.get("logIndex")
    if not isinstance(tx_index, str) or not isinstance(log_index, str):
        raise ValueError("LiquidationCall index fields are malformed")
    return {
        "event_name": "LiquidationCall",
        "protocol": "aave_v3",
        "pool": replay.pool,
        "collateral_asset": _topic_address(str(topics[1])),
        "debt_asset": _topic_address(str(topics[2])),
        "user": _topic_address(str(topics[3])),
        "liquidator": liquidator,
        "debt_to_cover_raw": str(int.from_bytes(data[0:32], "big")),
        "liquidated_collateral_amount_raw": str(int.from_bytes(data[32:64], "big")),
        "receive_a_token": False,
        "block_number": block_number,
        "transaction_hash": replay.seed_transaction_hash,
        "transaction_index": int(tx_index, 16),
        "log_index": int(log_index, 16),
        "topic0": LIQUIDATION_CALL_TOPIC0,
    }


def _decode_transfers(logs: list[object], binding: dict[str, object]) -> list[dict[str, object]]:
    transfers: list[dict[str, object]] = []
    for item in logs:
        if not isinstance(item, dict):
            continue
        topics = item.get("topics")
        if not isinstance(topics, list) or not topics:
            continue
        if _lower(topics[0]) != TRANSFER_TOPIC0:
            continue
        if len(topics) != 3:
            raise ValueError("ERC20 Transfer topics are malformed")
        for topic in topics:
            _validate_fixed_hex(topic, 32, "ERC20 Transfer topic")
        _validate_fixed_hex(item.get("address"), 20, "ERC20 Transfer address")
        _validate_fixed_hex(item.get("data"), 32, "ERC20 Transfer data")
        _validate_selected_log_binding(item, binding, "ERC20 Transfer")
        data_hex = item.get("data")
        assert isinstance(data_hex, str)
        amount = str(int(data_hex, 16))
        log_index = item.get("logIndex")
        transfers.append(
            {
                "token": _lower(item.get("address")),
                "from": _topic_address(str(topics[1])),
                "to": _topic_address(str(topics[2])),
                "amount": amount,
                "log_index": _parse_hex_index(log_index, "Transfer logIndex"),
                "raw_log": _selected_log_signature(item),
            }
        )
    return transfers


def _match_transfer(
    transfers: list[dict[str, object]],
    *,
    asset: str,
    amount: str,
    subject: str,
    direction: Literal["in", "out"],
    preferred_to: str | None = None,
    preferred_from: str | None = None,
) -> dict[str, object]:
    candidates = []
    for item in transfers:
        if item["token"] != asset or item["amount"] != amount:
            continue
        if (
            direction == "out"
            and item["from"] == subject
            or direction == "in"
            and item["to"] == subject
        ):
            candidates.append(item)
    if not candidates:
        raise DefiLendingIncomplete(f"matching {direction} Transfer for {asset} is unavailable")
    if preferred_to is not None:
        preferred = [item for item in candidates if item["to"] == preferred_to]
        if preferred:
            return preferred[0]
    if preferred_from is not None:
        preferred = [item for item in candidates if item["from"] == preferred_from]
        if preferred:
            return preferred[0]
    return candidates[0]


def _match_subsequent_outflow(
    transfers: list[dict[str, object]],
    *,
    subject: str,
    asset: str,
    seed_tx: str,
    after_log_index: int,
) -> dict[str, object]:
    candidates = [
        item
        for item in transfers
        if item["token"] == asset
        and item["from"] == subject
        and item["to"] != subject
        and int(item["log_index"]) > after_log_index
    ]
    if not candidates:
        raise DefiLendingIncomplete("bounded subsequent collateral outflow is unavailable")
    chosen = max(candidates, key=lambda item: (int(str(item["amount"])), int(item["log_index"])))
    return {
        "status": "bounded",
        "seed_address": subject,
        "terminal_address": chosen["to"],
        "asset_address": asset,
        "raw_amount": chosen["amount"],
        "transaction_hash": seed_tx,
        "log_index": chosen["log_index"],
        "classification": "confirmed_fact",
        "raw_log": chosen["raw_log"],
    }


def _load_provider_pins(path: Path) -> dict[str, dict[str, object]]:
    try:
        value = json.loads(path.read_bytes())
    except (OSError, json.JSONDecodeError) as error:
        raise DefiLendingIncomplete("provider replay pins are unavailable") from error
    if not isinstance(value, dict) or not isinstance(value.get("providers"), list):
        raise ValueError("provider replay pins are malformed")
    providers: dict[str, dict[str, object]] = {}
    for item in value["providers"]:
        if not isinstance(item, dict) or not isinstance(item.get("provider_id"), str):
            raise ValueError("provider replay entry is malformed")
        if item["provider_id"] in providers:
            raise ValueError("provider replay IDs must be unique")
        providers[item["provider_id"]] = item
    return providers


def _validate_provider_diversity(providers: dict[str, dict[str, object]]) -> None:
    if len(providers) != 2:
        raise DefiLendingIncomplete("exactly two independent RPC providers are required")
    if set(providers) != set(EXPECTED_PROVIDERS):
        raise ValueError("lending provider IDs do not match the approved provider pins")
    roles = {provider.get("role") for provider in providers.values()}
    if roles != {"PRIMARY", "VERIFY"}:
        raise DefiLendingIncomplete("PRIMARY and VERIFY provider roles are required")
    endpoints = []
    hashes_by_role: dict[object, dict[str, str]] = {}
    for provider_id, provider in providers.items():
        endpoint = provider.get("endpoint")
        if not isinstance(endpoint, str) or not endpoint:
            raise ValueError("provider endpoint is malformed")
        expected_role, expected_endpoint = EXPECTED_PROVIDERS[provider_id]
        if provider.get("role") != expected_role or endpoint != expected_endpoint:
            raise ValueError("lending provider role/endpoint differs from its approved pin")
        endpoints.append(endpoint.rstrip("/").lower())
        pins = provider.get("raw_sha256")
        if not isinstance(pins, dict):
            raise ValueError("provider raw_sha256 pins are malformed")
        role_hashes: dict[str, str] = {}
        for capability in ("transaction", "receipt", "block"):
            digest = pins.get(capability)
            if not isinstance(digest, str):
                raise ValueError(f"provider {capability} pin is malformed")
            role_hashes[capability] = digest
        hashes_by_role[provider.get("role")] = role_hashes
    if len(set(endpoints)) != 2:
        raise ValueError("PRIMARY and VERIFY providers must use distinct endpoints")
    for capability in ("transaction", "receipt", "block"):
        if hashes_by_role["PRIMARY"][capability] == hashes_by_role["VERIFY"][capability]:
            raise ValueError(f"PRIMARY and VERIFY {capability} artifact bytes must be distinct")


def _load_capture_meta(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_bytes())
    except (OSError, json.JSONDecodeError) as error:
        raise DefiLendingIncomplete("capture metadata is unavailable") from error
    return _mapping(value, "capture metadata")


def _validate_capture_meta(
    capture_meta: dict[str, object],
    providers: dict[str, dict[str, object]],
    replay: DefiLendingReplay,
) -> None:
    if (
        capture_meta.get("schema_version") != "0.1"
        or capture_meta.get("fixture_id") != replay.fixture_id
        or capture_meta.get("captured_at") != replay.captured_at.isoformat().replace("+00:00", "Z")
    ):
        raise ValueError("capture metadata envelope differs from the replay")
    capabilities = capture_meta.get("capabilities")
    if not isinstance(capabilities, list) or len(capabilities) != 6:
        raise ValueError("capture metadata must bind exactly six capabilities")
    observed: set[tuple[str, str]] = set()
    for item in capabilities:
        if not isinstance(item, dict):
            raise ValueError("capture metadata capability is malformed")
        provider_id = item.get("provider_id")
        capability = item.get("capability")
        if not isinstance(provider_id, str) or capability not in CAPABILITY_METHODS:
            raise ValueError("capture metadata provider/capability is malformed")
        provider = providers.get(provider_id)
        if provider is None:
            raise ValueError("capture metadata references an unapproved provider")
        key = (provider_id, str(capability))
        if key in observed:
            raise ValueError("capture metadata capabilities must be unique")
        observed.add(key)
        expected_params = (
            [replay.seed_transaction_hash]
            if capability in {"transaction", "receipt"}
            else [replay.block_tag, False]
        )
        pins = provider.get("raw_sha256")
        if not isinstance(pins, dict):
            raise ValueError("provider raw SHA pins are malformed")
        if (
            item.get("provider_role") != provider.get("role")
            or item.get("endpoint") != provider.get("endpoint")
            or item.get("method") != CAPABILITY_METHODS[str(capability)]
            or item.get("params") != expected_params
            or item.get("response_sha256") != pins.get(capability)
            or item.get("captured_at") != provider.get("retrieved_at")
        ):
            raise ValueError("capture metadata capability differs from provider replay")
    expected = {
        (provider_id, capability)
        for provider_id in EXPECTED_PROVIDERS
        for capability in CAPABILITY_METHODS
    }
    if observed != expected:
        raise ValueError("capture metadata capability coverage is incomplete")


def _load_pinned_artifact(
    package: Path,
    artifacts: LendingObservationArtifacts,
    pins: dict[str, object],
    capability: str,
) -> dict[str, object]:
    uri = getattr(artifacts, capability)
    if uri is MISSING:
        raise DefiLendingIncomplete(f"{capability} artifact is unavailable")
    referenced_sha256 = str(uri).removeprefix("artifact://sha256/")
    if pins.get(capability) != referenced_sha256:
        raise ValueError(f"{capability} artifact differs from the provider pin")
    path = package / "artifacts" / "sha256" / f"{referenced_sha256}.json"
    try:
        raw_bytes = path.read_bytes()
    except OSError as error:
        raise DefiLendingIncomplete(f"{capability} artifact is unavailable") from error
    if hashlib.sha256(raw_bytes).hexdigest() != referenced_sha256:
        raise ValueError(f"{capability} artifact content hash mismatch")
    try:
        value = json.loads(raw_bytes)
    except json.JSONDecodeError as error:
        raise ValueError(f"{capability} artifact JSON is malformed") from error
    return _mapping(value, f"{capability} artifact")


def _mapping(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def _lower(value: object) -> str:
    return value.lower() if isinstance(value, str) else ""


def _topic_address(topic: str) -> str:
    _validate_fixed_hex(topic, 32, "topic address")
    if topic[2:26] != "0" * 24:
        raise ValueError("topic address has noncanonical ABI padding")
    return "0x" + topic[-40:].lower()


def _validate_selected_log_binding(
    log: dict[str, object], binding: dict[str, object], label: str
) -> None:
    if log.get("removed") is not False:
        raise ValueError(f"{label} must be a canonical non-removed receipt log")
    if (
        _lower(log.get("transactionHash")) != binding["transaction_hash"]
        or _lower(log.get("blockHash")) != binding["block_hash"]
        or _lower(log.get("blockNumber")) != binding["block_number"]
        or _parse_hex_index(log.get("transactionIndex"), f"{label} transactionIndex")
        != binding["transaction_index"]
    ):
        raise ValueError(f"{label} is not bound to the transaction receipt and block")
    _parse_hex_index(log.get("logIndex"), f"{label} logIndex")


def _selected_log_signature(log: dict[str, object]) -> dict[str, object]:
    return {
        "address": _lower(log.get("address")),
        "topics": [_lower(topic) for topic in log.get("topics", [])],
        "data": _lower(log.get("data")),
        "log_index": _parse_hex_index(log.get("logIndex"), "selected logIndex"),
        "transaction_index": _parse_hex_index(
            log.get("transactionIndex"), "selected transactionIndex"
        ),
        "transaction_hash": _lower(log.get("transactionHash")),
        "block_hash": _lower(log.get("blockHash")),
        "block_number": _lower(log.get("blockNumber")),
    }


def _parse_hex_index(value: object, label: str) -> int:
    if (
        not isinstance(value, str)
        or not value.startswith("0x")
        or len(value) < 3
        or any(char not in "0123456789abcdef" for char in value[2:].lower())
    ):
        raise ValueError(f"{label} is malformed")
    return int(value, 16)


def _validate_fixed_hex(value: object, byte_length: int, label: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("0x")
        or len(value) != 2 + byte_length * 2
        or any(char not in "0123456789abcdef" for char in value[2:].lower())
    ):
        raise ValueError(f"{label} is malformed")
