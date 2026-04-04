import uvicorn
from src.config import HOST, PORT

if __name__ == "__main__":
    uvicorn.run("src.api_server:app", host=HOST, port=PORT)
