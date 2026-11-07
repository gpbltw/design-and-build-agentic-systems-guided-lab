from typing import Any, TypedDict, Optional
from agents import function_tool, RunContextWrapper
import re
from typing import Dict
import json

"""
Exercise tools for the Agents Lab.

Read `labs/lab02_agents_guided/README.md` for the end-to-end instructions.
These functions are MOCK implementations to practice validation, error handling,
and consistent outputs for an agent that calls tools.

Implementations guidance (do during the exercise):
- Validate and sanitize inputs; raise `ValueError` for missing/invalid arguments.
- Keep outputs concise and user-friendly; avoid leaking internal details.
- Do not call external services; keep all data clearly marked as mock.

If you are stuck, consult `tools_solution.py` for reference only. Do not copy it directly.
"""

class OrderLookupArgs(TypedDict):
    """Arguments required for looking up an order."""
    order_id: str

#Step 1.1: Define the OrderDetails class
class OrderDetails(TypedDict):
    """
    JSON object representing the details of an order.

    Fields:
        order_id (str): The unique identifier for the order.
        order_status (str): The current status of the order (e.g., "IN_TRANSIT").
        order_date (str): The date the order was placed (ISO format recommended).
        order_total (float): The total amount for the order.

    This class is used to structure order information as a JSON object for mock responses.
    """
    order_id: str
    order_status: str
    order_date: str
    order_total: float

#Step 1.2: Mock database for orders
ORDERS_DB: Dict[str, OrderDetails] = {
    "A123-456": {
        "order_id": "A123-456",
        "order_status": "WAITING_FOR_PAYMENT",
        "order_date": "2025-09-05",
        "order_total": 100.00
    },
    "A123-457": {
        "order_id": "A123-457",
        "order_status": "IN_TRANSIT",
        "order_date": "2025-09-05",
        "order_total": 100.00
    },
    "A123-458": {
        "order_id": "A123-458",
        "order_status": "DELIVERED",
        "order_date": "2025-09-05",
        "order_total": 100.00
    }
}

#Step 2 Extend the helper function to validate the order_id format.
# This is a helper function used by multiple tool functions to validate that an order_id is provided.
# Implement the helper function to validate the order_id format.
def _require_order_id(order_id: Optional[str]) -> None:
    if not order_id or not str(order_id).strip():
        raise ValueError("Missing required argument: order_id")
    order_id = str(order_id).strip()
    if not re.fullmatch(r"A\d{3}-\d{3}", order_id):
        raise ValueError("Invalid order_id format; expected alphanumerics/hyphens")

#Step 1: Implement the lookup_order tool with mock data to look up an order by ID. Following Step 1.1 and Step 1.2.
# If no order is found, raise a ValueError.
@function_tool
def lookup_order(ctx: RunContextWrapper[Any], order_id: str) -> str:
    """
    Look up an order by ID.

    Args:
        ctx: The runtime context for the tool (not used in this mock implementation).
        args: A dictionary containing the required argument:
            - order_id (str): The order identifier (e.g., "A123-456").

    Returns:
        str: A JSON string containing the order details.

    Raises:
        ValueError: If the order_id is missing, invalid, or not found in the database.
    """

    _require_order_id(order_id)
    if order_id not in ORDERS_DB:
        raise ValueError(f"Order {order_id} not found")
    order = ORDERS_DB[order_id]


    result = {
        "order_id": order["order_id"],
        "order_status": order["order_status"],
        "order_date": order["order_date"],
        "order_total": order["order_total"]
    }
    return json.dumps(result)

#Step 3: Implement a mock complaint tool
@function_tool
def raise_complaint(ctx: RunContextWrapper[Any], dummy: str = "none") -> str:
    """
    Raise the customer complaint in the system.
    Args:
        dummy: Do not use this argument.
    """
    return "Complaint intake started. A support specialist will follow up via your account email. [MOCK]"

#Step 4: Implement the check_payment_methods tool, and add a few payment methods.
PAYMENT_METHODS = "Accepted payment methods: Visa, Mastercard, Amex, PayPal."
@function_tool
def check_payment_methods(ctx: RunContextWrapper[Any], dummy: str = "none") -> str:
    """
    List accepted payment methods.
    Args:
        dummy: Do not use this argument.
    """
    return PAYMENT_METHODS


#Step 5: Implement a mock cancel_order tool
#Step 5.1: Ensure to validate the order_id format and raise a ValueError if it is missing or does not match the expected format.
class CancelOrderArgs(TypedDict):
    """Arguments required for canceling an order."""
    order_id: str

@function_tool
def cancel_order(ctx: RunContextWrapper[Any], order_id: str) -> str:
    """
    Cancel an order by its order ID.
    """
    _require_order_id(order_id) # <-- Без args['order_id']
    if order_id not in ORDERS_DB:
        raise ValueError(f"Order {order_id} not found")
    
    order = ORDERS_DB[order_id]
    order['order_status'] = "CANCELLED"
    return f"Cancellation initiated for order {order_id}. The order status is now CANCELLED."

#Step 6: Implementing Tool for FAQ Retrieval by using the FAQ_DATA with the tool function FAQ_retrieval

#Sample FAQ data.
FAQ_DATA = [
    {
        "question": "What are your customer service hours?",
        "answer": "Our customer service is available Monday to Friday, 9am–5pm PT."
    },
    {
        "question": "How can I contact customer support?",
        "answer": "You can reach us at support@example.com or call +1-800-000-0000."
    },
    {
        "question": "How do I reset my account password?",
        "answer": "To reset your password, visit the login page and click on 'Forgot Password'. Follow the instructions sent to your email."
    },
    {
        "question": "Where can I track my order?",
        "answer": "You can track your order by logging into your account and visiting the 'Orders' section."
    },
    {
        "question": "What payment methods do you accept?",
        "answer": "We accept Visa, Mastercard, Amex, and PayPal."
    },
    {
        "question": "How do I cancel my order?",
        "answer": "To cancel your order, please log in to your account, go to 'Orders', select the order, and click 'Cancel'."
    },
    {
        "question": "Can I change my shipping address after placing an order?",
        "answer": "If your order has not shipped, you can update your shipping address in the 'Orders' section of your account."
    },
    {
        "question": "How long does delivery take?",
        "answer": "Standard delivery takes 3–5 business days after your order is processed."
    },
    {
        "question": "Do you offer international shipping?",
        "answer": "Yes, we offer international shipping to select countries. Please see our shipping policy for details."
    },
    {
        "question": "What is your return policy?",
        "answer": "You can return most items within 30 days of delivery for a full refund. Please visit our returns page for instructions."
    }
]

@function_tool
def FAQ_retrieval(ctx: RunContextWrapper[Any], dummy: str = "none") -> str:
    """
    Provide a static FAQ with sample customer service questions and answers.

    Returns:
        A formatted string listing FAQ question and answer pairs.
    
    Args:
        dummy: Do not use this argument.
    """
    
        # Build a human-readable FAQ string
    try:
        # Build a human-readable FAQ string
        faq_lines = []
        for idx, item in enumerate(FAQ_DATA, 1):
            faq_lines.append(f"Q{idx}: {item['question']}\nA{idx}: {item['answer']}\n")
        return "\n".join(faq_lines)
    except Exception as e:
        # Log the error for debugging and return a generic error message
        print(f"[ERROR] contact_customer_service FAQ retrieval failed: {e}")
        return "Sorry, we are unable to retrieve the FAQ at this time. Please try again later."