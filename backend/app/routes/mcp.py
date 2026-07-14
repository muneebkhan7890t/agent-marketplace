from fastapi import APIRouter

router = APIRouter()

@router.post("/connect")
def connect_service():

    return {
        "message":"Service connected"
    }

@router.get("/")
def get_connections():

    return []