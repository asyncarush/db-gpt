from agent.config import Config
from langchain_community.utilities import SQLDatabase

config = Config()

print(f"Connecting to database: {config.db_uri}")

db = SQLDatabase.from_uri(config.db_uri)

