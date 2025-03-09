from pymongo import MongoClient
from flask_bcrypt import Bcrypt
import certifi

# MongoDB Connection
client = MongoClient("mongodb+srv://aarushibawejaji:heya@cluster0.imgm1l7.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0", tlsCAFile=certifi.where())

db = client["ticketing_system"]  # Updated to match app.py
tickets_collection = db["tickets"]  # Collection for tickets
users_collection = db["users"]  # Collection for users

# Initialize Bcrypt for password hashing
bcrypt = Bcrypt()

# Predefined Users
users = [
    {"username": "p1", "password": "password", "role": "production"},
    {"username": "eng", "password": "password", "role": "engineering"},
    {"username": "engineer2", "password": "password", "role": "engineering"}
]

# Insert or Update Users in MongoDB
for user in users:
    # Hash the password before storing it
    hashed_password = bcrypt.generate_password_hash(user["password"]).decode("utf-8")
    
    # Update user if exists, otherwise insert
    users_collection.update_one(
        {"username": user["username"]},  # Search by username
        {"$set": {"password": hashed_password, "role": user["role"]}},  
        upsert=True  # Insert if not found
    )

print("✅ All user credentials updated successfully in MongoDB!")

# Verify inserted data
print("🔹 Current Users in Database:")
for user in users_collection.find({}, {"_id": 0, "username": 1, "role": 1}):
    print(user)
