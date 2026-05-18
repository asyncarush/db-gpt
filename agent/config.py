from dataclasses import dataclass

@dataclass  
class Config:
    model_name: str = "llama-3.3-70b-versatile"
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    temperature: float = 0.0
    db_uri: str = "postgresql://postgres:postgres@localhost:5432/prodrag"