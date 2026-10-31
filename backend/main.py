import os
import sys
import io
import base64
import json
import asyncio
from pathlib import Path
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import qrcode
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

load_dotenv(BASE_DIR / ".env")
load_dotenv()

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session
from passlib.context import CryptContext
import jwt

try:
    from database import get_db
except ImportError:
    from backend.database import get_db

async def background_slot_cleaner():
    while True:
        try:
            await asyncio.sleep(60)
            from database import SessionLocal
            with SessionLocal() as db:
                release_expired_bookings(db)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Error in background slot cleaner: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(background_slot_cleaner())
    yield
    task.cancel()


app = FastAPI(
    title="ParkSpot API",
    description="Parking Management System Backend",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Security Configurations
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-to-a-long-random-secret-key")
ALGORITHM = "HS256"

# Password security
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str
):
    try:
        return pwd_context.verify(
            plain_password,
            hashed_password
        )
    except Exception:
        return False


def create_access_token(data: dict, expires_minutes: int = 60):
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes
    )

    to_encode.update({
        "exp": expire
    })

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

# =========================================================
# REQUEST MODELS
# =========================================================
class ComplaintCreateRequest(BaseModel):
    user_id: int
    booking_id: int | None = None
    subject: str
    description: str

class ComplaintStatusUpdateRequest(BaseModel):
    status: str

class NotificationCreateRequest(BaseModel):
    user_id: int
    title: str
    message: str

class AdminUserStatusRequest(BaseModel):
    account_status: str

class AdminAssignManagerRequest(BaseModel):
    user_id: int
    location_id: int

class ScanQRRequest(BaseModel):
    booking_id: int
    action: str = "AUTO"

from pydantic import EmailStr

class UserRegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: str | None = None

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str

class PricingRuleRequest(BaseModel):
    location_id: int
    day_of_week: str
    start_time: str
    end_time: str
    price_per_hour: float

class SlotStatusRequest(BaseModel):
    status: str

class PaymentRequest(BaseModel):
    booking_id: int
    payment_method: str


class VehicleRequest(BaseModel):
    vehicle_number: str
    vehicle_type: str
    vehicle_model: str | None = None
class RatingRequest(BaseModel):
    user_id: int
    location_id: int
    booking_id: int
    rating: int
    review: str | None = None


class BookingStatusRequest(BaseModel):
    status: str


class BookingRequest(BaseModel):
    user_id: int
    vehicle_id: int
    slot_id: int
    start_time: str
    end_time: str

class ParkingRequest(BaseModel):
    location_name: str
    address: str
    latitude: float | None = None
    longitude: float | None = None
    capacity: int
    base_price: float

class SlotRequest(BaseModel):
    slot_number: str
    slot_type: str = "GENERAL"


class ArrivalInsightRequest(BaseModel):
    arrival_time: str

# =========================================================

# =========================================================
# HELPER UTILITIES: NOTIFICATIONS, QR PASS & AUTO-RELEASE
# =========================================================

def create_notification(db: Session, user_id: int, title: str, message: str):
    try:
        db.execute(
            text("""
                INSERT INTO notifications (user_id, title, message, is_read, created_at)
                VALUES (:user_id, :title, :message, FALSE, :created_at)
            """),
            {
                "user_id": user_id,
                "title": title,
                "message": message,
                "created_at": datetime.now(timezone.utc)
            }
        )
        db.commit()
    except Exception as e:
        print(f"Failed to create notification: {e}")


def generate_qr_code_base64(data: dict) -> str:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(json.dumps(data, default=str))
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0f172a", back_color="#ffffff")
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{img_str}"


def release_expired_bookings(db: Session):
    now = datetime.now(timezone.utc)
    expired = db.execute(
        text("""
            SELECT booking_id, slot_id, user_id
            FROM bookings
            WHERE end_time <= :now
              AND booking_status IN ('CONFIRMED', 'ACTIVE')
        """),
        {"now": now}
    ).mappings().all()

    released = 0
    for b in expired:
        db.execute(
            text("UPDATE bookings SET booking_status = 'COMPLETED' WHERE booking_id = :b_id"),
            {"b_id": b["booking_id"]}
        )
        db.execute(
            text("UPDATE parking_slots SET status = 'AVAILABLE' WHERE slot_id = :s_id"),
            {"s_id": b["slot_id"]}
        )
        create_notification(
            db,
            b["user_id"],
            "Booking Completed",
            f"Your booking #{b['booking_id']} has ended. Slot #{b['slot_id']} is now released."
        )
        released += 1

    if released > 0:
        db.commit()
    return released

# USER REGISTRATION
# =========================================================
@app.post("/register")
def register_user(
    user_data: UserRegisterRequest, 
    db: Session = Depends(get_db)
):
    # Check if the email is already registered
    existing_user = db.execute(
        text("SELECT user_id FROM users WHERE email = :email"),
        {"email": user_data.email}
    ).first()

    if existing_user:
        raise HTTPException(status_code=400, detail="Email is already registered")

    # Hash the password
    hashed_pwd = hash_password(user_data.password)

    # Get default role_id for regular USER (defaults to 1 if not found)
    role = db.execute(
        text("SELECT role_id FROM roles WHERE role_name = 'USER'")
    ).first()
    role_id = role[0] if role else 1

    # Insert new user into the database
    db.execute(
        text("""
            INSERT INTO users (role_id, name, email, password_hash, phone, created_at)
            VALUES (:role_id, :name, :email, :password_hash, :phone, :created_at)
        """),
        {
            "role_id": role_id,
            "name": user_data.name,
            "email": user_data.email,
            "password_hash": hashed_pwd,
            "phone": user_data.phone,
            "created_at": datetime.now(timezone.utc)
        }
    )
    db.commit()

    return {"message": "User registered successfully!"}



@app.post("/login")
def login_user(
    credentials: UserLoginRequest,
    db: Session = Depends(get_db)
):
    user = db.execute(
        text("""
            SELECT
                user_id,
                role_id,
                name,
                email,
                password_hash,
                account_status
            FROM users
            WHERE email = :email
        """),
        {"email": credentials.email}
    ).mappings().first()

    if not user or not verify_password(
        credentials.password,
        user["password_hash"]
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    if user["account_status"] == "INACTIVE":
        raise HTTPException(
            status_code=403,
            detail="Your account is inactive. Please contact support."
        )

    if user["account_status"] == "BLOCKED":
        raise HTTPException(
            status_code=403,
            detail="Your account has been blocked. Please contact support."
        )

    access_token = create_access_token(
        data={
            "user_id": user["user_id"],
            "email": user["email"],
            "role_id": user["role_id"]
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "user_id": user["user_id"],
            "role_id": user["role_id"],
            "name": user["name"],
            "email": user["email"],
            "account_status": user["account_status"]
        }
    }

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        user_id = payload.get("user_id")
        email = payload.get("email")
        role_id = payload.get("role_id")

        if user_id is None or email is None or role_id is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication token"
            )

        return {
            "user_id": user_id,
            "email": email,
            "role_id": role_id
        }

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Authentication token has expired"
        )

    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token"
        )
# =========================================================
# 1. HOME
# =========================================================

@app.get("/")
def home():
    index_file = BASE_DIR.parent / "frontend" / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {
        "message": "ParkSpot Backend is running!"
    }


# =========================================================
# 2. TEST DATABASE
# =========================================================

@app.get("/test-db")
def test_database(
    db: Session = Depends(get_db)
):

    result = db.execute(
        text("SELECT DATABASE()")
    ).scalar()

    return {
        "message": "MySQL connected successfully!",
        "database": result
    }


# =========================================================
# 3. GET PARKING LOCATIONS
# =========================================================

@app.get("/parking")
def get_parking(
    db: Session = Depends(get_db)
):

    result = db.execute(
        text("""
            SELECT
                pl.location_id,
                pl.location_name,
                pl.address,
                pl.capacity,
                pl.base_price,
                pl.status,

                COUNT(ps.slot_id) AS total_slots,

                SUM(
                    CASE
                        WHEN ps.status = 'AVAILABLE'
                        THEN 1
                        ELSE 0
                    END
                ) AS available_slots,

                SUM(
                    CASE
                        WHEN ps.status = 'OCCUPIED'
                        THEN 1
                        ELSE 0
                    END
                ) AS occupied_slots

            FROM parking_locations pl

            LEFT JOIN parking_slots ps
                ON pl.location_id = ps.location_id

            WHERE pl.status = 'ACTIVE'

            GROUP BY
                pl.location_id,
                pl.location_name,
                pl.address,
                pl.capacity,
                pl.base_price,
                pl.status

            ORDER BY pl.location_id
        """)
    )

    parking = result.mappings().all()

    return {
        "count": len(parking),
        "parking_locations": parking,
        "locations": parking
    }


# =========================================================
# 4. GET PARKING SLOTS
# =========================================================

@app.get("/parking/{location_id}/slots")
def get_parking_slots(
    location_id: int,
    db: Session = Depends(get_db)
):

    result = db.execute(
        text("""
            SELECT
                slot_id,
                slot_number,
                slot_type,
                status

            FROM parking_slots

            WHERE location_id = :location_id

            ORDER BY slot_number
        """),
        {
            "location_id": location_id
        }
    )

    slots = result.mappings().all()

    return {
        "location_id": location_id,
        "count": len(slots),
        "slots": slots
    }


# =========================================================
# 5. PARKING AVAILABILITY
# =========================================================

@app.get("/parking/{location_id}/availability")
def get_parking_availability(
    location_id: int,
    db: Session = Depends(get_db)
):

    result = db.execute(
        text("""
            SELECT
                COUNT(*) AS total_slots,

                SUM(
                    CASE
                        WHEN status = 'AVAILABLE'
                        THEN 1
                        ELSE 0
                    END
                ) AS available_slots,

                SUM(
                    CASE
                        WHEN status = 'OCCUPIED'
                        THEN 1
                        ELSE 0
                    END
                ) AS occupied_slots

            FROM parking_slots

            WHERE location_id = :location_id
        """),
        {
            "location_id": location_id
        }
    )

    availability = result.mappings().one()

    return {
        "location_id": location_id,
        "total_slots": availability["total_slots"],
        "available_slots": availability["available_slots"],
        "occupied_slots": availability["occupied_slots"]
    }


# =========================================================
# 6. CREATE BOOKING
# =========================================================

