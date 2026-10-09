import ipaddress
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


# Restrict device categories to recognised values.
DeviceType = Literal[
    "router",
    "switch",
    "firewall",
    "server",
    "access_point",
    "other",
]

# Restrict status values to a consistent set.
DeviceStatus = Literal[
    "online",
    "offline",
    "unknown",
]


class DeviceBase(BaseModel):
    """
    Fields shared by device creation and update requests.
    """

    hostname: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Unique name identifying the network device.",
    )

    ip_address: str = Field(
        ...,
        description="IPv4 address assigned to the device.",
    )

    device_type: DeviceType = Field(
        ...,
        description="Category of network device.",
    )

    vendor: str | None = Field(
        default=None,
        max_length=100,
    )

    model: str | None = Field(
        default=None,
        max_length=100,
    )

    operating_system: str | None = Field(
        default=None,
        max_length=100,
    )

    location: str | None = Field(
        default=None,
        max_length=150,
    )

    status: DeviceStatus = Field(
        default="unknown",
        description="Recorded device status.",
    )

    @field_validator("hostname", "vendor", "model", "operating_system", "location")
    @classmethod
    def strip_whitespace(cls, value):
        """
        Remove unnecessary surrounding whitespace.

        Required hostnames cannot be blank after trimming.
        Optional text fields may be empty or omitted.
        """

        if value is None:
            return value

        value = value.strip()

        if not value and cls.model_fields.get("hostname"):
            # The hostname-specific validator below handles
            # the required hostname field.
            pass

        return value

    @field_validator("hostname")
    @classmethod
    def validate_hostname(cls, value):
        """
        Reject hostnames that contain only whitespace.
        """

        if not value.strip():
            raise ValueError("Hostname cannot be blank.")

        return value

    @field_validator("ip_address")
    @classmethod
    def validate_ipv4_address(cls, value):
        """
        Accept valid IPv4 addresses and reject other formats.
        """

        try:
            address = ipaddress.ip_address(value)

        except ValueError:
            raise ValueError("A valid IPv4 address is required.")

        if address.version != 4:
            raise ValueError("Only IPv4 addresses are supported.")

        return str(address)


class DeviceCreate(DeviceBase):
    """
    Schema for registering a new network device.
    """

    pass


class DeviceUpdate(BaseModel):
    """
    Schema for partial device updates.

    All fields are optional so a client can update only
    the properties it needs to change.
    """

    model_config = ConfigDict(extra="forbid")

    hostname: str | None = Field(default=None, min_length=1, max_length=100)
    ip_address: str | None = None
    device_type: DeviceType | None = None
    vendor: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    operating_system: str | None = Field(default=None, max_length=100)
    location: str | None = Field(default=None, max_length=150)
    status: DeviceStatus | None = None

    @field_validator("hostname", "vendor", "model", "operating_system", "location")
    @classmethod
    def strip_update_whitespace(cls, value):
        if value is None:
            return value

        value = value.strip()

        if not value:
            raise ValueError("Text fields cannot be blank.")

        return value

    @field_validator("ip_address")
    @classmethod
    def validate_update_ipv4_address(cls, value):
        if value is None:
            return value

        try:
            address = ipaddress.ip_address(value)

        except ValueError:
            raise ValueError("A valid IPv4 address is required.")

        if address.version != 4:
            raise ValueError("Only IPv4 addresses are supported.")

        return str(address)


class DeviceResponse(DeviceBase):
    """
    Schema returned to clients when a device is retrieved.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime