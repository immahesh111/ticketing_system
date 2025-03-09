from pymongo import MongoClient
import certifi

# MongoDB Connection
client = MongoClient(
    "mongodb+srv://aarushibawejaji:heya@cluster0.imgm1l7.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0",
    tlsCAFile=certifi.where()
)
db = client["ticketing_system"]
users_collection = db["users"]
tickets_collection = db["tickets"]

# Delete all documents
users_result = users_collection.delete_many({})
tickets_result = tickets_collection.delete_many({})

print(f"Deleted {users_result.deleted_count} user records.")
print(f"Deleted {tickets_result.deleted_count} ticket records.")
print("All data cleared successfully!")