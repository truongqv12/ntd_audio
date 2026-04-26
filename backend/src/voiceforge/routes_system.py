from fastapi import APIRouter

from .services_system import get_host_capabilities, to_dict

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/capabilities")
def host_capabilities() -> dict:
    return to_dict(get_host_capabilities())
