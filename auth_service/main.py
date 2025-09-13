from fastapi import FastAPI

app = FastAPI(title="Auth Service")

@app.get("/")
def read_root():
    return {"message": "Auth Service Running"}