@app.post("/bookings")
def create_booking(
    booking: BookingRequest,
    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    #  Check slot
    # -----------------------------------------------------

    slot = db.execute(
        text("""
            SELECT
                slot_id,
                location_id,
                status

            FROM parking_slots

            WHERE slot_id = :slot_id
        """),
        {
            "slot_id": booking.slot_id
        }
    ).mappings().first()

    if not slot:

        raise HTTPException(
            status_code=404,
            detail="Parking slot not found"
        )

    # -----------------------------------------------------
    # Check user
    # -----------------------------------------------------

    user = db.execute(
        text("""
            SELECT user_id

            FROM users

            WHERE user_id = :user_id
        """),
        {
            "user_id": booking.user_id
        }
    ).first()

    if not user:

        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # -----------------------------------------------------
    #  Check vehicle
    # -----------------------------------------------------

    vehicle = db.execute(
        text("""
            SELECT vehicle_id

            FROM vehicles

            WHERE vehicle_id = :vehicle_id
              AND user_id = :user_id
        """),
        {
            "vehicle_id": booking.vehicle_id,
            "user_id": booking.user_id
        }
    ).first()

    if not vehicle:

        raise HTTPException(
            status_code=404,
            detail="Vehicle not found for this user"
        )

    # -----------------------------------------------------
    # Validate booking time
    # -----------------------------------------------------

    try:

        start_datetime = datetime.strptime(
            booking.start_time,
            "%Y-%m-%d %H:%M:%S"
        )

        end_datetime = datetime.strptime(
            booking.end_time,
            "%Y-%m-%d %H:%M:%S"
        )

    except ValueError:

        raise HTTPException(
            status_code=400,
            detail="Invalid date/time format. Use YYYY-MM-DD HH:MM:SS"
        )

    if start_datetime >= end_datetime:

        raise HTTPException(
            status_code=400,
            detail="End time must be after start time"
        )

    # -----------------------------------------------------
    #  Check overlapping booking
    # -----------------------------------------------------

    conflict = db.execute(
        text("""
            SELECT booking_id

            FROM bookings

            WHERE slot_id = :slot_id

              AND booking_status
                  NOT IN ('CANCELLED', 'COMPLETED')

              AND start_time < :end_time

              AND end_time > :start_time

            LIMIT 1
        """),
        {
            "slot_id": booking.slot_id,
            "start_time": booking.start_time,
            "end_time": booking.end_time
        }
    ).first()

    if conflict:

        raise HTTPException(
            status_code=409,
            detail="This parking slot is already booked for the selected time."
        )

    # -----------------------------------------------------
    #  Get parking price
    # -----------------------------------------------------

    parking = db.execute(
        text("""
            SELECT
                pl.location_id,
                pl.base_price

            FROM parking_locations pl

            JOIN parking_slots ps
                ON pl.location_id = ps.location_id

            WHERE ps.slot_id = :slot_id
              AND pl.status = 'ACTIVE'
        """),
        {
            "slot_id": booking.slot_id
        }
    ).mappings().first()

    if not parking:

        raise HTTPException(
            status_code=404,
            detail="Parking location not found or inactive"
        )

    # -----------------------------------------------------
    #  Calculate duration
    # -----------------------------------------------------

    duration_result = db.execute(
        text("""
            SELECT TIMESTAMPDIFF(
                MINUTE,
                :start_time,
                :end_time
            ) AS duration_minutes
        """),
        {
            "start_time": booking.start_time,
            "end_time": booking.end_time
        }
    ).scalar()

    if duration_result is None or duration_result <= 0:

        raise HTTPException(
            status_code=400,
            detail="Invalid booking duration"
        )

    duration_hours = duration_result / 60

    # -----------------------------------------------------
    #  Calculate amount
    # -----------------------------------------------------

    total_amount = round(
        duration_hours *
        float(parking["base_price"]),
        2
    )

    # -----------------------------------------------------
    #  Insert booking
    # -----------------------------------------------------

    result = db.execute(
        text("""
            INSERT INTO bookings
            (
                user_id,
                vehicle_id,
                slot_id,
                start_time,
                end_time,
                booking_status,
                total_amount
            )

            VALUES
            (
                :user_id,
                :vehicle_id,
                :slot_id,
                :start_time,
                :end_time,
                'CONFIRMED',
                :total_amount
            )
        """),
        {
            "user_id": booking.user_id,
            "vehicle_id": booking.vehicle_id,
            "slot_id": booking.slot_id,
            "start_time": booking.start_time,
            "end_time": booking.end_time,
            "total_amount": total_amount
        }
    )

    db.commit()

    booking_id = result.lastrowid

    # -----------------------------------------------------
    #  Return booking details
    # -----------------------------------------------------

    return {
        "message": "Booking created successfully!",
        "booking_id": booking_id,
        "slot_id": booking.slot_id,
        "start_time": booking.start_time,
        "end_time": booking.end_time,
        "duration_hours": duration_hours,
        "price_per_hour": float(parking["base_price"]),
        "total_amount": total_amount,
        "status": "CONFIRMED"
    }
# =========================================================
# 7. USER BOOKING HISTORY
# =========================================================

@app.get("/users/{user_id}/bookings")
def get_user_bookings(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    
    if user_id != current_user["user_id"] and current_user.get("role_id") not in [2, 3]:
        raise HTTPException(
            status_code=403,
            detail="You can only access your own bookings"
        )

    result = db.execute(
        text("""
            SELECT
                b.booking_id,
                pl.location_name,
                pl.address,
                ps.slot_number,
                ps.slot_type,
                v.vehicle_number,
                v.vehicle_model,
                b.start_time,
                b.end_time,
                b.booking_status,
                b.total_amount,
                b.created_at

            FROM bookings b

            JOIN vehicles v
                ON b.vehicle_id = v.vehicle_id

            JOIN parking_slots ps
                ON b.slot_id = ps.slot_id

            JOIN parking_locations pl
                ON ps.location_id = pl.location_id

            WHERE b.user_id = :user_id

            ORDER BY b.created_at DESC
        """),
        {
            "user_id": user_id
        }
    )

    bookings = result.mappings().all()

    return {
        "user_id": user_id,
        "count": len(bookings),
        "bookings": bookings
    }


# =========================================================
# 8. CREATE PAYMENT
# =========================================================

@app.post("/payments")
def create_payment(
    payment: PaymentRequest,
    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    # Check booking
    # -----------------------------------------------------

    booking = db.execute(
        text("""
            SELECT
                booking_id,
                total_amount,
                booking_status

            FROM bookings

            WHERE booking_id = :booking_id
        """),
        {
            "booking_id": payment.booking_id
        }
    ).mappings().first()

    if not booking:

        raise HTTPException(
            status_code=404,
            detail="Booking not found"
        )

    # -----------------------------------------------------
    #  Check booking status
    # -----------------------------------------------------

    booking_status = booking["booking_status"]

    if booking_status == "CANCELLED":

        raise HTTPException(
            status_code=400,
            detail="Payment cannot be made for a cancelled booking"
        )

    if booking_status == "COMPLETED":

        raise HTTPException(
            status_code=400,
            detail="Booking is already completed"
        )

    if booking_status != "CONFIRMED":

        raise HTTPException(
            status_code=400,
            detail="Payment is allowed only for confirmed bookings"
        )

    # -----------------------------------------------------
    #  Check existing payment
    # -----------------------------------------------------

    existing_payment = db.execute(
        text("""
            SELECT
                payment_id,
                payment_status

            FROM payments

            WHERE booking_id = :booking_id
        """),
        {
            "booking_id": payment.booking_id
        }
    ).mappings().first()

    if existing_payment:

        raise HTTPException(
            status_code=409,
            detail="Payment already exists for this booking"
        )

    # -----------------------------------------------------
    #  Validate payment method
    # -----------------------------------------------------

    allowed_methods = [
        "UPI",
        "CARD",
        "NET_BANKING",
        "CASH"
    ]

    payment_method = (
        payment.payment_method
        .strip()
        .upper()
    )

    if payment_method not in allowed_methods:

        raise HTTPException(
            status_code=400,
            detail="Invalid payment method"
        )

    # -----------------------------------------------------
    #  Generate transaction reference
    # -----------------------------------------------------

    transaction_reference = (
        f"PARKSPOT_TXN_{payment.booking_id}"
    )

    # -----------------------------------------------------
    #  Insert payment
    # -----------------------------------------------------

    db.execute(
        text("""
            INSERT INTO payments
            (
                booking_id,
                amount,
                payment_method,
                payment_status,
                transaction_reference,
                paid_at
            )

            VALUES
            (
                :booking_id,
                :amount,
                :payment_method,
                'SUCCESS',
                :transaction_reference,
                NOW()
            )
        """),
        {
            "booking_id": payment.booking_id,
            "amount": booking["total_amount"],
            "payment_method": payment_method,
            "transaction_reference": transaction_reference
        }
    )

    db.commit()

    # -----------------------------------------------------
    # Return payment details
    # -----------------------------------------------------

    return {
        "message": "Payment successful!",
        "booking_id": payment.booking_id,
        "amount": float(booking["total_amount"]),
        "payment_method": payment_method,
        "payment_status": "SUCCESS",
        "transaction_reference": transaction_reference
    }


# =========================================================
# 9. PAYMENT HISTORY
# =========================================================

@app.get("/users/{user_id}/payments")
def get_user_payments(
    user_id: int,
    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    #  Check user
    # -----------------------------------------------------

    user = db.execute(
        text("""
            SELECT
                user_id

            FROM users

            WHERE user_id = :user_id
        """),
        {
            "user_id": user_id
        }
    ).first()

    if not user:

        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # -----------------------------------------------------
    # Get payment history
    # -----------------------------------------------------

    result = db.execute(
        text("""
            SELECT
                p.payment_id,
                p.booking_id,
                pl.location_name,
                ps.slot_number,
                p.amount,
                p.payment_method,
                p.payment_status,
                p.transaction_reference,
                p.paid_at

            FROM payments p

            JOIN bookings b
                ON p.booking_id = b.booking_id

            JOIN parking_slots ps
                ON b.slot_id = ps.slot_id

            JOIN parking_locations pl
                ON ps.location_id = pl.location_id

            WHERE b.user_id = :user_id

            ORDER BY p.paid_at DESC
        """),
        {
            "user_id": user_id
        }
    )

    payments = result.mappings().all()

    # -----------------------------------------------------
    #  Return payment history
    # -----------------------------------------------------

    return {
        "user_id": user_id,
        "count": len(payments),
        "payments": [dict(payment) for payment in payments]
    }

# =========================================================
# 10. CANCEL BOOKING
# =========================================================

@app.post("/bookings/{booking_id}/cancel")
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    # Check booking
    # -----------------------------------------------------

    booking = db.execute(
        text("""
            SELECT
                booking_id,
                booking_status

            FROM bookings

            WHERE booking_id = :booking_id
        """),
        {
            "booking_id": booking_id
        }
    ).mappings().first()

    if not booking:

        raise HTTPException(
            status_code=404,
            detail="Booking not found"
        )

    # -----------------------------------------------------
    #  Check booking status
    # -----------------------------------------------------

    if booking["booking_status"] != "CONFIRMED":

        raise HTTPException(
            status_code=400,
            detail="Only confirmed bookings can be cancelled"
        )

    # -----------------------------------------------------
    #  Check payment
    # -----------------------------------------------------

    payment = db.execute(
        text("""
            SELECT
                payment_id,
                payment_status

            FROM payments

            WHERE booking_id = :booking_id
        """),
        {
            "booking_id": booking_id
        }
    ).mappings().first()

    # -----------------------------------------------------
    #  Cancel booking
    # -----------------------------------------------------

    db.execute(
        text("""
            UPDATE bookings

            SET booking_status = 'CANCELLED'

            WHERE booking_id = :booking_id
              AND booking_status = 'CONFIRMED'
        """),
        {
            "booking_id": booking_id
        }
    )

    # -----------------------------------------------------
    # Handle payment refund
    # -----------------------------------------------------

    if payment and payment["payment_status"] == "SUCCESS":

        db.execute(
            text("""
                UPDATE payments

                SET payment_status = 'REFUNDED'

                WHERE payment_id = :payment_id
                  AND payment_status = 'SUCCESS'
            """),
            {
                "payment_id": payment["payment_id"]
            }
        )

        refund_status = "REFUNDED"

    elif payment and payment["payment_status"] == "REFUNDED":

        refund_status = "ALREADY_REFUNDED"

    elif payment:

        refund_status = payment["payment_status"]

    else:

        refund_status = "NO_PAYMENT"

    # -----------------------------------------------------
    # Save changes
    # -----------------------------------------------------

    db.commit()

    # -----------------------------------------------------
    #  Return cancellation details
    # -----------------------------------------------------

    return {
        "message": "Booking cancelled successfully!",
        "booking_id": booking_id,
        "booking_status": "CANCELLED",
        "payment_status": refund_status
    }

# =========================================================
# 11. ADD VEHICLE
# =========================================================

@app.post("/users/{user_id}/vehicles")
def add_vehicle(
    user_id: int,
    vehicle: VehicleRequest,
    db: Session = Depends(get_db)
):

    # Check user
    user = db.execute(
        text("""
            SELECT user_id

            FROM users

            WHERE user_id = :user_id
        """),
        {
            "user_id": user_id
        }
    ).first()

    if not user:

        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # Clean input
    vehicle_number = (
        vehicle.vehicle_number
        .strip()
        .upper()
    )

    vehicle_type = (
        vehicle.vehicle_type
        .strip()
        .upper()
    )

    # Validate vehicle type
    allowed_types = [
        "CAR",
        "BIKE",
        "SCOOTER",
        "EV",
        "OTHER"
    ]

    if vehicle_type not in allowed_types:

        raise HTTPException(
            status_code=400,
            detail="Invalid vehicle type"
        )

    # Check duplicate vehicle
    existing = db.execute(
        text("""
            SELECT vehicle_id

            FROM vehicles

            WHERE vehicle_number = :vehicle_number
        """),
        {
            "vehicle_number": vehicle_number
        }
    ).first()

    if existing:

        raise HTTPException(
            status_code=409,
            detail="Vehicle already exists"
        )

    # Insert vehicle
    result = db.execute(
        text("""
            INSERT INTO vehicles
            (
                user_id,
                vehicle_number,
                vehicle_type,
                vehicle_model
            )

            VALUES
            (
                :user_id,
                :vehicle_number,
                :vehicle_type,
                :vehicle_model
            )
        """),
        {
            "user_id": user_id,
            "vehicle_number": vehicle_number,
            "vehicle_type": vehicle_type,
            "vehicle_model": vehicle.vehicle_model
        }
    )

    db.commit()

    return {
        "message": "Vehicle added successfully!",
        "vehicle_id": result.lastrowid,
        "user_id": user_id,
        "vehicle_number": vehicle_number,
        "vehicle_type": vehicle_type,
        "vehicle_model": vehicle.vehicle_model
    }
# =========================================================
# 12. GET USER VEHICLES
# =========================================================

@app.get("/users/{user_id}/vehicles")
def get_user_vehicles(
    user_id: int,
    db: Session = Depends(get_db)
):

    user = db.execute(
        text("""
            SELECT user_id
            FROM users
            WHERE user_id = :user_id
        """),
        {"user_id": user_id}
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = db.execute(
        text("""
            SELECT
                vehicle_id,
                vehicle_number,
                vehicle_type,
                vehicle_model,
                created_at

            FROM vehicles

            WHERE user_id = :user_id

            ORDER BY vehicle_id
        """),
        {
            "user_id": user_id
        }
    )

    vehicles = result.mappings().all()

    return {
        "user_id": user_id,
        "count": len(vehicles),
        "vehicles": vehicles
    }

# =========================================================
# 13. DELETE VEHICLE
# =========================================================

@app.delete("/vehicles/{vehicle_id}")
def delete_vehicle(
    vehicle_id: int,
    db: Session = Depends(get_db)
):

    # Check vehicle
    vehicle = db.execute(
        text("""
            SELECT
                vehicle_id,
                vehicle_number
            FROM vehicles
            WHERE vehicle_id = :vehicle_id
        """),
        {
            "vehicle_id": vehicle_id
        }
    ).mappings().first()

    if not vehicle:

        raise HTTPException(
            status_code=404,
            detail="Vehicle not found"
        )

    # Check whether vehicle is used in a booking
    booking = db.execute(
        text("""
            SELECT booking_id
            FROM bookings
            WHERE vehicle_id = :vehicle_id
            LIMIT 1
        """),
        {
            "vehicle_id": vehicle_id
        }
    ).first()

    if booking:

        raise HTTPException(
            status_code=409,
            detail="Vehicle cannot be deleted because it is linked to a booking"
        )

    # Delete vehicle
    db.execute(
        text("""
            DELETE FROM vehicles
            WHERE vehicle_id = :vehicle_id
        """),
        {
            "vehicle_id": vehicle_id
        }
    )

    db.commit()

    return {
        "message": "Vehicle deleted successfully!",
        "vehicle_id": vehicle_id,
        "vehicle_number": vehicle["vehicle_number"]
    }
# =========================================================
# 14. ADD RATING
# =========================================================

@app.post("/ratings")
def add_rating(
    rating: RatingRequest,
    db: Session = Depends(get_db)
):

    # Check user
    user = db.execute(
        text("""
            SELECT user_id
            FROM users
            WHERE user_id = :user_id
        """),
        {
            "user_id": rating.user_id
        }
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # Check booking
    booking = db.execute(
        text("""
            SELECT
                booking_id,
                user_id,
                slot_id,
                booking_status
            FROM bookings
            WHERE booking_id = :booking_id
        """),
        {
            "booking_id": rating.booking_id
        }
    ).mappings().first()

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found"
        )

    # Make sure booking belongs to user
    if booking["user_id"] != rating.user_id:
        raise HTTPException(
            status_code=403,
            detail="This booking does not belong to this user"
        )

    # Get location from booking
    booking_location = db.execute(
        text("""
            SELECT location_id
            FROM parking_slots
            WHERE slot_id = :slot_id
        """),
        {
            "slot_id": booking["slot_id"]
        }
    ).scalar()

    if booking_location != rating.location_id:
        raise HTTPException(
            status_code=400,
            detail="Location does not match the booking"
        )

    # Only completed bookings can be rated
    if booking["booking_status"] != "COMPLETED":
        raise HTTPException(
            status_code=400,
            detail="Only completed bookings can be rated"
        )

    # Validate rating
    if rating.rating < 1 or rating.rating > 5:
        raise HTTPException(
            status_code=400,
            detail="Rating must be between 1 and 5"
        )

    # Check existing rating
    existing = db.execute(
        text("""
            SELECT rating_id
            FROM ratings
            WHERE booking_id = :booking_id
        """),
        {
            "booking_id": rating.booking_id
        }
    ).first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="This booking has already been rated"
        )

    # Insert rating
    result = db.execute(
        text("""
            INSERT INTO ratings
            (
                user_id,
                location_id,
                booking_id,
                rating,
                review
            )
            VALUES
            (
                :user_id,
                :location_id,
                :booking_id,
                :rating,
                :review
            )
        """),
        {
            "user_id": rating.user_id,
            "location_id": rating.location_id,
            "booking_id": rating.booking_id,
            "rating": rating.rating,
            "review": rating.review
        }
    )

    db.commit()

    return {
        "message": "Rating submitted successfully!",
        "rating_id": result.lastrowid,
        "user_id": rating.user_id,
        "location_id": rating.location_id,
        "booking_id": rating.booking_id,
        "rating": rating.rating,
        "review": rating.review
    }

# =========================================================
# 15. GET PARKING RATINGS
# =========================================================

@app.get("/parking/{location_id}/ratings")
def get_parking_ratings(
    location_id: int,
    db: Session = Depends(get_db)
):

    location = db.execute(
        text("""SELECT location_id FROM parking_locations WHERE location_id = :location_id"""),
        {"location_id": location_id}
    ).first()

    if not location:
        raise HTTPException(status_code=404, detail="Parking location not found")

    result = db.execute(
        text("""
            SELECT
                r.rating_id,
                r.user_id,
                r.booking_id,
                r.rating,
                r.review,
                r.created_at
            FROM ratings r
            WHERE r.location_id = :location_id
            ORDER BY r.created_at DESC
        """),
        {
            "location_id": location_id
        }
    )

    ratings = result.mappings().all()

    return {
        "location_id": location_id,
        "count": len(ratings),
        "ratings": ratings
    }

# =========================================================
# 16. ADD PARKING LOCATION
# =========================================================

@app.post("/parking")
def add_parking_location(
    parking: ParkingRequest,
    db: Session = Depends(get_db)
):

    # Validate required fields
    if not parking.location_name or not parking.location_name.strip():
        raise HTTPException(status_code=400, detail="Location name is required")

    if not parking.address or not parking.address.strip():
        raise HTTPException(status_code=400, detail="Address is required")

    if parking.latitude is not None and not -90 <= parking.latitude <= 90:
        raise HTTPException(status_code=400, detail="Latitude must be between -90 and 90")

    if parking.longitude is not None and not -180 <= parking.longitude <= 180:
        raise HTTPException(status_code=400, detail="Longitude must be between -180 and 180")

    # Validate capacity
    if parking.capacity <= 0:
        raise HTTPException(
            status_code=400,
            detail="Capacity must be greater than 0"
        )

    # Validate price
    if parking.base_price < 0:
        raise HTTPException(
            status_code=400,
            detail="Base price cannot be negative"
        )

    # Insert parking location
    result = db.execute(
        text("""
            INSERT INTO parking_locations
            (
                location_name,
                address,
                latitude,
                longitude,
                capacity,
                base_price,
                status
            )
            VALUES
            (
                :location_name,
                :address,
                :latitude,
                :longitude,
                :capacity,
                :base_price,
                'PENDING'
            )
        """),
        {
            "location_name": parking.location_name,
            "address": parking.address,
            "latitude": parking.latitude,
            "longitude": parking.longitude,
            "capacity": parking.capacity,
            "base_price": parking.base_price
        }
    )

    db.commit()

    return {
        "message": "Parking location added successfully!",
        "location_id": result.lastrowid,
        "location_name": parking.location_name,
        "address": parking.address,
        "capacity": parking.capacity,
        "base_price": parking.base_price,
        "status": "PENDING"
    }
# =========================================================
# 17. APPROVE PARKING LOCATION
# =========================================================

@app.patch("/parking/{location_id}/approve")
def approve_parking_location(
    location_id: int,
    db: Session = Depends(get_db)
):

    # Check parking location
    parking = db.execute(
        text("""
            SELECT
                location_id,
                location_name,
                status
            FROM parking_locations
            WHERE location_id = :location_id
        """),
        {
            "location_id": location_id
        }
    ).mappings().first()

    if not parking:
        raise HTTPException(
            status_code=404,
            detail="Parking location not found"
        )

    # Check current status
    if parking["status"] == "ACTIVE":
        raise HTTPException(
            status_code=400,
            detail="Parking location is already active"
        )

    if parking["status"] != "PENDING":
        raise HTTPException(
            status_code=400,
            detail="Only pending parking locations can be approved"
        )

    # Approve parking
    db.execute(
        text("""
            UPDATE parking_locations
            SET status = 'ACTIVE'
            WHERE location_id = :location_id
        """),
        {
            "location_id": location_id
        }
    )

    db.commit()

    return {
        "message": "Parking location approved successfully!",
        "location_id": location_id,
        "location_name": parking["location_name"],
        "status": "ACTIVE"
    }

# =========================================================
# 18. ADD PARKING SLOT
# =========================================================

@app.post("/parking/{location_id}/slots")
def add_parking_slot(
    location_id: int,
    slot: SlotRequest,
    db: Session = Depends(get_db)
):

    # Check parking location
    parking = db.execute(
        text("""
            SELECT location_id, status
            FROM parking_locations
            WHERE location_id = :location_id
        """),
        {
            "location_id": location_id
        }
    ).mappings().first()

    if not parking:
        raise HTTPException(
            status_code=404,
            detail="Parking location not found"
        )

    if parking["status"] != "ACTIVE":
        raise HTTPException(
            status_code=400,
            detail="Parking location is not active"
        )

    slot_count = db.execute(
        text("""
            SELECT COUNT(*)
            FROM parking_slots
            WHERE location_id = :location_id
        """),
        {"location_id": location_id}
    ).scalar() or 0

    capacity = db.execute(
        text("""
            SELECT capacity
            FROM parking_locations
            WHERE location_id = :location_id
        """),
        {"location_id": location_id}
    ).scalar()

    if slot_count >= capacity:
        raise HTTPException(status_code=409, detail="Parking slot capacity has been reached")

    # Clean input
    slot_number = slot.slot_number.strip().upper()
    slot_type = slot.slot_type.strip().upper()

    # Validate slot type
    allowed_types = [
        "CAR",
        "BIKE",
        "EV",
        "HANDICAPPED",
        "GENERAL"
    ]

    if slot_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Invalid slot type"
        )

    # Check duplicate slot
    existing = db.execute(
        text("""
            SELECT slot_id
            FROM parking_slots
            WHERE location_id = :location_id
              AND slot_number = :slot_number
        """),
        {
            "location_id": location_id,
            "slot_number": slot_number
        }
    ).first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Slot already exists at this parking location"
        )

    # Add slot
    result = db.execute(
        text("""
            INSERT INTO parking_slots
            (
                location_id,
                slot_number,
                slot_type,
                status
            )
            VALUES
            (
                :location_id,
                :slot_number,
                :slot_type,
                'AVAILABLE'
            )
        """),
        {
            "location_id": location_id,
            "slot_number": slot_number,
            "slot_type": slot_type
        }
    )

    db.commit()

    return {
        "message": "Parking slot added successfully!",
        "slot_id": result.lastrowid,
        "location_id": location_id,
        "slot_number": slot_number,
        "slot_type": slot_type,
        "status": "AVAILABLE"
    }
# =========================================================
# 19. UPDATE SLOT STATUS
# =========================================================

@app.patch("/parking/slots/{slot_id}/status")
def update_slot_status(
    slot_id: int,
    slot_status: SlotStatusRequest,
    db: Session = Depends(get_db)
):

    # Allowed statuses
    allowed_statuses = [
        "AVAILABLE",
        "OCCUPIED",
        "MAINTENANCE",
        "RESERVED"
    ]

    status = slot_status.status.strip().upper()

    if status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail="Invalid slot status"
        )

    # Check slot
    slot = db.execute(
        text("""
            SELECT
                slot_id,
                location_id,
                slot_number,
                status
            FROM parking_slots
            WHERE slot_id = :slot_id
        """),
        {
            "slot_id": slot_id
        }
    ).mappings().first()

    if not slot:
        raise HTTPException(
            status_code=404,
            detail="Parking slot not found"
        )

    if status in {"MAINTENANCE", "OCCUPIED"}:
        active_booking = db.execute(
            text("""
                SELECT booking_id
                FROM bookings
                WHERE slot_id = :slot_id
                  AND booking_status IN ('CONFIRMED', 'ACTIVE')
                  AND end_time > NOW()
                LIMIT 1
            """),
            {"slot_id": slot_id}
        ).first()

        if active_booking:
            raise HTTPException(
                status_code=409,
                detail="Slot has an active booking and cannot be changed to this status"
            )

    # Update status
    db.execute(
        text("""
            UPDATE parking_slots
            SET status = :status
            WHERE slot_id = :slot_id
        """),
        {
            "status": status,
            "slot_id": slot_id
        }
    )

    db.commit()

    return {
        "message": "Slot status updated successfully!",
        "slot_id": slot_id,
        "location_id": slot["location_id"],
        "slot_number": slot["slot_number"],
        "old_status": slot["status"],
        "new_status": status
    }

# =========================================================
# 20. SEARCH PARKING
# =========================================================

@app.get("/parking/search")
def search_parking(
    db: Session = Depends(get_db)
):

    result = db.execute(
        text("""
            SELECT
                pl.location_id,
                pl.location_name,
                pl.address,
                pl.latitude,
                pl.longitude,
                pl.capacity,
                pl.base_price,

                COUNT(ps.slot_id) AS total_slots,

                COALESCE(SUM(
                    CASE
                        WHEN ps.status = 'AVAILABLE'
                        THEN 1
                        ELSE 0
                    END
                ), 0) AS available_slots,

                COALESCE(SUM(
                    CASE
                        WHEN ps.status = 'OCCUPIED'
                        THEN 1
                        ELSE 0
                    END
                ), 0) AS occupied_slots

            FROM parking_locations pl

            LEFT JOIN parking_slots ps
                ON pl.location_id = ps.location_id

            WHERE pl.status = 'ACTIVE'

            GROUP BY
                pl.location_id,
                pl.location_name,
                pl.address,
                pl.latitude,
                pl.longitude,
                pl.capacity,
                pl.base_price

            ORDER BY available_slots DESC
        """)
    )

    parking = result.mappings().all()

    return {
        "count": len(parking),
        "results": parking
    }

# =========================================================
# 21. FIND NEARBY PARKING
# =========================================================

@app.get("/parking/nearby")
def nearby_parking(
    latitude: float,
    longitude: float,
    radius_km: float = 5,
    db: Session = Depends(get_db)
):

    if not -90 <= latitude <= 90:
        raise HTTPException(status_code=400, detail="Latitude must be between -90 and 90")

    if not -180 <= longitude <= 180:
        raise HTTPException(status_code=400, detail="Longitude must be between -180 and 180")

    if radius_km <= 0 or radius_km > 100:
        raise HTTPException(status_code=400, detail="Radius must be between 0 and 100 km")

    result = db.execute(
        text("""
            SELECT
                pl.location_id,
                pl.location_name,
                pl.address,
                pl.latitude,
                pl.longitude,
                pl.base_price,

                COUNT(ps.slot_id) AS total_slots,

                SUM(
                    CASE
                        WHEN ps.status = 'AVAILABLE'
                        THEN 1
                        ELSE 0
                    END
                ) AS available_slots,

                ROUND(
                    6371 * ACOS(
                        LEAST(
                            1,
                            GREATEST(
                                -1,
                                COS(RADIANS(:latitude))
                                * COS(RADIANS(pl.latitude))
                                * COS(
                                    RADIANS(pl.longitude)
                                    - RADIANS(:longitude)
                                )
                                + SIN(RADIANS(:latitude))
                                * SIN(RADIANS(pl.latitude))
                            )
                        )
                    ),
                    2
                ) AS distance_km

            FROM parking_locations pl

            LEFT JOIN parking_slots ps
                ON pl.location_id = ps.location_id

            WHERE pl.status = 'ACTIVE'

              AND pl.latitude IS NOT NULL
              AND pl.longitude IS NOT NULL

            GROUP BY
                pl.location_id,
                pl.location_name,
                pl.address,
                pl.latitude,
                pl.longitude,
                pl.base_price

            HAVING distance_km <= :radius_km

            ORDER BY distance_km ASC
        """),
        {
            "latitude": latitude,
            "longitude": longitude,
            "radius_km": radius_km
        }
    )

    parking = result.mappings().all()

    return {
        "search_location": {
            "latitude": latitude,
            "longitude": longitude
        },
        "radius_km": radius_km,
        "count": len(parking),
        "nearby_parking": parking
    }

    # =========================================================
# 22. PARKSCORE
# =========================================================

@app.get("/parking/parkscore")
def get_parkscore(
    latitude: float,
    longitude: float,
    db: Session = Depends(get_db)
):

    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise HTTPException(status_code=400, detail="Invalid latitude or longitude")

    result = db.execute(
        text("""
            SELECT
                pl.location_id,
                pl.location_name,
                pl.address,
                pl.base_price,

                COUNT(DISTINCT ps.slot_id) AS total_slots,

                COUNT(
                    DISTINCT CASE
                        WHEN ps.status = 'AVAILABLE'
                        THEN ps.slot_id
                    END
                ) AS available_slots,

                COALESCE(
                    ROUND(AVG(r.rating), 2),
                    0
                ) AS average_rating,

                ROUND(
                    6371 * ACOS(
                        LEAST(
                            1,
                            GREATEST(
                                -1,
                                COS(RADIANS(:latitude))
                                * COS(RADIANS(pl.latitude))
                                * COS(
                                    RADIANS(pl.longitude)
                                    - RADIANS(:longitude)
                                )
                                + SIN(RADIANS(:latitude))
                                * SIN(RADIANS(pl.latitude))
                            )
                        )
                    ),
                    2
                ) AS distance_km

            FROM parking_locations pl

            LEFT JOIN parking_slots ps
                ON pl.location_id = ps.location_id

            LEFT JOIN ratings r
                ON pl.location_id = r.location_id

            WHERE pl.status = 'ACTIVE'

              AND pl.latitude IS NOT NULL
              AND pl.longitude IS NOT NULL

            GROUP BY
                pl.location_id,
                pl.location_name,
                pl.address,
                pl.base_price,
                pl.latitude,
                pl.longitude

            ORDER BY distance_km ASC
        """),
        {
            "latitude": latitude,
            "longitude": longitude
        }
    )

    parking = result.mappings().all()

    if not parking:
        return {
            "count": 0,
            "results": []
        }

    # Find maximum price for normalization
    max_price = max(
        float(p["base_price"])
        for p in parking
    )

    results = []

    for p in parking:

        total_slots = int(p["total_slots"])
        available_slots = int(p["available_slots"])
        rating = float(p["average_rating"])
        price = float(p["base_price"])
        distance = float(p["distance_km"])

        # Availability score: 0-100
        if total_slots > 0:
            availability_score = (
                available_slots / total_slots
            ) * 100
        else:
            availability_score = 0

        # Rating score: 0-100
        rating_score = (
            rating / 5
        ) * 100

        # Price score: lower price gets higher score
        if max_price > 0:
            price_score = (
                1 - (price / max_price)
            ) * 100
        else:
            price_score = 0

        # Distance score
        distance_score = max(
            0,
            100 - (distance * 20)
        )

        # ParkScore
        parkscore = (
            availability_score * 0.30
            + rating_score * 0.25
            + price_score * 0.20
            + distance_score * 0.25
        )

        results.append({
            "location_id": p["location_id"],
            "location_name": p["location_name"],
            "address": p["address"],
            "distance_km": distance,
            "available_slots": available_slots,
            "total_slots": total_slots,
            "base_price": price,
            "average_rating": rating,
            "availability_score": round(
                availability_score, 2
            ),
            "rating_score": round(
                rating_score, 2
            ),
            "price_score": round(
                price_score, 2
            ),
            "distance_score": round(
                distance_score, 2
            ),
            "parkscore": round(
                parkscore, 2
            )
        })

    # Highest ParkScore first
    results.sort(
        key=lambda x: x["parkscore"],
        reverse=True
    )

    return {
        "count": len(results),
        "results": results
    }

# =========================================================
# 23. PARKING DEMAND PATTERN
# =========================================================

@app.get("/parking/{location_id}/demand-pattern")
def get_demand_pattern(
    location_id: int,
    db: Session = Depends(get_db)
):

    # Check parking location
    location = db.execute(
        text("""
            SELECT location_id, location_name
            FROM parking_locations
            WHERE location_id = :location_id
        """),
        {
            "location_id": location_id
        }
    ).mappings().first()

    if not location:
        raise HTTPException(
            status_code=404,
            detail="Parking location not found"
        )

    # Analyze occupancy by hour
    result = db.execute(
        text("""
            SELECT
                HOUR(recorded_at) AS hour,
                ROUND(
                    AVG(occupancy_percentage),
                    2
                ) AS average_occupancy,
                COUNT(*) AS records
            FROM occupancy_records
            WHERE location_id = :location_id
            GROUP BY HOUR(recorded_at)
            ORDER BY hour
        """),
        {
            "location_id": location_id
        }
    )

    patterns = result.mappings().all()

    return {
        "location_id": location_id,
        "location_name": location["location_name"],
        "count": len(patterns),
        "demand_pattern": patterns
    }
# =========================================================
# 24. ARRIVAL INSIGHT
# =========================================================

@app.get("/parking/{location_id}/arrival-insight")
def get_arrival_insight(
    location_id: int,
    arrival_time: str,
    db: Session = Depends(get_db)
):

    # Check parking location
    location = db.execute(
        text("""
            SELECT location_id, location_name
            FROM parking_locations
            WHERE location_id = :location_id
        """),
        {
            "location_id": location_id
        }
    ).mappings().first()

    if not location:
        raise HTTPException(
            status_code=404,
            detail="Parking location not found"
        )

    # Validate and extract hour from arrival time
    try:
        parsed_arrival = datetime.strptime(arrival_time, "%H:%M")
        hour = parsed_arrival.hour
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid arrival_time. Use HH:MM format."
        )

    # Find historical occupancy for that hour
    result = db.execute(
        text("""
            SELECT
                ROUND(AVG(occupancy_percentage), 2)
                AS average_occupancy,
                COUNT(*) AS records
            FROM occupancy_records
            WHERE location_id = :location_id
              AND HOUR(recorded_at) = :hour
        """),
        {
            "location_id": location_id,
            "hour": hour
        }
    ).mappings().first()

    average_occupancy = result["average_occupancy"]
    records = result["records"]

    if records == 0:
        return {
            "location_id": location_id,
            "location_name": location["location_name"],
            "arrival_time": arrival_time,
            "message": "No historical data available for this arrival time."
        }

    # Generate simple insight
    if average_occupancy >= 80:
        insight = "Parking is usually very busy around this time."
    elif average_occupancy >= 50:
        insight = "Parking usually has moderate demand around this time."
    else:
        insight = "Parking usually has lower demand around this time."

    return {
        "location_id": location_id,
        "location_name": location["location_name"],
        "arrival_time": arrival_time,
        "average_occupancy": float(average_occupancy),
        "historical_records": records,
        "insight": insight
    }
