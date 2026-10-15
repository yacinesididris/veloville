import os
from dotenv import load_dotenv

load_dotenv()


DATABASE_URL = os.environ["DATABASE_URL"]

JWT_SECRET=os.environ["JWT_SECRET"]

JWT_ALGORITHM=os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(
    os.getenv("JWT_EXPIRATION_MINUTES", os.getenv("JWT_EXPIRE_MINUTES", "30"))
)