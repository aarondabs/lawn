from fastapi import FastAPI

app = FastAPI(title="Lawn API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