# =========================================================
# 25. PARKSPOT PICK
# =========================================================

@app.get("/parking/parkspot-pick")
def parkspot_pick(
    latitude: float,
    longitude: float,
    arrival_time: str,
    db: Session = Depends(get_db)
):

    if not -90 <= latitude <= 90:
        raise HTTPException(status_code=400, detail="Latitude must be between -90 and 90")

    if not -180 <= longitude <= 180:
        raise HTTPException(status_code=400, detail="Longitude must be between -180 and 180")

    # Validate arrival time
    try:
        time_parts = arrival_time.split(":")

        if len(time_parts) != 2:
            raise ValueError

        hour = int(time_parts[0])
        minute = int(time_parts[1])

        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
            raise ValueError

    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid arrival_time. Use HH:MM format."
        )

    # Get active parking locations
    result = db.execute(
        text("""
            SELECT
                pl.location_id,
                pl.location_name,
                pl.address,
                pl.base_price,

                COUNT(DISTINCT ps.slot_id) AS total_slots,

                COUNT(
                    DISTINCT CASE
                        WHEN ps.status = 'AVAILABLE'
                        THEN ps.slot_id
                    END
                ) AS available_slots,

                COALESCE(
                    (
                        SELECT ROUND(AVG(r.rating), 2)
                        FROM ratings r
                        WHERE r.location_id = pl.location_id
                    ),
                    0
                ) AS average_rating,

                ROUND(
                    6371 * ACOS(
                        LEAST(
                            1,
                            GREATEST(
                                -1,
                                COS(RADIANS(:latitude))
                                * COS(RADIANS(pl.latitude))
                                * COS(
                                    RADIANS(pl.longitude)
                                    - RADIANS(:longitude)
                                )
                                + SIN(RADIANS(:latitude))
                                * SIN(RADIANS(pl.latitude))
                            )
                        )
                    ),
                    2
                ) AS distance_km,

                (
                    SELECT ROUND(
                        AVG(oc.occupancy_percentage),
                        2
                    )
                    FROM occupancy_records oc
                    WHERE oc.location_id = pl.location_id
                      AND HOUR(oc.recorded_at) = :hour
                ) AS historical_occupancy

            FROM parking_locations pl

            LEFT JOIN parking_slots ps
                ON pl.location_id = ps.location_id

            WHERE pl.status = 'ACTIVE'
              AND pl.latitude IS NOT NULL
              AND pl.longitude IS NOT NULL

            GROUP BY
                pl.location_id,
                pl.location_name,
                pl.address,
                pl.base_price,
                pl.latitude,
                pl.longitude

            ORDER BY distance_km ASC
        """),
        {
            "latitude": latitude,
            "longitude": longitude,
            "hour": hour
        }
    )

    parking = result.mappings().all()

    if not parking:
        return {
            "message": "No active parking locations found.",
            "count": 0,
            "results": []
        }

    # Find maximum price
    max_price = max(
        float(p["base_price"])
        for p in parking
    )

    results = []

    for p in parking:

        total_slots = int(p["total_slots"])
        available_slots = int(p["available_slots"])
        rating = float(p["average_rating"])
        price = float(p["base_price"])
        distance = float(p["distance_km"])

        historical_occupancy = p["historical_occupancy"]

        # -----------------------------------------
        # 1. Availability Score
        # -----------------------------------------

        if total_slots > 0:
            availability_score = (
                available_slots / total_slots
            ) * 100
        else:
            availability_score = 0

        # -----------------------------------------
        # 2. Rating Score
        # -----------------------------------------

        rating_score = (
            rating / 5
        ) * 100

        # -----------------------------------------
        # 3. Price Score
        # -----------------------------------------

        if max_price > 0:
            price_score = (
                1 - (price / max_price)
            ) * 100
        else:
            price_score = 0

        # -----------------------------------------
        # 4. Distance Score
        # -----------------------------------------

        distance_score = max(
            0,
            100 - (distance * 20)
        )

        # -----------------------------------------
        # 5. Arrival / Demand Score
        # -----------------------------------------

        if historical_occupancy is not None:

            demand_score = max(
                0,
                100 - float(historical_occupancy)
            )

            if historical_occupancy >= 80:
                demand_message = "Usually very busy around your arrival time."
            elif historical_occupancy >= 50:
                demand_message = "Usually has moderate demand around your arrival time."
            else:
                demand_message = "Usually has lower demand around your arrival time."

        else:

            demand_score = 50

            demand_message = (
                "No historical data is available for your arrival time."
            )

        # -----------------------------------------
        # PARKSPOT PICK SCORE
        # -----------------------------------------

        pick_score = (
            availability_score * 0.25
            + rating_score * 0.20
            + price_score * 0.15
            + distance_score * 0.20
            + demand_score * 0.20
        )

        # -----------------------------------------
        # Generate explanation
        # -----------------------------------------

        reasons = []

        if available_slots > 0:
            reasons.append(
                f"{available_slots} parking slot(s) currently available"
            )
        else:
            reasons.append(
                "No parking slots are currently available"
            )

        if distance <= 1:
            reasons.append(
                "very close to your location"
            )
        elif distance <= 3:
            reasons.append(
                "within a short distance"
            )

        if rating >= 4:
            reasons.append(
                f"good rating of {rating}/5"
            )
        elif rating == 0:
            reasons.append(
                "no ratings available yet"
            )

        if historical_occupancy is not None:
            reasons.append(
                f"historical occupancy around arrival time is "
                f"{float(historical_occupancy):.0f}%"
            )

        results.append({
            "location_id": p["location_id"],
            "location_name": p["location_name"],
            "address": p["address"],
            "distance_km": distance,
            "available_slots": available_slots,
            "total_slots": total_slots,
            "base_price": price,
            "average_rating": rating,
            "historical_occupancy": (
                float(historical_occupancy)
                if historical_occupancy is not None
                else None
            ),
            "demand_message": demand_message,
            "pick_score": round(pick_score, 2),
            "reasons": reasons
        })

    # Highest Pick Score first
    results.sort(
        key=lambda x: x["pick_score"],
        reverse=True
    )

    # First result = ParkSpot Pick
    best_pick = results[0]

    return {
        "message": "ParkSpot Pick generated successfully!",
        "search_location": {
            "latitude": latitude,
            "longitude": longitude
        },
        "arrival_time": f"{hour:02d}:{minute:02d}",
        "parkspot_pick": best_pick,
        "other_options": results[1:],
        "count": len(results)
    }
