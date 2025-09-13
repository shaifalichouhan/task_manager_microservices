from fastapi import FastAPI

app = FastAPI(title="Task Service")

@app.get("/")
def read_root():
    return {"message": "Task Service Running"}
