from typing import Generic, TypeVar

from pydantic import BaseModel, model_validator


class SafeStringMixin(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def reject_null_bytes_all_fields(cls, data):
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, str):
                    if "\x00" in value:
                        raise ValueError(f"Null-tecken (\\x00) är inte tillåtna i fältet '{key}'")
                    # Avvisa strängar som enbart består av whitespace i namnfält
                    if key == "name" and value and not value.strip():
                        raise ValueError(f"Fältet '{key}' får inte enbart innehålla blanksteg")
        return data


T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int