# =========================================================
# 26. ADD PRICING RULE
# =========================================================

@app.post("/pricing-rules")
def add_pricing_rule(
    request: PricingRuleRequest,
    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    # 1. Check parking location
    # -----------------------------------------------------

    location = db.execute(
        text("""
            SELECT location_id
            FROM parking_locations
            WHERE location_id = :location_id
        """),
        {
            "location_id": request.location_id
        }
    ).mappings().first()

    if not location:
        raise HTTPException(
            status_code=404,
            detail="Parking location not found"
        )

    # -----------------------------------------------------
    # 2. Validate day
    # -----------------------------------------------------

    valid_days = [
        "MONDAY",
        "TUESDAY",
        "WEDNESDAY",
        "THURSDAY",
        "FRIDAY",
        "SATURDAY",
        "SUNDAY"
    ]

    day = request.day_of_week.strip().upper()

    if day not in valid_days:
        raise HTTPException(
            status_code=400,
            detail="Invalid day_of_week"
        )

    # -----------------------------------------------------
    # 3. Validate price
    # -----------------------------------------------------

    if request.price_per_hour < 0:
        raise HTTPException(
            status_code=400,
            detail="Price cannot be negative"
        )

    # -----------------------------------------------------
    # 4. Validate time format
    # -----------------------------------------------------

    try:
        start = datetime.strptime(
            request.start_time,
            "%H:%M"
        ).time()

        end = datetime.strptime(
            request.end_time,
            "%H:%M"
        ).time()

    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid time format. Use HH:MM."
        )

    # -----------------------------------------------------
    # 5. Check time order
    # -----------------------------------------------------

    if end <= start:
        raise HTTPException(
            status_code=400,
            detail="End time must be after start time"
        )

    # -----------------------------------------------------
    # 6. Check overlapping pricing rules
    #
    # Example:
    # Existing: 09:00 - 17:00
    #
    # New:      17:00 - 20:00
    # Result:   ALLOWED
    #
    # Existing: 09:00 - 17:00
    #
    # New:      16:00 - 20:00
    # Result:   CONFLICT
    # -----------------------------------------------------

    conflict = db.execute(
        text("""
            SELECT
                pricing_rule_id,
                start_time,
                end_time
            FROM pricing_rules
            WHERE location_id = :location_id
              AND day_of_week = :day
              AND start_time < :end_time
              AND end_time > :start_time
            LIMIT 1
        """),
        {
            "location_id": request.location_id,
            "day": day,
            "start_time": start,
            "end_time": end
        }
    ).mappings().first()

    if conflict:
        raise HTTPException(
            status_code=409,
            detail=(
                "Pricing rule overlaps with an existing rule "
                f"({conflict['start_time']} - {conflict['end_time']})."
            )
        )

    # -----------------------------------------------------
    # 7. Insert pricing rule
    # -----------------------------------------------------

    result = db.execute(
        text("""
            INSERT INTO pricing_rules
            (
                location_id,
                day_of_week,
                start_time,
                end_time,
                price_per_hour
            )
            VALUES
            (
                :location_id,
                :day_of_week,
                :start_time,
                :end_time,
                :price_per_hour
            )
        """),
        {
            "location_id": request.location_id,
            "day_of_week": day,
            "start_time": start,
            "end_time": end,
            "price_per_hour": request.price_per_hour
        }
    )

    db.commit()

    # -----------------------------------------------------
    # 8. Return success response
    # -----------------------------------------------------

    return {
        "message": "Pricing rule added successfully!",
        "pricing_rule_id": result.lastrowid,
        "location_id": request.location_id,
        "day_of_week": day,
        "start_time": request.start_time,
        "end_time": request.end_time,
        "price_per_hour": request.price_per_hour
    }
