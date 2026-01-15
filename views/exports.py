import pandas as pd
from .api_client import api_get


def export_monthly_excel(year, month, branch_id, file_path):
    app = None  # api_client does not require UI context

    rows = api_get(
        app,
        "/exports/monthly",
        {
            "year": year,
            "month": month,
            "branch_id": branch_id
        }
    )

    df = pd.DataFrame(rows)
    df.to_excel(file_path, index=False)
