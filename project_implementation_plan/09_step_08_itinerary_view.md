# Step 8: Frontend - Itinerary View & PDF Export

## Objective
Create the itinerary display page with professional layout and PDF export functionality.

## Prerequisites
- Step 7 completed (Dashboard Page)
- Step 5 completed (Itinerary API)

## Implementation Details

### 8.1 Page Layout (`page_serving_routers/pages/itinerary.html`)

**Sections:**
1. **Header Bar** - Back to dashboard, title, export buttons
2. **Trip Summary Card** - Destination, dates, travelers, budget overview
3. **Day-by-Day Itinerary** - Expandable day sections
4. **Sidebar** - Quick navigation, budget breakdown

### 8.2 Itinerary Card Structure

**Day Section:**
```html
<div class="day-card" id="day-1">
    <div class="day-header">
        <h3>Day 1 - Cultural Exploration</h3>
        <span class="day-cost">Estimated: $120</span>
    </div>
    
    <div class="activities">
        <div class="activity morning">
            <span class="time">09:00 - 11:00</span>
            <h4>Visit Temple of Dawn</h4>
            <p class="description">...</p>
            <div class="meta">
                <span class="cost">$5 entry</span>
                <span class="travel">15 min from hotel</span>
            </div>
            <div class="tips">💡 Arrive early to avoid crowds</div>
            <div class="warnings">⚠️ Watch for overpriced tuk-tuks</div>
        </div>
        
        <div class="meal lunch">
            <span class="time">12:00 - 13:00</span>
            <h4>🍜 Lunch at Local Market</h4>
            <p>Try Pad Thai and Mango Sticky Rice</p>
            <span class="cost">$8-12</span>
        </div>
        
        <!-- More activities... -->
    </div>
</div>
```

### 8.3 PDF Export Implementation

**Libraries (via CDN):**
```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
```

**Export Function:**
```javascript
async function exportToPDF() {
    const element = document.getElementById('itinerary-content');
    
    // Show loading state
    showExportLoading(true);
    
    const opt = {
        margin: [10, 10, 10, 10],
        filename: `${itineraryTitle}_itinerary.pdf`,
        image: { type: 'jpeg', quality: 0.98 },
        html2canvas: { 
            scale: 2,
            useCORS: true,
            letterRendering: true
        },
        jsPDF: { 
            unit: 'mm', 
            format: 'a4', 
            orientation: 'portrait' 
        },
        pagebreak: { mode: ['avoid-all', 'css', 'legacy'] }
    };
    
    try {
        await html2pdf().set(opt).from(element).save();
    } catch (error) {
        showError('Failed to generate PDF. Please try again.');
    } finally {
        showExportLoading(false);
    }
}
```

### 8.4 Print-Friendly Styles
```css
@media print {
    .no-print { display: none !important; }
    .day-card { page-break-inside: avoid; }
    .activity { break-inside: avoid; }
    body { background: white; }
}

/* PDF-specific overrides */
.pdf-mode .day-card {
    border: 1px solid #ddd;
    margin-bottom: 20px;
}
```

### 8.5 Budget Breakdown Widget
```html
<div class="budget-breakdown">
    <h4>Budget Summary</h4>
    <div class="budget-chart">
        <!-- Simple bar chart or pie chart -->
    </div>
    <ul>
        <li>Accommodation: $XXX (XX%)</li>
        <li>Food & Dining: $XXX (XX%)</li>
        <li>Activities: $XXX (XX%)</li>
        <li>Transportation: $XXX (XX%)</li>
    </ul>
    <div class="total">
        <strong>Total Estimated:</strong> $XXX
        <span class="vs-budget">Under budget by $XX ✓</span>
    </div>
</div>
```

### 8.6 Navigation
- Sticky sidebar with day links
- Smooth scroll to day sections
- Collapse/expand all days
- Share button (copy link to clipboard)

## Research Areas
- html2pdf.js page break handling
- CSS for PDF optimization
- Image handling in PDF (if any maps/images added later)

## Expected Outcome
- Beautiful, readable itinerary display
- One-click PDF export with professional formatting
- Budget visualization
- Easy navigation between days

## Estimated Effort
2-3 days

## Dependencies
- Step 5: Itinerary API
- Step 7: Dashboard Page