# =========================================================
# 27. VIEW PRICING RULES
# =========================================================

@app.get("/pricing-rules/{location_id}")
def get_pricing_rules(
    location_id: int,
    db: Session = Depends(get_db)
):

    # Check parking location
    location = db.execute(
        text("""
            SELECT location_id, location_name
            FROM parking_locations
            WHERE location_id = :location_id
        """),
        {
            "location_id": location_id
        }
    ).mappings().first()

    if not location:
        raise HTTPException(
            status_code=404,
            detail="Parking location not found"
        )

    # Get pricing rules
    result = db.execute(
        text("""
            SELECT
                pricing_rule_id,
                day_of_week,
                start_time,
                end_time,
                price_per_hour
            FROM pricing_rules
            WHERE location_id = :location_id
            ORDER BY
                FIELD(
                    day_of_week,
                    'MONDAY',
                    'TUESDAY',
                    'WEDNESDAY',
                    'THURSDAY',
                    'FRIDAY',
                    'SATURDAY',
                    'SUNDAY'
                ),
                start_time
        """),
        {
            "location_id": location_id
        }
    )

    rules = result.mappings().all()

    return {
        "location_id": location["location_id"],
        "location_name": location["location_name"],
        "count": len(rules),
        "pricing_rules": [
            {
                "pricing_rule_id": r["pricing_rule_id"],
                "day_of_week": r["day_of_week"],
                "start_time": str(r["start_time"]),
                "end_time": str(r["end_time"]),
                "price_per_hour": float(r["price_per_hour"])
            }
            for r in rules
        ]
    }
