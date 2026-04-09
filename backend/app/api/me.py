from fastapi import APIRouter, Depends

from app.core.auth import CurrentUser, get_current_user

router = APIRouter(tags=["Auth"])


@router.get("/me")
async def get_me(user: CurrentUser = Depends(get_current_user)):
    return {
        "sub": user.sub,
        "email": user.email,
        "name": user.name,
        "org_id": str(user.org_id) if user.org_id else None,
        "is_superadmin": user.is_superadmin,
        "roles": user.roles,
    }
