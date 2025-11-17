#data models

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class BodyType(str, Enum):
    NONE = "none"
    RAW = "raw"
    FORM_URLENCODED = "x-www-form-urlencoded"
    MULTIPART = "multipart/form-data"


class RawBodyType(str, Enum):
    TEXT = "text"
    JSON = "json"
    XML = "xml"


class AuthType(str, Enum):
    NONE = "none"
    BASIC = "basic"
    BEARER = "bearer"


@dataclass
class KeyValuePair:
    enabled: bool = True
    key: str = ""
    value: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "key": self.key,
            "value": self.value
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KeyValuePair":
        return cls(
            enabled=data.get("enabled", True),
            key=data.get("key", ""),
            value=data.get("value", "")
        )


@dataclass
class MultipartItem:
    enabled: bool = True
    key: str = ""
    type: str = "text"  # "text" or "file"
    value: str = ""  # text value or file path

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "key": self.key,
            "type": self.type,
            "value": self.value
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MultipartItem":
        return cls(
            enabled=data.get("enabled", True),
            key=data.get("key", ""),
            type=data.get("type", "text"),
            value=data.get("value", "")
        )


@dataclass
class AuthConfig:
    auth_type: AuthType = AuthType.NONE
    username: str = ""
    password: str = ""
    bearer_token: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "auth_type": self.auth_type.value,
            "username": self.username,
            "password": self.password,
            "bearer_token": self.bearer_token
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuthConfig":
        return cls(
            auth_type=AuthType(data.get("auth_type", "none")),
            username=data.get("username", ""),
            password=data.get("password", ""),
            bearer_token=data.get("bearer_token", "")
        )


@dataclass
class RequestModel:
    method: HttpMethod = HttpMethod.GET
    url: str = ""
    query_params: List[KeyValuePair] = field(default_factory=list)
    headers: List[KeyValuePair] = field(default_factory=list)
    body_type: BodyType = BodyType.NONE
    raw_body_type: RawBodyType = RawBodyType.TEXT
    raw_body: str = ""
    form_data: List[KeyValuePair] = field(default_factory=list)
    multipart_data: List[MultipartItem] = field(default_factory=list)
    auth: AuthConfig = field(default_factory=AuthConfig)
    environment: str = "Default"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method.value,
            "url": self.url,
            "query_params": [p.to_dict() for p in self.query_params],
            "headers": [h.to_dict() for h in self.headers],
            "body_type": self.body_type.value,
            "raw_body_type": self.raw_body_type.value,
            "raw_body": self.raw_body,
            "form_data": [f.to_dict() for f in self.form_data],
            "multipart_data": [m.to_dict() for m in self.multipart_data],
            "auth": self.auth.to_dict(),
            "environment": self.environment
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RequestModel":
        return cls(
            method=HttpMethod(data.get("method", "GET")),
            url=data.get("url", ""),
            query_params=[KeyValuePair.from_dict(p) for p in data.get("query_params", [])],
            headers=[KeyValuePair.from_dict(h) for h in data.get("headers", [])],
            body_type=BodyType(data.get("body_type", "none")),
            raw_body_type=RawBodyType(data.get("raw_body_type", "text")),
            raw_body=data.get("raw_body", ""),
            form_data=[KeyValuePair.from_dict(f) for f in data.get("form_data", [])],
            multipart_data=[MultipartItem.from_dict(m) for m in data.get("multipart_data", [])],
            auth=AuthConfig.from_dict(data.get("auth", {})),
            environment=data.get("environment", "Default")
        )


@dataclass
class ResponseModel:
    status_code: int = 0
    reason: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    body_bytes: bytes = b""
    body_text: str = ""
    time_taken_ms: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status_code": self.status_code,
            "reason": self.reason,
            "headers": self.headers,
            "body_text": self.body_text,
            "time_taken_ms": self.time_taken_ms,
            "error": self.error
        }


@dataclass
class Environment:
    name: str = ""
    variables: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "variables": self.variables
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Environment":
        return cls(
            name=data.get("name", ""),
            variables=data.get("variables", {})
        )


@dataclass
class Settings:
    default_timeout: int = 30
    ssl_verify: bool = True
    default_environment: str = "Default"
    http_proxy: str = ""
    https_proxy: str = ""
    theme: str = "dark"  # Always dark theme

    def to_dict(self) -> Dict[str, Any]:
        return {
            "default_timeout": self.default_timeout,
            "ssl_verify": self.ssl_verify,
            "default_environment": self.default_environment,
            "http_proxy": self.http_proxy,
            "https_proxy": self.https_proxy,
            "theme": self.theme
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Settings":
        return cls(
            default_timeout=data.get("default_timeout", 30),
            ssl_verify=data.get("ssl_verify", True),
            default_environment=data.get("default_environment", "Default"),
            http_proxy=data.get("http_proxy", ""),
            https_proxy=data.get("https_proxy", ""),
            theme=data.get("theme", "dark")
        )


@dataclass
class HistoryEntry:
    timestamp: datetime
    method: str
    url: str
    status_code: Optional[int] = None
    name: str = ""
    request: Optional["RequestModel"] = None

    def __post_init__(self):
        if not self.name:
            #generate a short name from url
            try:
                from urllib.parse import urlparse
                parsed = urlparse(self.url)
                self.name = f"{self.method} {parsed.netloc}{parsed.path[:30]}"
            except:
                self.name = f"{self.method} {self.url[:40]}"

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "timestamp": self.timestamp.isoformat(),
            "method": self.method,
            "url": self.url,
            "status_code": self.status_code,
            "name": self.name
        }
        if self.request:
            result["request"] = self.request.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HistoryEntry":
        timestamp_str = data.get("timestamp", "")
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
        except:
            timestamp = datetime.now()
        
        request = None
        if "request" in data:
            request = RequestModel.from_dict(data["request"])
        
        return cls(
            timestamp=timestamp,
            method=data.get("method", "GET"),
            url=data.get("url", ""),
            status_code=data.get("status_code"),
            name=data.get("name", ""),
            request=request
        )


@dataclass
class CollectionItem:
    name: str = ""
    request: RequestModel = field(default_factory=RequestModel)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "request": self.request.to_dict()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CollectionItem":
        return cls(
            name=data.get("name", ""),
            request=RequestModel.from_dict(data.get("request", {}))
        )


@dataclass
class Collection:
    name: str = ""
    items: List[CollectionItem] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "items": [item.to_dict() for item in self.items]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Collection":
        return cls(
            name=data.get("name", ""),
            items=[CollectionItem.from_dict(item) for item in data.get("items", [])]
        )

