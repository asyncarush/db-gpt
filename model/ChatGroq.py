from langchain_groq import ChatGroq
from dotenv import load_dotenv
from agent.config import Config

load_dotenv()

config = Config()

llm_model = ChatGroq(
    model=config.model_name
)
