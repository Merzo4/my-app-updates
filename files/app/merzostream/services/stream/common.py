from dataclasses import dataclass


@dataclass(slots=True)
class ServiceResult:
    ok: bool
    message: str

    @classmethod
    def success(cls, message: str) -> "ServiceResult":
        return cls(True, message)

    @classmethod
    def error(cls, message: str) -> "ServiceResult":
        return cls(False, message)
