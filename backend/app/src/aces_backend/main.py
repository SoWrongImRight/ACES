from fastapi import FastAPI

from aces_backend.api.router import api_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="A.C.E.S. Backend",
        version="0.1.0",
        description=(
            "Rules-authoritative backend skeleton for the A.C.E.S. tactical air combat card game."
        ),
    )
    app.include_router(api_router)
    return app


app = create_app()