# =========================================================
# 28. DELETE PRICING RULE
# =========================================================

@app.delete("/pricing-rules/{pricing_rule_id}")
def delete_pricing_rule(
    pricing_rule_id: int,
    db: Session = Depends(get_db)
):

    rule = db.execute(
        text("""
            SELECT
                pricing_rule_id,
                location_id,
                day_of_week,
                start_time,
                end_time,
                price_per_hour
            FROM pricing_rules
            WHERE pricing_rule_id = :pricing_rule_id
        """),
        {
            "pricing_rule_id": pricing_rule_id
        }
    ).mappings().first()

    if not rule:
        raise HTTPException(
            status_code=404,
            detail="Pricing rule not found"
        )

    db.execute(
        text("""
            DELETE FROM pricing_rules
            WHERE pricing_rule_id = :pricing_rule_id
        """),
        {
            "pricing_rule_id": pricing_rule_id
        }
    )

    db.commit()

    return {
        "message": "Pricing rule deleted successfully!",
        "pricing_rule_id": pricing_rule_id
    }

# =========================================================
# 29. MANAGER - VIEW ASSIGNED PARKING LOCATION
# =========================================================

@app.get("/manager/{user_id}/parking")
def manager_parking(
    user_id: int,
    db: Session = Depends(get_db)
):

    result = db.execute(
        text("""
            SELECT
                pm.manager_id,
                u.user_id,
                u.name AS manager_name,
                u.email AS manager_email,
                pl.location_id,
                pl.location_name,
                pl.address,
                pl.latitude,
                pl.longitude,
                pl.capacity,
                pl.base_price,
                pl.status
            FROM parking_managers pm
            JOIN users u
                ON pm.user_id = u.user_id
            JOIN parking_locations pl
                ON pm.location_id = pl.location_id
            WHERE pm.user_id = :user_id
        """),
        {
            "user_id": user_id
        }
    ).mappings().first()

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Manager or assigned parking location not found"
        )

    return {
        "manager": {
            "manager_id": result["manager_id"],
            "user_id": result["user_id"],
            "name": result["manager_name"],
            "email": result["manager_email"]
        },
        "parking_location": {
            "location_id": result["location_id"],
            "location_name": result["location_name"],
            "address": result["address"],
            "latitude": result["latitude"],
            "longitude": result["longitude"],
            "capacity": result["capacity"],
            "base_price": result["base_price"],
            "status": result["status"]
        }
    }
# =========================================================
# 30. MANAGER - VIEW PARKING SLOTS
# =========================================================

@app.get("/manager/{user_id}/parking/slots")
def manager_parking_slots(
    user_id: int,
    db: Session = Depends(get_db)
):

    result = db.execute(
        text("""
            SELECT
                pm.manager_id,
                pl.location_id,
                pl.location_name
            FROM parking_managers pm
            JOIN parking_locations pl
                ON pm.location_id = pl.location_id
            WHERE pm.user_id = :user_id
        """),
        {
            "user_id": user_id
        }
    ).mappings().first()

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Manager or assigned parking location not found"
        )

    slots = db.execute(
        text("""
            SELECT
                slot_id,
                slot_number,
                slot_type,
                status
            FROM parking_slots
            WHERE location_id = :location_id
            ORDER BY slot_id
        """),
        {
            "location_id": result["location_id"]
        }
    ).mappings().all()

    return {
        "manager_id": result["manager_id"],
        "location_id": result["location_id"],
        "location_name": result["location_name"],
        "total_slots": len(slots),
        "slots": [dict(slot) for slot in slots]
    }
# =========================================================
# 31. MANAGER - UPDATE PARKING SLOT STATUS
# =========================================================

@app.patch("/manager/{user_id}/parking/slots/{slot_id}/status")
def manager_update_slot_status(
    user_id: int,
    slot_id: int,
    request: SlotStatusRequest,
    db: Session = Depends(get_db)
):

    # Check manager and assigned parking location
    manager = db.execute(
        text("""
            SELECT
                pm.manager_id,
                pm.location_id
            FROM parking_managers pm
            WHERE pm.user_id = :user_id
        """),
        {
            "user_id": user_id
        }
    ).mappings().first()

    if not manager:
        raise HTTPException(
            status_code=404,
            detail="Manager or assigned parking location not found"
        )

    # Validate status
    status = request.status.strip().upper()

    allowed_statuses = {
        "AVAILABLE",
        "OCCUPIED",
        "MAINTENANCE",
        "RESERVED"
    }

    if status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail="Invalid slot status"
        )

    # Check slot belongs to manager's parking
    slot = db.execute(
        text("""
            SELECT
                slot_id,
                slot_number,
                slot_type,
                status,
                location_id
            FROM parking_slots
            WHERE slot_id = :slot_id
              AND location_id = :location_id
        """),
        {
            "slot_id": slot_id,
            "location_id": manager["location_id"]
        }
    ).mappings().first()

    if not slot:
        raise HTTPException(
            status_code=404,
            detail="Parking slot not found in manager's assigned parking"
        )

    # Update status
    db.execute(
        text("""
            UPDATE parking_slots
            SET status = :status
            WHERE slot_id = :slot_id
        """),
        {
            "status": status,
            "slot_id": slot_id
        }
    )

    db.commit()

    return {
        "message": "Parking slot status updated successfully!",
        "slot_id": slot["slot_id"],
        "slot_number": slot["slot_number"],
        "old_status": slot["status"],
        "new_status": status
    }

# =========================================================
# 32. MANAGER - VIEW BOOKINGS
# =========================================================

@app.get("/manager/{user_id}/bookings")
def manager_bookings(
    user_id: int,
    db: Session = Depends(get_db)
):

    # Check manager and assigned parking
    manager = db.execute(
        text("""
            SELECT
                pm.manager_id,
                pm.location_id,
                pl.location_name
            FROM parking_managers pm
            JOIN parking_locations pl
                ON pm.location_id = pl.location_id
            WHERE pm.user_id = :user_id
        """),
        {
            "user_id": user_id
        }
    ).mappings().first()

    if not manager:
        raise HTTPException(
            status_code=404,
            detail="Manager or assigned parking location not found"
        )

    # Get bookings for manager's parking
    bookings = db.execute(
        text("""
            SELECT
                b.booking_id,
                u.user_id,
                u.name AS user_name,
                v.vehicle_number,
                v.vehicle_type,
                ps.slot_number,
                b.start_time,
                b.end_time,
                b.booking_status,
                b.total_amount,
                b.created_at
            FROM bookings b
            JOIN users u
                ON b.user_id = u.user_id
            JOIN vehicles v
                ON b.vehicle_id = v.vehicle_id
            JOIN parking_slots ps
                ON b.slot_id = ps.slot_id
            WHERE ps.location_id = :location_id
            ORDER BY b.start_time DESC
        """),
        {
            "location_id": manager["location_id"]
        }
    ).mappings().all()

    return {
        "manager_id": manager["manager_id"],
        "location_id": manager["location_id"],
        "location_name": manager["location_name"],
        "total_bookings": len(bookings),
        "bookings": [dict(booking) for booking in bookings]
    }
# =========================================================
# 33. MANAGER - VIEW OCCUPANCY
# =========================================================

