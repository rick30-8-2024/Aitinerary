# Step 2: Authentication System

## Objective
Implement user registration, login, and JWT-based session management with auto-login/redirect functionality.

## Prerequisites
- Step 1 completed (Project Setup)
- MongoDB connection working

## Implementation Details

### 2.1 User Model (`models/user.py`)
```python
class UserCreate:
    email: str
    password: str

class UserInDB:
    id: str
    email: str
    password_hash: str
    created_at: datetime

class Token:
    access_token: str
    token_type: str
```

### 2.2 Password Utilities (`services/auth_service.py`)
- Password hashing with bcrypt
- Password verification
- JWT token creation with expiry
- JWT token validation

### 2.3 Auth Router (`api/routers/auth.py`)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/register` | POST | Create new user account |
| `/api/auth/login` | POST | Authenticate and return JWT |
| `/api/auth/logout` | POST | Invalidate session (client-side) |
| `/api/auth/me` | GET | Get current user info (protected) |
| `/api/auth/verify` | GET | Verify if token is valid |

### 2.4 Auth Dependency (`api/dependencies.py`)
- Create `get_current_user` dependency
- Extract and validate JWT from:
  - Authorization header (Bearer token)
  - OR HTTP-only cookie

### 2.5 Frontend Auth Flow
**Login Page:**
- Form with email/password
- On success: store token, redirect to dashboard
- On error: show error message

**Auto-login Logic (JavaScript):**
```
On page load:
├── If on login page AND token valid → redirect to dashboard
└── If on protected page AND token invalid → redirect to login
```

**Token Storage:**
- Store in localStorage (simpler) or HTTP-only cookie (more secure)
- Include in all API requests via Authorization header

### 2.6 MongoDB User Collection
```javascript
// Indexes
{ email: 1 } // unique index for fast lookup
```

## Research Areas
- JWT refresh token strategy (for longer sessions)
- HTTP-only cookies vs localStorage security trade-offs
- FastAPI OAuth2PasswordBearer for Swagger UI integration

## Expected Outcome
- User can register with email/password
- User can login and receive JWT token
- Protected routes require valid token
- Auto-redirect based on auth state working
- Passwords securely hashed

## Estimated Effort
2-3 days

## Dependencies
- Step 1: Project Setup
