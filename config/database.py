"""Database configuration for async MongoDB connection using Motor."""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional

from config.settings import settings


class Database:
    """MongoDB database connection manager."""
    
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None
    
    async def connect(self) -> None:
        """Establish connection to MongoDB."""
        self.client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            maxPoolSize=10,
            minPoolSize=1
        )
        self.db = self.client[settings.DATABASE_NAME]
        
    async def disconnect(self) -> None:
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            
    async def health_check(self) -> bool:
        """Check if database connection is healthy."""
        try:
            await self.client.admin.command("ping")
            return True
        except Exception:
            return False
    
    def get_database(self) -> AsyncIOMotorDatabase:
        """Get database instance."""
        return self.db
    
    def get_collection(self, collection_name: str):
        """Get a specific collection from the database."""
        return self.db[collection_name]


database = Database()


async def get_database() -> AsyncIOMotorDatabase:
    """Dependency to get database instance."""
    return database.get_database()
