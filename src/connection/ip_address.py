from dataclasses import dataclass


@dataclass(frozen=True)
class IpAddress:
    host: str
    port: int

    def __str__(self) -> str:
        return f"{self.host}:{self.port}"
