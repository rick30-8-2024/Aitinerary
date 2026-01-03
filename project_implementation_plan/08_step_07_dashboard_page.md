# Step 7: Frontend - Dashboard Page

## Objective
Create the main dashboard with YouTube URL input, user preference form, and itinerary history.

## Prerequisites
- Step 6 completed (Login Page)
- Step 5 completed (Itinerary API)

## Implementation Details

### 7.1 Page Layout (`page_serving_routers/pages/dashboard.html`)

**Sections:**
1. **Header** - Logo, user email, logout button
2. **Main Content**
   - YouTube URL Input Section
   - User Preferences Form
   - Generate Button
3. **Sidebar/Tab** - Past Itineraries List
4. **Generation Status Modal** - Progress indicator

### 7.2 YouTube URL Input Section
```html
<div class="url-input-section">
    <h2>Add YouTube Videos</h2>
    <p>Paste travel vlog URLs to analyze</p>
    
    <div id="url-inputs">
        <!-- Dynamic URL input fields -->
    </div>
    
    <button id="add-url-btn">+ Add Another Video</button>
</div>
```

**Features:**
- Start with 1 URL input, min 1, max 5
- "Add Another" button to add more
- "Remove" button on each (except if only 1)
- URL validation on blur
- Video title preview after validation

### 7.3 User Preferences Form

| Field | Type | Options/Validation |
|-------|------|-------------------|
| Budget | Number + Currency | Required, min 100 |
| Trip Type | Select | Family, Friends, Solo, Couple |
| Activity Style | Select | Sporty/Adventure, Relaxing, Mixed |
| Number of Travelers | Number | Required, 1-20 |
| Trip Duration | Number | Required, 1-30 days |
| Dietary Restrictions | Multi-select | Veg, Vegan, Halal, Kosher, Gluten-free, None |
| Mobility Constraints | Select | None, Wheelchair, Limited walking, Elderly |
| Must-Visit Places | Text | Optional, comma-separated |
| Additional Notes | Textarea | Optional, max 500 chars |

### 7.4 Generation Flow UI
```
1. User fills form, clicks "Generate Itinerary"
2. Button shows loading spinner
3. Modal appears: "Analyzing videos..."
4. Progress updates:
   - "Extracting transcripts..." (25%)
   - "Analyzing content..." (50%)
   - "Generating itinerary..." (75%)
   - "Almost done..." (90%)
5. On complete: Redirect to /itinerary/{id}
6. On error: Show error modal with retry option
```

### 7.5 Past Itineraries Section
```html
<div class="past-itineraries">
    <h3>Your Itineraries</h3>
    <div id="itinerary-list">
        <!-- Cards with: title, destination, date, view/delete buttons -->
    </div>
</div>
```

### 7.6 Auth Guard (Auto-redirect if not logged in)
```javascript
async function checkAuth() {
    const token = localStorage.getItem('access_token');
    if (!token) {
        window.location.href = '/login';
        return false;
    }
    
    try {
        const response = await fetch('/api/auth/me', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) {
            localStorage.removeItem('access_token');
            window.location.href = '/login';
            return false;
        }
        return await response.json();
    } catch {
        window.location.href = '/login';
        return false;
    }
}
```

### 7.7 Styles (`page_serving_routers/css/dashboard.css`)
- Consistent with login page design tokens
- Card-based layout for sections
- Smooth form interactions
- Responsive grid for desktop/mobile

## Research Areas
- Form multi-select component without external library
- Status polling with exponential backoff
- Skeleton loading for itinerary list

## Expected Outcome
- Users can input multiple YouTube URLs
- Comprehensive preference form with all required fields
- Real-time generation status updates
- View past itineraries from sidebar

## Estimated Effort
2-3 days

## Dependencies
- Step 5: Itinerary API
- Step 6: Login Page
