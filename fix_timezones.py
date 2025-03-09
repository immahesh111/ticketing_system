from pymongo import MongoClient
import pytz
import certifi
from datetime import datetime

client = MongoClient(
    "mongodb+srv://aarushibawejaji:heya@cluster0.imgm1l7.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0",
    tlsCAFile=certifi.where()
)
db = client["ticketing_system"]
tickets_collection = db["tickets"]
ist = pytz.timezone('Asia/Kolkata')

updated_count = 0
for ticket in tickets_collection.find():
    updated = False
    if ticket.get("start_time") and not ticket["start_time"].tzinfo:
        localized_start = ist.localize(ticket["start_time"])
        tickets_collection.update_one(
            {"_id": ticket["_id"]},
            {"$set": {"start_time": localized_start}}
        )
        updated = True
    if ticket.get("close_time") and not ticket["close_time"].tzinfo:
        localized_close = ist.localize(ticket["close_time"])
        tickets_collection.update_one(
            {"_id": ticket["_id"]},
            {"$set": {"close_time": localized_close}}
        )
        updated = True
    if updated:
        updated_count += 1

print(f"✅ Updated {updated_count} tickets with IST timezone.")