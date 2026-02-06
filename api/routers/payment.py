"""Payment router for Razorpay credit recharge and verification."""

import logging
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Depends, status

from config.settings import settings
from api.dependencies import get_current_user
from models.user import UserResponse
from services.payment_service import payment_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/payment", tags=["Payment"])


class CreateOrderRequest(BaseModel):
    """Request schema for creating a Razorpay order."""
    amount: int = Field(..., ge=settings.MIN_RECHARGE_AMOUNT, description="Amount in INR")


class CreateOrderResponse(BaseModel):
    """Response schema with Razorpay order details."""
    order_id: str
    amount: int
    currency: str
    key_id: str


class VerifyPaymentRequest(BaseModel):
    """Request schema for verifying Razorpay payment."""
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    amount: int


class VerifyPaymentResponse(BaseModel):
    """Response schema after successful payment verification."""
    success: bool
    credits: int
    message: str


class CreditsResponse(BaseModel):
    """Response schema for credit balance."""
    credits: int


@router.post("/create-order", response_model=CreateOrderResponse)
async def create_order(
    request: CreateOrderRequest,
    current_user: UserResponse = Depends(get_current_user)
):
    """Create a Razorpay order for credit recharge."""
    if request.amount < settings.MIN_RECHARGE_AMOUNT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Minimum recharge amount is ₹{settings.MIN_RECHARGE_AMOUNT}"
        )

    try:
        order = payment_service.create_order(request.amount, current_user.id)
        logger.info(f"Created Razorpay order {order['id']} for user {current_user.id}, amount={request.amount}")

        return CreateOrderResponse(
            order_id=order["id"],
            amount=request.amount,
            currency="INR",
            key_id=settings.RAZORPAY_KEY_ID
        )
    except Exception as e:
        logger.error(f"Failed to create Razorpay order: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create payment order"
        )


@router.post("/verify", response_model=VerifyPaymentResponse)
async def verify_payment(
    request: VerifyPaymentRequest,
    current_user: UserResponse = Depends(get_current_user)
):
    """Verify Razorpay payment and add credits to user account."""
    is_valid = payment_service.verify_payment_signature(
        request.razorpay_order_id,
        request.razorpay_payment_id,
        request.razorpay_signature
    )

    if not is_valid:
        logger.warning(f"Invalid payment signature for order {request.razorpay_order_id}, user {current_user.id}")
        await payment_service.save_transaction(
            user_id=current_user.id,
            order_id=request.razorpay_order_id,
            payment_id=request.razorpay_payment_id,
            amount=request.amount,
            status="failed"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment verification failed"
        )

    new_balance = await payment_service.add_credits(current_user.id, request.amount)

    await payment_service.save_transaction(
        user_id=current_user.id,
        order_id=request.razorpay_order_id,
        payment_id=request.razorpay_payment_id,
        amount=request.amount,
        status="success"
    )

    logger.info(f"Payment verified for user {current_user.id}. Added {request.amount} credits. Balance: {new_balance}")

    return VerifyPaymentResponse(
        success=True,
        credits=new_balance,
        message=f"Successfully added ₹{request.amount} credits"
    )


@router.get("/credits", response_model=CreditsResponse)
async def get_credits(
    current_user: UserResponse = Depends(get_current_user)
):
    """Get the current credit balance for the authenticated user."""
    credits = await payment_service.get_user_credits(current_user.id)
    return CreditsResponse(credits=credits)