@app.get("/manager/{user_id}/occupancy")
def manager_occupancy(
    user_id: int,
    db: Session = Depends(get_db)
):

    # Check manager and assigned parking
    manager = db.execute(
        text("""
            SELECT
                pm.manager_id,
                pm.location_id,
                pl.location_name
            FROM parking_managers pm
            JOIN parking_locations pl
                ON pm.location_id = pl.location_id
            WHERE pm.user_id = :user_id
        """),
        {
            "user_id": user_id
        }
    ).mappings().first()

    if not manager:
        raise HTTPException(
            status_code=404,
            detail="Manager or assigned parking location not found"
        )

    # Get current slot occupancy
    occupancy = db.execute(
        text("""
            SELECT
                COUNT(*) AS total_slots,
                SUM(
                    CASE
                        WHEN status = 'AVAILABLE'
                        THEN 1 ELSE 0
                    END
                ) AS available_slots,
                SUM(
                    CASE
                        WHEN status = 'OCCUPIED'
                        THEN 1 ELSE 0
                    END
                ) AS occupied_slots
            FROM parking_slots
            WHERE location_id = :location_id
        """),
        {
            "location_id": manager["location_id"]
        }
    ).mappings().first()

    total_slots = occupancy["total_slots"] or 0
    available_slots = occupancy["available_slots"] or 0
    occupied_slots = occupancy["occupied_slots"] or 0

    if total_slots > 0:
        occupancy_percentage = round(
            (occupied_slots / total_slots) * 100,
            2
        )
    else:
        occupancy_percentage = 0

    return {
        "manager_id": manager["manager_id"],
        "location_id": manager["location_id"],
        "location_name": manager["location_name"],
        "total_slots": total_slots,
        "available_slots": available_slots,
        "occupied_slots": occupied_slots,
        "occupancy_percentage": occupancy_percentage
    }
# =========================================================
# 34. MANAGER - VIEW REVENUE
# =========================================================

@app.get("/manager/{user_id}/revenue")
def manager_revenue(
    user_id: int,
    db: Session = Depends(get_db)
):

    # Check manager and assigned parking
    manager = db.execute(
        text("""
            SELECT
                pm.manager_id,
                pm.location_id,
                pl.location_name
            FROM parking_managers pm
            JOIN parking_locations pl
                ON pm.location_id = pl.location_id
            WHERE pm.user_id = :user_id
        """),
        {
            "user_id": user_id
        }
    ).mappings().first()

    if not manager:
        raise HTTPException(
            status_code=404,
            detail="Manager or assigned parking location not found"
        )

    # Calculate revenue from successful payments
    revenue = db.execute(
        text("""
            SELECT
                COUNT(DISTINCT p.payment_id) AS successful_payments,
                COALESCE(SUM(p.amount), 0) AS total_revenue
            FROM payments p
            JOIN bookings b
                ON p.booking_id = b.booking_id
            JOIN parking_slots ps
                ON b.slot_id = ps.slot_id
            WHERE ps.location_id = :location_id
              AND p.payment_status = 'SUCCESS'
        """),
        {
            "location_id": manager["location_id"]
        }
    ).mappings().first()

    return {
        "manager_id": manager["manager_id"],
        "location_id": manager["location_id"],
        "location_name": manager["location_name"],
        "successful_payments": revenue["successful_payments"],
        "total_revenue": float(revenue["total_revenue"])
    }
# =========================================================
# 35. MANAGER - UPDATE BOOKING STATUS
# =========================================================

@app.patch("/manager/{user_id}/bookings/{booking_id}/status")
def manager_update_booking_status(
    user_id: int,
    booking_id: int,
    request: BookingStatusRequest,
    db: Session = Depends(get_db)
):

    # Check manager and assigned parking
    manager = db.execute(
        text("""
            SELECT
                pm.manager_id,
                pm.location_id
            FROM parking_managers pm
            WHERE pm.user_id = :user_id
        """),
        {
            "user_id": user_id
        }
    ).mappings().first()

    if not manager:
        raise HTTPException(
            status_code=404,
            detail="Manager or assigned parking location not found"
        )

    # Check booking belongs to manager's parking
    booking = db.execute(
        text("""
            SELECT
                b.booking_id,
                b.booking_status,
                b.slot_id,
                ps.location_id
            FROM bookings b
            JOIN parking_slots ps
                ON b.slot_id = ps.slot_id
            WHERE b.booking_id = :booking_id
              AND ps.location_id = :location_id
        """),
        {
            "booking_id": booking_id,
            "location_id": manager["location_id"]
        }
    ).mappings().first()

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found in manager's assigned parking"
        )

    status = request.status.strip().upper()

    allowed_statuses = {
        "CONFIRMED",
        "ACTIVE",
        "COMPLETED",
        "CANCELLED"
    }

    if status not in allowed_statuses:
        raise HTTPException(status_code=400, detail="Invalid booking status")

    current_status = booking["booking_status"]

    valid_transitions = {
        "CONFIRMED": {"ACTIVE", "CANCELLED"},
        "ACTIVE": {"COMPLETED", "CANCELLED"},
        "COMPLETED": set(),
        "CANCELLED": set()
    }

    if status == current_status:
        raise HTTPException(status_code=400, detail="Booking is already in this status")

    if status not in valid_transitions.get(current_status, set()):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid booking status transition: {current_status} to {status}"
        )

    # Update booking status
    db.execute(
        text("""
            UPDATE bookings
            SET booking_status = :status
            WHERE booking_id = :booking_id
        """),
        {
            "status": status,
            "booking_id": booking_id
        }
    )

    refund_status = "NO_REFUND"

    if status == "CANCELLED":
        payment = db.execute(
            text("""
                SELECT payment_id, payment_status
                FROM payments
                WHERE booking_id = :booking_id
            """),
            {"booking_id": booking_id}
        ).mappings().first()

        if payment and payment["payment_status"] == "SUCCESS":
            db.execute(
                text("""
                    UPDATE payments
                    SET payment_status = 'REFUNDED'
                    WHERE payment_id = :payment_id
                """),
                {"payment_id": payment["payment_id"]}
            )
            refund_status = "REFUNDED"
        elif payment and payment["payment_status"] == "REFUNDED":
            refund_status = "ALREADY_REFUNDED"
        elif payment:
            refund_status = payment["payment_status"]
        else:
            refund_status = "NO_PAYMENT"

    db.commit()

    return {
        "message": "Booking status updated successfully!",
        "booking_id": booking_id,
        "old_status": booking["booking_status"],
        "new_status": status,
        "payment_status": refund_status
    }




# =========================================================
# 30. COMPLAINTS API
# =========================================================

@app.post("/complaints")
def create_complaint(
    payload: ComplaintCreateRequest,
    db: Session = Depends(get_db)
):
    user = db.execute(
        text("SELECT user_id, name FROM users WHERE user_id = :user_id"),
        {"user_id": payload.user_id}
    ).mappings().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.booking_id:
        booking = db.execute(
            text("SELECT booking_id FROM bookings WHERE booking_id = :b_id"),
            {"b_id": payload.booking_id}
        ).mappings().first()
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")

    res = db.execute(
        text("""
            INSERT INTO complaints (user_id, booking_id, subject, description, status, created_at)
            VALUES (:user_id, :booking_id, :subject, :description, 'OPEN', :created_at)
        """),
        {
            "user_id": payload.user_id,
            "booking_id": payload.booking_id,
            "subject": payload.subject,
            "description": payload.description,
            "created_at": datetime.now(timezone.utc)
        }
    )
    db.commit()
    complaint_id = res.lastrowid

    create_notification(
        db,
        payload.user_id,
        "Complaint Submitted",
        f"Your complaint #{complaint_id} has been received. Our team will review it shortly."
    )

    return {
        "message": "Complaint submitted successfully!",
        "complaint_id": complaint_id,
        "status": "OPEN"
    }


@app.get("/complaints")
def list_complaints(
    status: str | None = None,
    db: Session = Depends(get_db)
):
    query = """
        SELECT
            c.complaint_id,
            c.user_id,
            u.name AS user_name,
            u.email AS user_email,
            c.booking_id,
            c.subject,
            c.description,
            c.status,
            c.created_at,
            c.resolved_at
        FROM complaints c
        JOIN users u ON c.user_id = u.user_id
    """
    params = {}
    if status:
        query += " WHERE c.status = :status"
        params["status"] = status
    query += " ORDER BY c.created_at DESC"

    complaints = db.execute(text(query), params).mappings().all()
    return {
        "count": len(complaints),
        "complaints": complaints
    }


@app.get("/users/{user_id}/complaints")
def get_user_complaints(
    user_id: int,
    db: Session = Depends(get_db)
):
    complaints = db.execute(
        text("""
            SELECT
                complaint_id,
                booking_id,
                subject,
                description,
                status,
                created_at,
                resolved_at
            FROM complaints
            WHERE user_id = :user_id
            ORDER BY created_at DESC
        """),
        {"user_id": user_id}
    ).mappings().all()

    return {
        "user_id": user_id,
        "count": len(complaints),
        "complaints": complaints
    }


@app.patch("/complaints/{complaint_id}/status")
def update_complaint_status(
    complaint_id: int,
    payload: ComplaintStatusUpdateRequest,
    db: Session = Depends(get_db)
):
    valid_statuses = ["OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"]
    status_upper = payload.status.upper()
    if status_upper not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of {valid_statuses}")

    complaint = db.execute(
        text("SELECT complaint_id, user_id, status FROM complaints WHERE complaint_id = :c_id"),
        {"c_id": complaint_id}
    ).mappings().first()

    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    resolved_at = datetime.now(timezone.utc) if status_upper in ["RESOLVED", "CLOSED"] else None

    db.execute(
        text("""
            UPDATE complaints
            SET status = :status,
                resolved_at = :resolved_at
            WHERE complaint_id = :c_id
        """),
        {
            "status": status_upper,
            "resolved_at": resolved_at,
            "c_id": complaint_id
        }
    )
    db.commit()

    create_notification(
        db,
        complaint["user_id"],
        f"Complaint #{complaint_id} Updated",
        f"Your complaint status is now {status_upper}."
    )

    return {
        "message": f"Complaint status updated to {status_upper}",
        "complaint_id": complaint_id,
        "old_status": complaint["status"],
        "new_status": status_upper
    }


# =========================================================
# 31. NOTIFICATIONS API
# =========================================================

@app.get("/users/{user_id}/notifications")
def get_user_notifications(
    user_id: int,
    db: Session = Depends(get_db)
):
    notifications = db.execute(
        text("""
            SELECT
                notification_id,
                title,
                message,
                is_read,
                created_at
            FROM notifications
            WHERE user_id = :user_id
            ORDER BY created_at DESC
        """),
        {"user_id": user_id}
    ).mappings().all()

    unread_count = sum(1 for n in notifications if not n["is_read"])

    return {
        "user_id": user_id,
        "total_count": len(notifications),
        "unread_count": unread_count,
        "notifications": notifications
    }


@app.patch("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db)
):
    notif = db.execute(
        text("SELECT notification_id FROM notifications WHERE notification_id = :n_id"),
        {"n_id": notification_id}
    ).first()

    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    db.execute(
        text("UPDATE notifications SET is_read = TRUE WHERE notification_id = :n_id"),
        {"n_id": notification_id}
    )
    db.commit()

    return {"message": "Notification marked as read", "notification_id": notification_id}


