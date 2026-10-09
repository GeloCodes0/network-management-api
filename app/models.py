from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class NetworkDevice(Base):
    """
    SQLAlchemy model representing a managed network device.

    Each instance corresponds to one row in the network_devices
    database table.
    """

    __tablename__ = "network_devices"

    # Unique database identifier assigned automatically.
    id = Column(Integer, primary_key=True, index=True)

    # Human-readable device name, such as SW-CORE-01.
    hostname = Column(String(100), unique=True, nullable=False, index=True)

    # IPv4 address used to identify the device on the network.
    ip_address = Column(String(45), unique=True, nullable=False, index=True)

    # Device category, such as router, switch, or server.
    device_type = Column(String(30), nullable=False)

    # Manufacturer and hardware model.
    vendor = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)

    # Operating system or network operating system.
    operating_system = Column(String(100), nullable=True)

    # Physical location or site where the device is installed.
    location = Column(String(150), nullable=True)

    # Administrative status recorded by the management system.
    status = Column(String(20), nullable=False, default="unknown")

    # Automatically record when the device record is created.
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Update the timestamp whenever the record is modified.
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )