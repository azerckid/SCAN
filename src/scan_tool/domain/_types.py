"""Shared strict types for Analysis I/O 0.1."""

import re
from collections.abc import Sequence
from typing import Annotated

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    StrictBool,
    StrictInt,
    StringConstraints,
)
from pydantic_core import PydanticCustomError


class ContractModel(BaseModel):
    """Forbid undeclared fields in every contract object."""

    model_config = ConfigDict(extra="forbid")


def ensure_unique[T](items: list[T]) -> list[T]:
    """Reject duplicate values without requiring hashable items."""
    if any(item in items[:index] for index, item in enumerate(items)):
        raise PydanticCustomError("invalid_input", "array items must be unique")
    return items


def non_empty_unique[T](items: list[T]) -> list[T]:
    """Reject empty and duplicate arrays."""
    if not items:
        raise PydanticCustomError("schema_invalid", "array must contain at least one item")
    return ensure_unique(items)


def exactly_two_unique[T](items: list[T]) -> list[T]:
    """Require exactly two distinct values."""
    if len(items) != 2:
        raise PydanticCustomError("invalid_input", "array must contain exactly two items")
    return ensure_unique(items)


def non_empty_mapping(value: dict[str, JsonValue]) -> dict[str, JsonValue]:
    """Reject empty extensible objects."""
    if not value:
        raise PydanticCustomError("schema_invalid", "object must contain at least one property")
    return value


def non_empty_text(value: str) -> str:
    """Reject empty text while preserving the original value."""
    if not value:
        raise PydanticCustomError("schema_invalid", "string must not be empty")
    return value


def _is_canonical_uint256(value: object) -> bool:
    return (
        isinstance(value, str)
        and re.fullmatch(r"0|[1-9][0-9]*", value) is not None
        and int(value) <= UINT256_MAX
    )


def raw_values_are_uint256(value: JsonValue) -> JsonValue:
    """Validate every nested field whose name ends in ``_raw``.

    The value may be a single decimal string or an array of them (e.g. a
    Batch transfer's parallel ``ids_raw``/``amounts_raw`` arrays).
    """
    if isinstance(value, dict):
        for key, nested in value.items():
            if key.endswith("_raw"):
                valid = (
                    _is_canonical_uint256(nested)
                    if not isinstance(nested, list)
                    else all(_is_canonical_uint256(item) for item in nested)
                )
                if not valid:
                    raise PydanticCustomError(
                        "schema_invalid",
                        "raw values must be canonical uint256 decimal strings",
                    )
            raw_values_are_uint256(nested)
    elif isinstance(value, list):
        for nested in value:
            raw_values_are_uint256(nested)
    return value


def missing_references(references: Sequence[str], known_ids: set[str]) -> set[str]:
    """Return references that do not exist in the known ID set."""
    return set(references) - known_ids


AnalysisId = Annotated[
    str,
    StringConstraints(pattern=r"^AN-[A-Z0-9][A-Z0-9-]{2,63}$"),
]
ResultId = Annotated[
    str,
    StringConstraints(pattern=r"^RES-[A-Z0-9][A-Z0-9-]{2,127}$"),
]
EvidenceId = Annotated[
    str,
    StringConstraints(pattern=r"^EV-[A-Z0-9][A-Z0-9-]{2,127}$"),
]
SourceId = Annotated[str, StringConstraints(pattern=r"^DS-[A-Z0-9-]+$")]
SourceRecordId = Annotated[
    str,
    StringConstraints(pattern=r"^SRC-[A-Z0-9][A-Z0-9-]{2,127}$"),
]
FixtureId = Annotated[str, StringConstraints(pattern=r"^FX-[A-Z0-9-]+$")]
ErrorId = Annotated[
    str,
    StringConstraints(pattern=r"^ERR-[A-Z0-9][A-Z0-9-]{2,63}$"),
]
WarningId = Annotated[
    str,
    StringConstraints(pattern=r"^WARN-[A-Z0-9][A-Z0-9-]{2,63}$"),
]
Address = Annotated[str, StringConstraints(pattern=r"^0x[a-f0-9]{40}$")]
TransactionHash = Annotated[str, StringConstraints(pattern=r"^0x[a-f0-9]{64}$")]
BitcoinTxId = Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]
Sha256 = Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]
ProviderId = Annotated[
    str,
    StringConstraints(pattern=r"^[a-z0-9][a-z0-9._-]{1,63}$"),
]
SnakeName = Annotated[
    str,
    StringConstraints(pattern=r"^[a-z][a-z0-9_]{1,63}$"),
]
ToolRequirementId = Annotated[
    str,
    StringConstraints(pattern=r"^REQ-(COM|P0|V1|NFR)-[A-Z0-9-]+$"),
]
FixtureRequirementId = Annotated[
    str,
    StringConstraints(
        pattern=r"^REQ-(DEX|AUTH|FREEZE|BASIC|TOKEN|NFT721|NFT1155|PROXY|FLOW|INTEL|BRIDGE|BTC|CEX|LEND|CASE)-[A-Z0-9-]+$"
    ),
]
BlockNumber = Annotated[StrictInt, Field(ge=0)]
NonNegativeInt = Annotated[StrictInt, Field(ge=0)]
NonEmptyString = Annotated[str, Field(min_length=1), AfterValidator(non_empty_text)]
JsonObject = dict[str, JsonValue]
NonEmptyJsonObject = Annotated[
    JsonObject,
    Field(min_length=1),
    AfterValidator(non_empty_mapping),
]
type UniqueList[T] = Annotated[
    list[T],
    Field(json_schema_extra={"uniqueItems": True}),
    AfterValidator(ensure_unique),
]
type NonEmptyUniqueList[T] = Annotated[
    list[T],
    Field(min_length=1, json_schema_extra={"uniqueItems": True}),
    AfterValidator(non_empty_unique),
]
type ExactlyTwoUniqueList[T] = Annotated[
    list[T],
    Field(min_length=2, max_length=2, json_schema_extra={"uniqueItems": True}),
    AfterValidator(exactly_two_unique),
]
ContractDatetime = AwareDatetime
ContractBool = StrictBool

UINT256_MAX = 2**256 - 1
