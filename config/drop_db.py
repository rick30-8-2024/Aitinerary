"""Script to drop all collections from the MongoDB database."""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from config.settings import settings


async def drop_all_collections():
    """Drop all collections from the database."""
    print(f"Connecting to MongoDB at: {settings.MONGODB_URL}")
    print(f"Database name: {settings.DATABASE_NAME}")
    
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.DATABASE_NAME]
    
    collections = await db.list_collection_names()
    
    if not collections:
        print("No collections found in the database.")
    else:
        print(f"\nFound {len(collections)} collection(s):")
        for collection_name in collections:
            print(f"  - {collection_name}")
        
        print("\n" + "=" * 50)
        confirm = input("Are you sure you want to drop ALL collections? (yes/no): ")
        
        if confirm.lower() == "yes":
            print("\nDropping collections...")
            for collection_name in collections:
                await db.drop_collection(collection_name)
                print(f"  ✓ Dropped: {collection_name}")
            print("\n✓ All collections have been dropped successfully!")
        else:
            print("\n✗ Operation cancelled. No collections were dropped.")
    
    client.close()


if __name__ == "__main__":
    asyncio.run(drop_all_collections())
