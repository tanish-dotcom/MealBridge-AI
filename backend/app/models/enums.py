"""String-backed enum constants shared across models, schemas, and API logic."""
from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    donor = "donor"
    ngo = "ngo"
    admin = "admin"


class DonorType(str, Enum):
    restaurant = "restaurant"
    household = "household"
    event = "event"
    grocery = "grocery"
    other = "other"


class VerificationStatus(str, Enum):
    pending = "pending"
    verified = "verified"
    rejected = "rejected"
    suspended = "suspended"


class DonationStatus(str, Enum):
    pending_match = "pending_match"
    awaiting_response = "awaiting_response"
    matched = "matched"
    picked_up = "picked_up"
    completed = "completed"
    unmatched = "unmatched"
    cancelled = "cancelled"
    expired = "expired"


class QuantityUnit(str, Enum):
    meals = "meals"
    kg = "kg"
    packets = "packets"


class MatchRequestStatus(str, Enum):
    offered = "offered"
    accepted = "accepted"
    rejected = "rejected"
    expired = "expired"


class FoodCategory(str, Enum):
    hot_meals = "hot_meals"
    packaged_food = "packaged_food"
    bakery = "bakery"
    fruits_vegetables = "fruits_vegetables"
    dairy = "dairy"
    beverages = "beverages"
    grains = "grains"
    snacks = "snacks"
    other = "other"


class NotificationType(str, Enum):
    donation_posted = "donation_posted"
    match_found = "match_found"
    request_received = "request_received"
    request_accepted = "request_accepted"
    request_rejected = "request_rejected"
    request_expired = "request_expired"
    pickup_confirmed = "pickup_confirmed"
    verification_status = "verification_status"
    admin_flag = "admin_flag"


class PreferencesSchema:
    """Keys stored in User.preferences JSON: email_notifications, sms_alerts."""
    email_notifications = "email_notifications"
    sms_alerts = "sms_alerts"
