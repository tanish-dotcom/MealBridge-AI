"""Development seed script.

Run:  python -m app.seed.seed
Creates: seeded admin, fake restaurants, verified/pending NGOs, and a realistic
set of donations spread over the last 6 months so every screen (including the
admin/impact charts) has data. Idempotent: skips creation when users already exist.
"""
from __future__ import annotations

import asyncio
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import async_session_factory
from app.core.security import hash_password
from app.models import (
    Address,
    Donation,
    DonorProfile,
    MatchRequest,
    NGOProfile,
    Notification,
    RefreshToken,
    User,
)
from app.models.enums import (
    DonationStatus,
    MatchRequestStatus,
    NotificationType,
    Role,
    VerificationStatus,
)
from app.services import geocoding

random.seed(42)

# (name, area, lat, lng)
BENGALURU_AREAS = [
    ("Indiranagar", 12.9719, 77.6412),
    ("Koramangala", 12.9352, 77.6245),
    ("Jayanagar", 12.9250, 77.5938),
    ("MG Road", 12.9756, 77.6040),
    ("HSR Layout", 12.9121, 77.6446),
    ("Whitefield", 12.9698, 77.7500),
    ("Malleshwaram", 13.0041, 77.5667),
    ("RT Nagar", 13.0207, 77.5944),
    ("BTM Layout", 12.9166, 77.6101),
    ("Electronic City", 12.8452, 77.6602),
    ("Hebbal", 13.0358, 77.5970),
    ("Kalyan Nagar", 13.0201, 77.6413),
]

RESTAURANTS = [
    ("Spice Junction", "Rahul Verma"),
    ("Green Bowl Cafe", "Priya Sharma"),
    ("The Dosa Corner", "Manoj Kumar"),
    ("Saffron Bistro", "Anita Reddy"),
    ("Copper Chimney", "Vikram Singh"),
    ("Tandoor Nights", "Farhan Ali"),
    ("Fresh Harvest Cafe", "Deepa Iyer"),
    ("Mumbai Masala", "Suresh Pillai"),
    ("Pasta Alley", "Nina Fernandes"),
    ("Cantonese Wok", "Li Wei"),
]

NGOS = [
    ("Akshaya Trust", "AKS-2021-0841", "Sundar Krishnan", 1500, ["Perishable meals OK", "No pork", "Halal"]),
    ("Seva Samraksha", "SEV-2019-5520", "Meera Nair", 900, ["Vegetarian only", "No onions", "No garlic"]),
    ("Annapoorna Foundation", "ANP-2018-1123", "Ravi Bhat", 1200, ["Perishable meals OK", "No nuts"]),
    ("Roti Bank", "ROT-2020-7789", "Kavitha Rao", 2000, []),
    ("Meal Mates NGO", "MMN-2022-3310", "Arjun Menon", 700, ["Vegan only"]),
    ("Feed the City", "FTC-2017-9902", "Lakshmi Devi", 2500, ["Perishable meals OK"]),
    ("Bhojan Seva", "BHO-2021-4477", "Ganesh Prabhu", 800, ["Non-veg OK"]),
    ("Hope Kitchen", "HOP-2020-1234", "Shweta Joshi", 1100, ["Perishable meals OK", "Certified storage required"]),
]

PENDING_NGOS = [
    ("New Dawn Foundation", "NDF-2026-0001", "Priyanka Rao", 500, []),
    ("Unity Meals", "UNT-2026-0002", "Imran Shaikh", 600, []),
]

FOOD_ITEMS = [
    ("Veg Biryani", "hot_meals"),
    ("Paneer Butter Masala", "hot_meals"),
    ("Masala Dosa", "hot_meals"),
    ("Dal Tadka", "hot_meals"),
    ("Idli Sambar", "hot_meals"),
    ("Bread Packets", "packaged_food"),
    ("Fresh Vegetables", "fruits_vegetables"),
    ("Cooking Oil Bottles", "packaged_food"),
    ("Cookies Box", "snacks"),
    ("Rice 25kg Bags", "grains"),
    ("Milk Cartons", "dairy"),
    ("Fruit Boxes", "fruits_vegetables"),
    ("Samosa Trays", "snacks"),
    ("Bottled Water", "beverages"),
]

ADMIN = ("admin@mealbridge.ai", "Admin@12345", "System", "Administrator")


async def _get_or_create_address(session: AsyncSession, line1: str, city: str, lat: float, lng: float) -> Address:
    addr = Address(
        line1=f"{line1}, {city}", city=city, state="Karnataka", country="India", lat=lat, lng=lng
    )
    session.add(addr)
    await session.flush()
    if settings.use_postgis:
        await geocoding.sync_geography(session, str(addr.id), lat, lng)
    return addr


async def _make_user(session: AsyncSession, email: str, phone: str, password: str, role: str, name: str) -> User:
    existing = (await session.execute(select(User.id).where(User.email == email))).first()
    if existing:
        return (await session.execute(select(User).where(User.email == email))).scalar_one()
    user = User(
        email=email,
        phone=phone,
        password_hash=hash_password(password),
        role=role,
        first_name=name,
        preferences={"email_notifications": True, "sms_alerts": False},
    )
    session.add(user)
    await session.flush()
    return user


