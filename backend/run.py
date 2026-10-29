try:
    import uvicorn  # pyright: ignore[reportMissingImports]
except ModuleNotFoundError:
    uvicorn = None

if __name__ == "__main__":
    if uvicorn is None:
        raise RuntimeError("uvicorn is not installed. Install it with: pip install uvicorn")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
