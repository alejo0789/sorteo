import uvicorn
import os

if __name__ == "__main__":
    print("Iniciando Servidor Acertemos...")
    print("API: http://localhost:8034")
    print("Documentación (Swagger): http://localhost:8034/docs")
    
    # Standard run for Python >= 3.8
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8034, reload=True)
