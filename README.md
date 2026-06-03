# Sacco Bridge - Backend API

## Contributors
- Gitau William

---

## Cooperative Liquidity & Chama Digitization Platform

Sacco Bridge is a comprehensive backend API that digitizes informal savings groups (Chamas) and creates a secondary market for SACCO (Savings and Credit Co-operative) shares. The platform enables SACCO members to access liquidity by connecting with verified buyers, while providing complete chama management tools including contribution tracking, loan management, and meeting coordination.

---

## Problem Statement

Kenya's cooperative sector faces critical liquidity challenges:

- **Trillions of shillings locked** in SACCO shares with no secondary market
- **Months of friction** to exit a SACCO or liquidate group equity
- **Predatory mobile lending** as the only quick alternative for emergency cash
- **Manual chama management** using Excel sheets and paper ledgers
- **No credit history** for millions of disciplined savers in informal groups
- **Lack of transparency** in group finances leading to disputes

---

## Solution Overview

Sacco Bridge provides a dual-mode platform serving both informal and formal cooperative finance:

| Feature | Description |
|---------|-------------|
| **Chama Digitization** | Replace Excel sheets with automated contribution tracking, M-Pesa integration, loan management, and meeting coordination |
| **SACCO Share Liquidity** | Secondary market connecting sellers needing cash with buyers seeking cooperative yields |
| **Atomic Settlement Engine** | 11-state distributed saga ensuring funds and shares are never lost during transfer |
| **Trustee-Backed Guarantee** | Licensed trustee bank provides settlement finality for all transactions |
| **Negotiated Connections** | Buyer-seller introduction with structured offer/counter-offer workflow |
| **Structured Dispute Resolution** | Evidence-backed resolution with immutable audit trail |
| **Multi-Channel Notifications** | Firebase push, Africa's Talking SMS, email, and in-app alerts |
| **AI Assistant** | Google Gemini-powered chatbot with platform knowledge base |
| **Real-Time Communication** | WebSocket connections for live chat, settlement tracking, and notifications |
| **PDF Receipts** | Professional receipts with QR verification codes for every transaction |

---

## Tech Stack

| Technology | Purpose |
|------------|---------|
| **Python 3.12** | Runtime environment |
| **Django 5.0** | Web framework |
| **Django REST Framework** | API framework |
| **PostgreSQL** | Primary database |
| **Redis** | Caching, message broker, WebSocket layer |
| **Celery** | Background task processing |
| **Django Channels** | WebSocket support for real-time features |
| **SimpleJWT** | JWT authentication with refresh token rotation |
| **Google OAuth2** | Social authentication |
| **pyotp / qrcode** | Two-factor authentication with TOTP |
| **Africa's Talking** | SMS gateway |
| **Safaricom Daraja API** | M-Pesa STK Push integration |
| **Firebase Admin SDK** | Push notifications |
| **Google Gemini AI** | Chatbot intelligence |
| **ReportLab** | PDF receipt generation |
| **Cloudinary** | Cloud media storage |
| **Gunicorn** | WSGI production server |
| **Daphne** | ASGI server for WebSocket |
| **Docker** | Containerization |
| **GitHub Actions** | CI/CD pipeline |
| **Sentry** | Error monitoring |
| **Render** | Cloud hosting |


---

## API Endpoints

### Authentication (14 endpoints)
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/v1/auth/register/` | Register new user | No |
| POST | `/api/v1/auth/login/` | Login with email/password | No |
| POST | `/api/v1/auth/google/` | Google OAuth login | No |
| POST | `/api/v1/auth/verify/email/` | Verify email with OTP | No |
| POST | `/api/v1/auth/verify/phone/` | Verify phone with SMS OTP | No |
| POST | `/api/v1/auth/verify/resend/` | Resend verification code | No |
| GET | `/api/v1/auth/2fa/setup/` | Get 2FA QR code | Yes |
| POST | `/api/v1/auth/2fa/setup/` | Enable 2FA | Yes |
| POST | `/api/v1/auth/token/refresh/` | Refresh JWT token | No |
| POST | `/api/v1/auth/password/change/` | Change password | Yes |
| POST | `/api/v1/auth/password/reset/` | Request password reset | No |
| POST | `/api/v1/auth/password/reset/confirm/` | Confirm password reset | No |
| POST | `/api/v1/auth/logout/` | Logout (blacklist token) | Yes |

### User Profile (5 endpoints)
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/users/profile/` | Get current user profile | Yes |
| PATCH | `/api/v1/users/profile/` | Update profile | Yes |
| GET | `/api/v1/users/profile/detail/` | Get detailed profile with KYC | Yes |
| PATCH | `/api/v1/users/profile/detail/` | Update detailed profile | Yes |
| GET | `/api/v1/users/login-history/` | View login history | Yes |

