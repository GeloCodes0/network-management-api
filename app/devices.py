
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import NetworkDevice
from app.schemas import DeviceCreate, DeviceResponse, DeviceUpdate


# Group all device-management endpoints under /devices.
router = APIRouter(
    prefix="/devices",
    tags=["Network Devices"],
)


@router.post(
    "/",
    response_model=DeviceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_device(
    device_data: DeviceCreate,
    db: Session = Depends(get_db),
):
    """Register a new network device."""

    # Hostnames and IP addresses must both be unique.
    existing_device = (
        db.query(NetworkDevice)
        .filter(
            (NetworkDevice.hostname == device_data.hostname)
            | (NetworkDevice.ip_address == device_data.ip_address)
        )
        .first()
    )

    if existing_device:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A device with this hostname or IP address already exists.",
        )

    new_device = NetworkDevice(**device_data.model_dump())

    try:
        db.add(new_device)
        db.commit()
        db.refresh(new_device)

    except IntegrityError:
        # Roll back in case another request created a duplicate
        # between our initial check and database commit.
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Device hostname or IP address must be unique.",
        )

    return new_device


@router.get(
    "/",
    response_model=list[DeviceResponse],
)
def list_devices(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Return a paginated list of registered devices."""

    return (
        db.query(NetworkDevice)
        .order_by(NetworkDevice.id)
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get(
    "/{device_id}",
    response_model=DeviceResponse,
)
def get_device(
    device_id: int,
    db: Session = Depends(get_db),
):
    """Retrieve one device using its database ID."""

    device = (
        db.query(NetworkDevice)
        .filter(NetworkDevice.id == device_id)
        .first()
    )

    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Network device not found.",
        )

    return device


@router.patch(
    "/{device_id}",
    response_model=DeviceResponse,
)
def update_device(
    device_id: int,
    device_data: DeviceUpdate,
    db: Session = Depends(get_db),
):
    """Update only the fields supplied by the client."""

    device = (
        db.query(NetworkDevice)
        .filter(NetworkDevice.id == device_id)
        .first()
    )

    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Network device not found.",
        )

    # exclude_unset=True preserves fields the client did not send.
    updates = device_data.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least one field to update.",
        )

    # These database fields cannot be set to NULL.
    required_fields = {
        "hostname",
        "ip_address",
        "device_type",
        "status",
    }

    if any(
        field in updates and updates[field] is None
        for field in required_fields
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Required device fields cannot be null.",
        )

    # Reject a hostname or IP address already assigned to
    # a different device.
    for field in ("hostname", "ip_address"):
        if field in updates:
            duplicate = (
                db.query(NetworkDevice)
                .filter(
                    getattr(NetworkDevice, field) == updates[field],
                    NetworkDevice.id != device_id,
                )
                .first()
            )

            if duplicate:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"That {field.replace('_', ' ')} is already in use.",
                )

    # Apply only the requested changes.
    for field, value in updates.items():
        setattr(device, field, value)

    try:
        db.commit()
        db.refresh(device)

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Device update conflicts with an existing record.",
        )

    return device


@router.delete(
    "/{device_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_device(
    device_id: int,
    db: Session = Depends(get_db),
):
    """Remove a registered device."""

    device = (
        db.query(NetworkDevice)
        .filter(NetworkDevice.id == device_id)
        .first()
    )

    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Network device not found.",
        )

    db.delete(device)
    db.commit()

    # HTTP 204 responses intentionally return no body.
    return None