# Step 6: Frontend - Login Page

## Objective
Create a professional, responsive login page with authentication and auto-redirect functionality.

## Prerequisites
- Step 1 completed (Project Setup)
- Step 2 completed (Authentication API)

## Implementation Details

### 6.1 Page Structure (`page_serving_routers/pages/login.html`)

**Layout:**
- Centered login card on subtle gradient background
- Logo/brand name at top
- Email and password inputs
- "Remember me" checkbox
- Login button with loading state
- Link to register (if needed)
- Error message display area

**Design Principles:**
- Modern, clean aesthetic
- Subtle animations on focus/hover
- Mobile-responsive
- Accessible (proper labels, ARIA)

### 6.2 Styles (`page_serving_routers/css/login.css`)
```css
/* Design tokens */
:root {
  --primary: #4F46E5;      /* Indigo */
  --primary-hover: #4338CA;
  --bg-gradient-start: #EEF2FF;
  --bg-gradient-end: #E0E7FF;
  --text-primary: #1F2937;
  --text-secondary: #6B7280;
  --error: #EF4444;
  --success: #10B981;
  --border-radius: 12px;
  --shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
}
```

### 6.3 JavaScript (`page_serving_routers/js/login.js`)

**Auto-Login Check (on page load):**
```javascript
async function checkExistingSession() {
    const token = localStorage.getItem('access_token');
    if (!token) return;
    
    try {
        const response = await fetch('/api/auth/verify', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (response.ok) {
            window.location.href = '/dashboard';
        } else {
            localStorage.removeItem('access_token');
        }
    } catch (error) {
        localStorage.removeItem('access_token');
    }
}
```

**Login Handler:**
```javascript
async function handleLogin(event) {
    event.preventDefault();
    setLoading(true);
    clearError();
    
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    
    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        
        if (response.ok) {
            const data = await response.json();
            localStorage.setItem('access_token', data.access_token);
            window.location.href = '/dashboard';
        } else {
            const error = await response.json();
            showError(error.detail || 'Login failed');
        }
    } catch (error) {
        showError('Connection error. Please try again.');
    } finally {
        setLoading(false);
    }
}
```

### 6.4 Page Router (`page_serving_routers/pages_router.py`)
```python
from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter()

@router.get("/login")
async def login_page():
    return FileResponse("page_serving_routers/pages/login.html")

@router.get("/")
async def root():
    return RedirectResponse("/login")
```

### 6.5 Registration (Optional for MVP)
- Could be admin-only initially
- Or simple registration form similar to login

## Research Areas
- CSS animations for smooth transitions
- Form validation best practices
- Accessibility guidelines (WCAG)

## Expected Outcome
- Professional login page matching modern SaaS aesthetics
- Auto-redirect to dashboard if already logged in
- Error handling with user-friendly messages
- Loading states during API calls

## Estimated Effort
1-2 days

## Dependencies
- Step 1: Project Setup
- Step 2: Authentication API