async def seed(session: AsyncSession) -> None:
    # --- Admin ---
    admin = await _make_user(
        session, settings.seed_admin_email, "+919000000000", settings.seed_admin_password, Role.admin.value, "System Admin"
    )

    # --- Restaurants ---
    donors: list[tuple[User, DonorProfile, float, float]] = []
    for i, (name, owner) in enumerate(RESTAURANTS):
        email = f"{name.lower().replace(' ', '.')}@restaurant.demo"
        user = await _make_user(session, email, f"+9198000{i:04d}", "Donor@12345", Role.donor.value, owner)
        existing = (
            await session.execute(
                select(DonorProfile)
                .where(DonorProfile.user_id == user.id)
                .options(selectinload(DonorProfile.address))
            )
        ).scalar_one_or_none()
        if existing:
            lat = existing.address.lat if existing.address else settings.seed_city_lat
            lng = existing.address.lng if existing.address else settings.seed_city_lng
            donors.append((user, existing, lat, lng))
            continue
        area = BENGALURU_AREAS[i % len(BENGALURU_AREAS)]
        lat = area[1] + random.uniform(-0.005, 0.005)
        lng = area[2] + random.uniform(-0.005, 0.005)
        addr = await _get_or_create_address(session, f"{i+1}, Main Road, {area[0]}", settings.seed_city, lat, lng)
        profile = DonorProfile(
            user_id=user.id,
            restaurant_name=name,
            owner_name=owner,
            donor_type="restaurant",
            address_id=addr.id,
            is_verified=True,
        )
        session.add(profile)
        await session.flush()
        donors.append((user, profile, lat, lng))

    # --- Verified NGOs ---
    ngos: list[NGOProfile] = []
    for i, (name, reg, contact, capacity, requirements) in enumerate(NGOS):
        email = f"{name.lower().replace(' ', '.')}@ngo.demo"
        user = await _make_user(session, email, f"+9197000{i:04d}", "Ngo@12345", Role.ngo.value, contact)
        existing = (
            await session.execute(select(NGOProfile).where(NGOProfile.user_id == user.id))
        ).scalar_one_or_none()
        if existing:
            ngos.append(existing)
            continue
        area = BENGALURU_AREAS[(i + 3) % len(BENGALURU_AREAS)]
        lat = area[1] + random.uniform(-0.004, 0.004)
        lng = area[2] + random.uniform(-0.004, 0.004)
        addr = await _get_or_create_address(session, f"{i+1}, Community Center, {area[0]}", settings.seed_city, lat, lng)
        profile = NGOProfile(
            user_id=user.id,
            org_name=name,
            registration_number=reg,
            contact_person=contact,
            verification_status=VerificationStatus.verified.value,
            capacity_meals_per_day=capacity,
            food_requirements=requirements,
            address_id=addr.id,
            reliability_score=round(random.uniform(3.4, 4.9), 1),
        )
        session.add(profile)
        await session.flush()
        ngos.append(profile)

    # --- Pending NGOs ---
    for i, (name, reg, contact, capacity, requirements) in enumerate(PENDING_NGOS):
        email = f"{name.lower().replace(' ', '.')}@ngo.demo"
        user = await _make_user(session, email, f"+9196000{i:04d}", "Ngo@12345", Role.ngo.value, contact)
        existing = (
            await session.execute(select(NGOProfile).where(NGOProfile.user_id == user.id))
        ).scalar_one_or_none()
        if existing:
            continue
        area = BENGALURU_AREAS[(i + 5) % len(BENGALURU_AREAS)]
        lat = area[1] + random.uniform(-0.004, 0.004)
        lng = area[2] + random.uniform(-0.004, 0.004)
        addr = await _get_or_create_address(session, f"{i+1}, NGO Street, {area[0]}", settings.seed_city, lat, lng)
        session.add(
            NGOProfile(
                user_id=user.id,
                org_name=name,
                registration_number=reg,
                contact_person=contact,
                verification_status=VerificationStatus.pending.value,
                capacity_meals_per_day=capacity,
                food_requirements=requirements,
                address_id=addr.id,
                reliability_score=0.0,
            )
        )

    # --- Donations across the last 6 months (for charts) ---
    now = datetime.now(timezone.utc)
    donation_count = await session.execute(select(Donation.id).limit(1))
    if donation_count.first():
        # Existing donations already seeded; skip history to stay idempotent.
        await session.commit()
        return

    for month_ago in range(6, -1, -1):
        base = now - timedelta(days=30 * month_ago)
        per_month = 6 if month_ago > 0 else 3
        for k in range(per_month):
            donor_user, donor_profile, donor_lat, donor_lng = random.choice(donors)
            food_name, category = random.choice(FOOD_ITEMS)
            qty = random.choice([25, 40, 50, 60, 75, 100, 120, 150])
            unit = random.choice(["meals", "meals", "kg", "packets"])
            created = base - timedelta(days=random.randint(0, 25), hours=random.randint(0, 10))
            best_before = created + timedelta(hours=random.randint(4, 20))

            status = "completed" if month_ago > 0 else random.choice(
                [DonationStatus.completed.value] * 3
                + [DonationStatus.awaiting_response.value]
                + [DonationStatus.matched.value]
                + [DonationStatus.pending_match.value]
                + [DonationStatus.expired.value]
            )

            addr = await _get_or_create_address(
                session,
                f"{k+1}, {donor_profile.restaurant_name}, {BENGALURU_AREAS[random.randrange(len(BENGALURU_AREAS))][0]}",
                settings.seed_city,
                donor_lat,
                donor_lng,
            )
            donation = Donation(
                donor_id=donor_user.id,
                address_id=addr.id,
                food_name=food_name,
                food_category=category,
                quantity_value=qty,
                quantity_unit=unit,
                best_before=best_before,
                notes=random.choice(
                    ["Packaged in sealed containers.", "Needs cold storage.", "Ready to collect immediately.", None, "Please bring containers."]
                ),
                status=status,
                pickup_lat=addr.lat,
                pickup_lng=addr.lng,
                created_at=created,
                updated_at=created,
            )

            if status == "completed":
                donation.completed_by_donor = True
                donation.completed_by_ngo = True
                matched_ngo = random.choice(ngos)
                donation.matched_ngo_id = matched_ngo.id
            elif status == "matched":
                donation.completed_by_donor = False
                donation.completed_by_ngo = False
                matched_ngo = random.choice(ngos)
                donation.matched_ngo_id = matched_ngo.id
            session.add(donation)
            await session.flush()

            if status in ("completed", "matched"):
                ngo = donation.matched_ngo_id and random.choice(ngos)
                if ngo:
                    session.add(
                        MatchRequest(
                            donation_id=donation.id,
                            ngo_id=ngo.id,
                            rank_score=round(random.uniform(0.5, 0.95), 3),
                            match_percent=random.randint(85, 99),
                            distance_km=round(random.uniform(0.8, 9.0), 2),
                            status=MatchRequestStatus.accepted.value if status == "completed" else MatchRequestStatus.accepted.value,
                            offered_at=created,
                            responded_at=created + timedelta(minutes=15),
                        )
                    )
            elif status == "awaiting_response":
                ngo = random.choice(ngos)
                session.add(
                    MatchRequest(
                        donation_id=donation.id,
                        ngo_id=ngo.id,
                        rank_score=round(random.uniform(0.6, 0.98), 3),
                        match_percent=random.randint(88, 99),
                        distance_km=round(random.uniform(0.5, 8.0), 2),
                        status=MatchRequestStatus.offered.value,
                        offered_at=created,
                    )
                )

    # --- Live donation awaiting a response so the NGO dashboard shows activity ---
    donor_user, donor_profile, donor_lat, donor_lng = donors[0]
    addr = await _get_or_create_address(
        session,
        f"{donor_profile.restaurant_name}, pickup point",
        settings.seed_city,
        donor_lat,
        donor_lng,
    )
    live = Donation(
        donor_id=donor_user.id,
        address_id=addr.id,
        food_name="Veg Biryani (50 portions)",
        food_category="hot_meals",
        quantity_value=50,
        quantity_unit="meals",
        best_before=now + timedelta(hours=6),
        notes="Hot, in sealed foil containers. Ready for immediate pickup.",
        status=DonationStatus.awaiting_response.value,
        pickup_lat=addr.lat,
        pickup_lng=addr.lng,
        created_at=now - timedelta(minutes=20),
        updated_at=now - timedelta(minutes=20),
    )
    session.add(live)
    await session.flush()
    for ngo in ngos[:4]:
        session.add(
            MatchRequest(
                donation_id=live.id,
                ngo_id=ngo.id,
                rank_score=round(random.uniform(0.5, 0.97), 3),
                match_percent=random.randint(90, 99),
                distance_km=round(random.uniform(0.6, 7.0), 2),
                status=MatchRequestStatus.offered.value,
                offered_at=now - timedelta(minutes=20),
            )
        )

    # --- Sample notifications ---
    for user, profile, _, _ in donors[:2]:
        session.add(
            Notification(
                user_id=user.id,
                type=NotificationType.donation_posted.value,
                title="Donation posted",
                body="Your donation is now live and matching with nearby NGOs.",
                payload={"donation_id": str(live.id)},
                read_at=None,
                created_at=now - timedelta(minutes=20),
            )
        )

    await session.commit()
    print("Seed complete:")
    print(f"  admin:        {settings.seed_admin_email} / {settings.seed_admin_password}")
    print(f"  restaurants:  {len(RESTAURANTS)}")
    print(f"  verified ngos:{len(NGOS)}   pending: {len(PENDING_NGOS)}")
    print("  donations:    ~48 across 6 months (completed history + live)")


async def main() -> None:
    async with async_session_factory() as session:
        await seed(session)


if __name__ == "__main__":
    asyncio.run(main())
