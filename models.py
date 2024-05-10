from sqlalchemy import Column, String, Integer, LargeBinary
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(length=512), unique=True)  
    password = Column(LargeBinary, nullable=False)
    provider = Column(String, default="user")

    def __init__(self, username, password, provider="user"):
        self.username = username.strip()  # Remove leading and trailing whitespace
        self.password = password
        self.provider = provider