### Chamas (18 endpoints)
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/chamas/` | List user's chamas | Yes |
| POST | `/api/v1/chamas/` | Create new chama | Yes |
| GET | `/api/v1/chamas/{id}/` | Get chama details | Yes |
| PATCH | `/api/v1/chamas/{id}/` | Update chama settings | Yes |
| POST | `/api/v1/chamas/{id}/join/` | Join chama | Yes |
| POST | `/api/v1/chamas/{id}/leave/` | Leave chama | Yes |
| GET | `/api/v1/chamas/{id}/members/` | List members | Yes |
| POST | `/api/v1/chamas/{id}/contributions/` | Record contribution | Yes |
| POST | `/api/v1/chamas/{id}/contributions/bulk/` | Bulk record contributions | Admin |
| GET | `/api/v1/chamas/{id}/contributions/` | List contributions | Yes |
| POST | `/api/v1/chamas/{id}/contributions/{id}/verify/` | Verify contribution | Admin |
| POST | `/api/v1/chamas/{id}/loans/` | Apply for loan | Yes |
| GET | `/api/v1/chamas/{id}/loans/` | List loans | Yes |
| POST | `/api/v1/chamas/{id}/loans/{id}/approve/` | Approve loan | Admin |
| POST | `/api/v1/chamas/{id}/loans/{id}/disburse/` | Disburse loan | Admin |
| POST | `/api/v1/chamas/{id}/loans/{id}/repay/` | Repay loan | Yes |
| POST | `/api/v1/chamas/{id}/meetings/` | Schedule meeting | Yes |
| POST | `/api/v1/chamas/{id}/meetings/{id}/attendance/` | Record attendance | Yes |

### Investments (15 endpoints)
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/investments/saccos/` | List verified SACCOs | Verified |
| GET | `/api/v1/investments/saccos/{id}/` | Get SACCO details | Verified |
| GET | `/api/v1/investments/saccos/{id}/share_classes/` | Get share classes | Verified |
| GET | `/api/v1/investments/holdings/` | My SACCO holdings | Yes |
| POST | `/api/v1/investments/requests/` | Create liquidity request | Verified |
| GET | `/api/v1/investments/requests/` | My liquidity requests | Verified |
| POST | `/api/v1/investments/requests/{id}/cancel/` | Cancel request | Verified |
| GET | `/api/v1/investments/opportunities/` | Browse opportunities | Verified |
| POST | `/api/v1/investments/opportunities/{id}/express_interest/` | Express interest | Verified |
| GET | `/api/v1/investments/connections/` | My connections | Verified |
| GET | `/api/v1/investments/connections/{id}/` | Connection details | Verified |
| POST | `/api/v1/investments/connections/{id}/make_offer/` | Make offer | Verified |
| POST | `/api/v1/investments/connections/{id}/offers/{id}/accept/` | Accept offer | Verified |
| POST | `/api/v1/investments/connections/{id}/offers/{id}/decline/` | Decline offer | Verified |
| POST | `/api/v1/investments/connections/{id}/offers/{id}/counter/` | Counter offer | Verified |

### Settlements (8 endpoints)
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/transactions/settlements/` | My settlements | Yes |
| GET | `/api/v1/transactions/settlements/{id}/` | Settlement details | Yes |
| GET | `/api/v1/transactions/settlements/{id}/events/` | Audit trail events | Yes |
| GET | `/api/v1/transactions/settlements/{id}/timeline/` | Human-readable timeline | Yes |
| GET | `/api/v1/transactions/settlements/{id}/ledger/` | Ledger entry | Yes |
| GET | `/api/v1/transactions/ledger/` | All ledger entries | Yes |
| GET | `/api/v1/transactions/disputes/` | List disputes | Admin |
| POST | `/api/v1/transactions/disputes/{id}/resolve/` | Resolve dispute | Admin |

### Notifications (8 endpoints)
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/notifications/` | List notifications | Yes |
| GET | `/api/v1/notifications/unread_count/` | Unread count | Yes |
| POST | `/api/v1/notifications/mark_all_read/` | Mark all read | Yes |
| POST | `/api/v1/notifications/{id}/mark_read/` | Mark single read | Yes |
| POST | `/api/v1/notifications/devices/` | Register device (FCM) | Yes |
| GET | `/api/v1/notifications/devices/` | List devices | Yes |
| GET | `/api/v1/notifications/preferences/` | Get preferences | Yes |
| POST | `/api/v1/notifications/preferences/` | Update preferences | Yes |

