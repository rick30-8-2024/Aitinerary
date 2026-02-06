"""Payment service for Razorpay integration and credit management."""

import razorpay
import hmac
import hashlib
import logging
from datetime import datetime
from bson import ObjectId

from config.settings import settings
from config.database import database

logger = logging.getLogger(__name__)


class PaymentService:
    """Handles Razorpay payment operations and credit management."""

    def __init__(self):
        self.client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )

    def create_order(self, amount: int, user_id: str) -> dict:
        """Create a Razorpay order for the given amount in INR (paise)."""
        order_data = {
            "amount": amount * 100,
            "currency": "INR",
            "notes": {
                "user_id": user_id,
                "purpose": "credit_recharge"
            }
        }
        return self.client.order.create(data=order_data)

    def verify_payment_signature(
        self, order_id: str, payment_id: str, signature: str
    ) -> bool:
        """Verify Razorpay payment signature using HMAC SHA256."""
        message = f"{order_id}|{payment_id}"
        generated_signature = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(generated_signature, signature)

    async def save_transaction(
        self,
        user_id: str,
        order_id: str,
        payment_id: str,
        amount: int,
        status: str
    ) -> str:
        """Save a payment transaction record to the database."""
        collection = database.get_collection("transactions")
        doc = {
            "user_id": user_id,
            "order_id": order_id,
            "payment_id": payment_id,
            "amount": amount,
            "status": status,
            "created_at": datetime.utcnow()
        }
        result = await collection.insert_one(doc)
        return str(result.inserted_id)

    async def add_credits(self, user_id: str, amount: int) -> int:
        """Add credits to user account. Returns new balance."""
        collection = database.get_collection("users")
        result = await collection.find_one_and_update(
            {"_id": ObjectId(user_id)},
            {"$inc": {"credits": amount}},
            return_document=True
        )
        return result.get("credits", 0) if result else 0

    async def deduct_credits(self, user_id: str, amount: int) -> bool:
        """Deduct credits from user account. Returns True if successful."""
        collection = database.get_collection("users")
        result = await collection.update_one(
            {"_id": ObjectId(user_id), "credits": {"$gte": amount}},
            {"$inc": {"credits": -amount}}
        )
        return result.modified_count > 0

    async def refund_credits(self, user_id: str, amount: int) -> int:
        """Refund credits to user account. Returns new balance."""
        collection = database.get_collection("users")
        result = await collection.find_one_and_update(
            {"_id": ObjectId(user_id)},
            {"$inc": {"credits": amount}},
            return_document=True
        )
        new_balance = result.get("credits", 0) if result else 0
        logger.info(f"Refunded {amount} credits to user {user_id}. New balance: {new_balance}")
        return new_balance

    async def get_user_credits(self, user_id: str) -> int:
        """Get the current credit balance for a user."""
        collection = database.get_collection("users")
        user = await collection.find_one({"_id": ObjectId(user_id)}, {"credits": 1})
        return user.get("credits", 0) if user else 0


payment_service = PaymentService()
