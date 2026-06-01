import os
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, Depends, HTTPException

from auth import ApiClient, get_api_client, require_scope

app = FastAPI()


def get_db_connection():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise HTTPException(
            status_code=500,
            detail="DATABASE_URL is not configured",
        )

    try:
        return psycopg2.connect(database_url)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database connection error: {str(e)}",
        )


def fetch_rows(query: str, params: tuple[Any, ...] = ()):
    try:
        conn = get_db_connection()

        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                rows = cursor.fetchall()

        conn.close()

        if not rows:
            return {
                "columns": [],
                "rows": [],
            }

        columns = list(rows[0].keys())
        data = [
            [row[column] for column in columns]
            for row in rows
        ]

        return {
            "columns": columns,
            "rows": data,
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database query error: {str(e)}",
        )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/me")
def me(client: ApiClient = Depends(get_api_client)):
    return {
        "client_id": client.client_id,
        "scopes": sorted(client.scopes),
    }

@app.get("/exports/status")
def export_status(
    client: ApiClient = Depends(require_scope("status.read")),
):
    result = fetch_rows("""
        SELECT *
        FROM tg_bot.status
        LIMIT 1000
    """)

    return {
        "client_id": client.client_id,
        **result,
    }