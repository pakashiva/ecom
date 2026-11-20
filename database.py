
import os

from dotenv import load_dotenv
from sqlalchemy import URL, create_engine

load_dotenv()

database_url = URL.create(
    drivername="postgresql+psycopg",
    database="ecom",
    host="127.0.0.1",
    port=5432,
    username="shiva",
    password=os.getenv("DBPASSWORD")
)

engine = create_engine(
    database_url,
    pool_size=7,
    pool_recycle=1800,
    pool_pre_ping=True,
    max_overflow=3
)
