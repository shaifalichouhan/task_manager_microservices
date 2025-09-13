from fastapi import FastAPI

app = FastAPI(title="Notification Service")

@app.get("/")
def read_root():
    return {"message": "Notification Service Running"}