### Analytics (5 endpoints)
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/analytics/dashboard/user/` | User dashboard | Yes |
| GET | `/api/v1/analytics/dashboard/platform/` | Platform dashboard | Admin |
| GET | `/api/v1/analytics/chama/{id}/` | Chama analytics | Yes |
| GET | `/api/v1/analytics/sacco/{id}/` | SACCO market analytics | Yes |
| POST | `/api/v1/analytics/refresh/` | Refresh analytics | Admin |

### Chatbot (6 endpoints)
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/chatbot/sessions/` | List chat sessions | Yes |
| POST | `/api/v1/chatbot/sessions/` | Create chat session | Yes |
| GET | `/api/v1/chatbot/sessions/{id}/messages/` | Get messages | Yes |
| POST | `/api/v1/chatbot/sessions/{id}/send_message/` | Send message (AI response) | Yes |
| POST | `/api/v1/chatbot/context/` | Update chat context | Yes |
| GET | `/api/v1/chatbot/knowledge/` | Knowledge articles | Admin |

### M-Pesa (3 endpoints)
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/v1/payments/mpesa/stk-push/` | Initiate STK Push | Yes |
| GET | `/api/v1/payments/mpesa/transactions/` | Transaction history | Yes |
| GET | `/api/v1/payments/mpesa/transactions/{id}/` | Transaction detail | Yes |

### Receipts (3 endpoints)
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/receipts/` | List my receipts | Yes |
| GET | `/api/v1/receipts/{id}/` | Receipt details | Yes |
| GET | `/api/v1/receipts/{id}/download/` | Download PDF | Yes |

### WebSocket Endpoints
| Protocol | Endpoint | Description |
|----------|----------|-------------|
| WS | `/ws/chat/` | AI chatbot (real-time) |
| WS | `/ws/chat/{session_id}/` | Specific chat session |
| WS | `/ws/settlements/{intent_id}/` | Live settlement tracking |
| WS | `/ws/notifications/` | Real-time notification push |

---

## Role-Based Access Control

The platform implements 10 distinct roles:

| Role | Permissions |
|------|-------------|
| **PLATFORM_ADMIN** | Full platform access, user management, dispute resolution |
| **SACCO_ADMIN** | SACCO verification, disclosure management |
| **CHAMA_TREASURER** | Financial management, contributions, loan approvals |
| **CHAMA_CHAIRPERSON** | Member management, loan approvals, settings |
| **CHAMA_SECRETARY** | Meeting management, records, announcements |
| **CHAMA_MEMBER** | Basic chama access, contributions, loan requests |
| **INVESTOR** | Browse SACCO listings, express interest, make offers |
| **SELLER** | Create liquidity requests, accept offers |
| **INSTITUTIONAL_BUYER** | Bulk purchases, premium access |
| **SUPPORT_AGENT** | View disputes, assist users |

---

## Installation & Setup

### Prerequisites

- Python 3.12+
- PostgreSQL 16+
- Redis 7+
- Git

### Local Development

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/gitauwilly/sacco_bridge.git
   cd sacco-bridge

2. **Create Virtual Environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
        # venv\Scripts\activate   # Windows

3. **Install Dependencies:**
   ```bash
    pip install -r requirements.txt

4. **Set Up Database:**
   ```bash
    sudo -u postgres psql
    CREATE USER sacco_bridge_user WITH PASSWORD 'sacco_bridge_password';
    CREATE DATABASE sacco_bridge_db OWNER sacco_bridge_user;
    GRANT ALL PRIVILEGES ON DATABASE sacco_bridge_db TO sacco_bridge_user;
    ALTER USER sacco_bridge_user CREATEDB;
    \q

5. **Run Migrations:**
   ```bash
    python manage.py makemigrations core users chamas investments transactions notifications analytics chatbot mpesa receipts
    python manage.py migrate
    python manage.py migrate token_blacklist

6. **Create Initial Data:**
   ```bash
    python manage.py create_roles
    python manage.py create_notification_templates
    python manage.py createsuperuser
    python manage.py seed_data

7. **Run Development Server:**
   ```bash
    python manage.py runserver

8. **Run with WebSocket Support:**
   ```bash
    daphne -b 0.0.0.0 -p 8000 sacco_bridge.asgi:application


## Known Bugs
There are no known bugs 

---

## License
* **License:** MIT License.

---

## Support and Information
**Email:** gitauwilly254@gmail.com  