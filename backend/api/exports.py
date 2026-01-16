from fastapi import APIRouter, Depends
from api.deps import get_current_user
from db import export_monthly_data_db

router = APIRouter(prefix="/exports", tags=["Exports"])


@router.get("/monthly")
def export_monthly_data(
            year: int,
            month: int,
            branch_id: int,
            user=Depends(get_current_user)
        ):
    
    df = export_monthly_data_db(year, month, branch_id)

    return df
