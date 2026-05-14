from fastapi import FastAPI

app = FastAPI(title="Monitor de Gastos API")

@app.get("/")
def read_root():
    return {"message": "API está rodando!"}