@app.patch("/users/{user_id}/notifications/read-all")
def mark_all_notifications_read(
    user_id: int,
    db: Session = Depends(get_db)
):
    db.execute(
        text("UPDATE notifications SET is_read = TRUE WHERE user_id = :user_id"),
        {"user_id": user_id}
    )
    db.commit()

    return {"message": "All notifications marked as read", "user_id": user_id}


# =========================================================
# 32. ADMIN MANAGEMENT API
# =========================================================

@app.get("/admin/users")
def admin_list_users(
    db: Session = Depends(get_db)
):
    users = db.execute(
        text("""
            SELECT
                u.user_id,
                u.name,
                u.email,
                u.phone,
                u.account_status,
                u.role_id,
                r.role_name,
                u.created_at,
                COUNT(DISTINCT v.vehicle_id) AS total_vehicles,
                COUNT(DISTINCT b.booking_id) AS total_bookings
            FROM users u
            JOIN roles r ON u.role_id = r.role_id
            LEFT JOIN vehicles v ON u.user_id = v.user_id
            LEFT JOIN bookings b ON u.user_id = b.user_id
            GROUP BY u.user_id, r.role_name
            ORDER BY u.user_id ASC
        """)
    ).mappings().all()

    return {
        "count": len(users),
        "users": users
    }


@app.patch("/admin/users/{user_id}/status")
def admin_update_user_status(
    user_id: int,
    payload: AdminUserStatusRequest,
    db: Session = Depends(get_db)
):
    valid = ["ACTIVE", "INACTIVE", "BLOCKED"]
    status_upper = payload.account_status.upper()
    if status_upper not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of {valid}")

    user = db.execute(
        text("SELECT user_id, account_status FROM users WHERE user_id = :uid"),
        {"uid": user_id}
    ).mappings().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.execute(
        text("UPDATE users SET account_status = :status WHERE user_id = :uid"),
        {"status": status_upper, "uid": user_id}
    )
    db.commit()

    return {
        "message": f"User status updated to {status_upper}",
        "user_id": user_id,
        "old_status": user["account_status"],
        "new_status": status_upper
    }


@app.post("/admin/managers")
def admin_assign_manager(
    payload: AdminAssignManagerRequest,
    db: Session = Depends(get_db)
):
    user = db.execute(
        text("SELECT user_id, name, role_id FROM users WHERE user_id = :uid"),
        {"uid": payload.user_id}
    ).mappings().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    location = db.execute(
        text("SELECT location_id, location_name FROM parking_locations WHERE location_id = :lid"),
        {"lid": payload.location_id}
    ).mappings().first()

    if not location:
        raise HTTPException(status_code=404, detail="Parking location not found")

    # Update role to MANAGER (role_id 2) if not already
    if user["role_id"] != 2:
        db.execute(
            text("UPDATE users SET role_id = 2 WHERE user_id = :uid"),
            {"uid": payload.user_id}
        )

    # Check if already assigned
    existing_mgr = db.execute(
        text("SELECT manager_id FROM parking_managers WHERE user_id = :uid"),
        {"uid": payload.user_id}
    ).mappings().first()

    if existing_mgr:
        db.execute(
            text("UPDATE parking_managers SET location_id = :lid WHERE user_id = :uid"),
            {"lid": payload.location_id, "uid": payload.user_id}
        )
    else:
        db.execute(
            text("""
                INSERT INTO parking_managers (user_id, location_id, assigned_at)
                VALUES (:uid, :lid, :assigned_at)
            """),
            {"uid": payload.user_id, "lid": payload.location_id, "assigned_at": datetime.now(timezone.utc)}
        )

    db.commit()

    create_notification(
        db,
        payload.user_id,
        "Manager Assignment",
        f"You have been assigned as Manager for {location['location_name']}."
    )

    return {
        "message": f"User {user['name']} assigned as manager for {location['location_name']}",
        "user_id": payload.user_id,
        "location_id": payload.location_id
    }


@app.get("/admin/platform-revenue")
def admin_platform_revenue(
    db: Session = Depends(get_db)
):
    total_revenue = db.execute(
        text("SELECT COALESCE(SUM(amount), 0.00) FROM payments WHERE payment_status = 'SUCCESS'")
    ).scalar()

    total_users = db.execute(text("SELECT COUNT(*) FROM users")).scalar()
    total_locations = db.execute(text("SELECT COUNT(*) FROM parking_locations WHERE status = 'ACTIVE'")).scalar()
    total_slots = db.execute(text("SELECT COUNT(*) FROM parking_slots")).scalar()
    total_bookings = db.execute(text("SELECT COUNT(*) FROM bookings")).scalar()

    location_breakdown = db.execute(
        text("""
            SELECT
                pl.location_id,
                pl.location_name,
                COUNT(DISTINCT b.booking_id) AS bookings_count,
                COALESCE(SUM(p.amount), 0.00) AS revenue
            FROM parking_locations pl
            JOIN parking_slots ps ON pl.location_id = ps.location_id
            JOIN bookings b ON ps.slot_id = b.slot_id
            LEFT JOIN payments p ON b.booking_id = p.booking_id AND p.payment_status = 'SUCCESS'
            GROUP BY pl.location_id, pl.location_name
            ORDER BY revenue DESC
        """)
    ).mappings().all()

    return {
        "platform_metrics": {
            "total_revenue": total_revenue,
            "total_users": total_users,
            "active_locations": total_locations,
            "total_slots": total_slots,
            "total_bookings": total_bookings
        },
        "location_breakdown": location_breakdown
    }


# =========================================================
# 33. QR CODE ENTRY & EXIT PASS SYSTEM
# =========================================================

@app.get("/bookings/{booking_id}/qr-pass")
def get_booking_qr_pass(
    booking_id: int,
    db: Session = Depends(get_db)
):
    booking = db.execute(
        text("""
            SELECT
                b.booking_id,
                b.user_id,
                u.name AS user_name,
                u.email AS user_email,
                u.phone AS user_phone,
                v.vehicle_number,
                v.vehicle_type,
                ps.slot_number,
                ps.slot_type,
                pl.location_id,
                pl.location_name,
                pl.address,
                b.start_time,
                b.end_time,
                b.booking_status,
                b.total_amount
            FROM bookings b
            JOIN users u ON b.user_id = u.user_id
            JOIN vehicles v ON b.vehicle_id = v.vehicle_id
            JOIN parking_slots ps ON b.slot_id = ps.slot_id
            JOIN parking_locations pl ON ps.location_id = pl.location_id
            WHERE b.booking_id = :b_id
        """),
        {"b_id": booking_id}
    ).mappings().first()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    # Generate QR Code with verifiable payload
    qr_data = {
        "pass_type": "PARKSPOT_DIGITAL_TICKET",
        "booking_id": booking["booking_id"],
        "user_id": booking["user_id"],
        "vehicle_number": booking["vehicle_number"],
        "slot_number": booking["slot_number"],
        "location_id": booking["location_id"],
        "start_time": booking["start_time"],
        "end_time": booking["end_time"],
        "status": booking["booking_status"]
    }

    qr_image_base64 = generate_qr_code_base64(qr_data)

    return {
        "booking": booking,
        "qr_code_base64": qr_image_base64
    }


@app.post("/manager/scan-qr")
def scan_qr_gate_pass(
    payload: ScanQRRequest,
    db: Session = Depends(get_db)
):
    booking = db.execute(
        text("""
            SELECT
                b.booking_id,
                b.user_id,
                b.slot_id,
                b.booking_status,
                ps.slot_number,
                pl.location_name,
                u.name AS user_name
            FROM bookings b
            JOIN parking_slots ps ON b.slot_id = ps.slot_id
            JOIN parking_locations pl ON ps.location_id = pl.location_id
            JOIN users u ON b.user_id = u.user_id
            WHERE b.booking_id = :b_id
        """),
        {"b_id": payload.booking_id}
    ).mappings().first()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found for scanned QR code")

    current_status = booking["booking_status"]
    action = payload.action.upper()

    # Determine Check-in vs Check-out
    if action == "CHECK_IN" or (action == "AUTO" and current_status == "CONFIRMED"):
        if current_status not in ["CONFIRMED", "PENDING"]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot check-in booking in '{current_status}' status"
            )

        # Transition to ACTIVE, mark slot OCCUPIED
        db.execute(
            text("UPDATE bookings SET booking_status = 'ACTIVE' WHERE booking_id = :b_id"),
            {"b_id": payload.booking_id}
        )
        db.execute(
            text("UPDATE parking_slots SET status = 'OCCUPIED' WHERE slot_id = :s_id"),
            {"s_id": booking["slot_id"]}
        )
        db.commit()

        create_notification(
            db,
            booking["user_id"],
            "Gate Check-In Verified 🚗",
            f"Welcome to {booking['location_name']}! You have checked in to Slot {booking['slot_number']}."
        )

        return {
            "status": "CHECKED_IN",
            "message": f"Check-in verified for {booking['user_name']}. Gate opened!",
            "booking_id": payload.booking_id,
            "slot_number": booking["slot_number"],
            "location_name": booking["location_name"]
        }

    elif action == "CHECK_OUT" or (action == "AUTO" and current_status == "ACTIVE"):
        if current_status != "ACTIVE":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot check-out booking in '{current_status}' status"
            )

        # Transition to COMPLETED, mark slot AVAILABLE
        db.execute(
            text("UPDATE bookings SET booking_status = 'COMPLETED' WHERE booking_id = :b_id"),
            {"b_id": payload.booking_id}
        )
        db.execute(
            text("UPDATE parking_slots SET status = 'AVAILABLE' WHERE slot_id = :s_id"),
            {"s_id": booking["slot_id"]}
        )
        db.commit()

        create_notification(
            db,
            booking["user_id"],
            "Gate Check-Out Verified 👋",
            f"Thank you for parking at {booking['location_name']}. Slot {booking['slot_number']} has been checked out."
        )

        return {
            "status": "CHECKED_OUT",
            "message": f"Check-out complete for {booking['user_name']}. Gate opened! Slot {booking['slot_number']} is now free.",
            "booking_id": payload.booking_id,
            "slot_number": booking["slot_number"],
            "location_name": booking["location_name"]
        }

    elif current_status == "COMPLETED":
        raise HTTPException(status_code=400, detail="This booking ticket has already been completed.")
    elif current_status == "CANCELLED":
        raise HTTPException(status_code=400, detail="This booking ticket was cancelled.")
    else:
        raise HTTPException(status_code=400, detail=f"Unexpected booking status: {current_status}")


# =========================================================
# 34. AUTOMATIC EXPIRED SLOT RELEASE
# =========================================================

@app.post("/system/auto-release-slots")
def trigger_auto_release_slots(
    db: Session = Depends(get_db)
):
    released = release_expired_bookings(db)
    return {
        "message": f"Automatic slot cleanup finished. Released {released} expired slot(s).",
        "released_count": released
    }


# =========================================================
# 35. FRONTEND WEB INTERFACE MOUNT
# =========================================================
FRONTEND_DIR = BASE_DIR.parent / "frontend"

@app.get("/app", include_in_schema=False)
def serve_frontend_app():
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return HTMLResponse("<h1>ParkSpot Frontend is building...</h1>")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True, app_dir=str(BASE_DIR))
