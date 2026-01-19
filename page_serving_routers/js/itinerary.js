let itineraryData = null;
let isSharedView = false;

function toTitleCase(str) {
    if (!str) return '';
    return str.toLowerCase().replace(/\b\w/g, char => char.toUpperCase());
}

function formatTitleWithDate(title) {
    if (!itineraryData || !itineraryData.days || itineraryData.days.length === 0) {
        return toTitleCase(title);
    }

    const firstDay = itineraryData.days[0];
    if (firstDay.date) {
        const date = new Date(firstDay.date);
        const day = date.getDate();
        const month = date.toLocaleString('en-US', { month: 'long' });
        const year = date.getFullYear();

        const titleWithoutDate = title.replace(/\s*-\s*\w+\s+\d{4}$/, '').trim();
        return `${toTitleCase(titleWithoutDate)} - ${day} ${month} ${year}`;
    }

    return toTitleCase(title);
}

document.addEventListener('DOMContentLoaded', async function () {
    setTimeout(() => {
        document.body.classList.remove('loading');
    }, 300);

    const pathParts = window.location.pathname.split('/');
    isSharedView = pathParts[1] === 'shared';
    const idOrCode = pathParts[2];

    if (!idOrCode) {
        showError('Invalid itinerary URL');
        return;
    }

    if (!isSharedView) {
        const isAuthenticated = await checkAuth();
        if (!isAuthenticated) return;
    }

    await loadItinerary(idOrCode);
    initExport();
    initShare();
    initStickyNavigation();
});

async function checkAuth() {
    const token = localStorage.getItem('access_token');
    if (!token) {
        window.location.href = '/login';
        return false;
    }

    try {
        const response = await fetch('/api/auth/verify', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) {
            localStorage.removeItem('access_token');
            window.location.href = '/login';
            return false;
        }
        return true;
    } catch (error) {
        window.location.href = '/login';
        return false;
    }
}

async function loadItinerary(idOrCode) {
    const loadingEl = document.getElementById('loading-state');
    const errorEl = document.getElementById('error-state');
    const contentEl = document.getElementById('itinerary-content');

    try {
        const endpoint = isSharedView
            ? `/api/itinerary/shared/${idOrCode}`
            : `/api/itinerary/${idOrCode}`;

        const headers = isSharedView ? {} : {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        };

        const response = await fetch(endpoint, { headers });

        if (!response.ok) {
            throw new Error(response.status === 404 ? 'Itinerary not found' : 'Failed to load');
        }

        itineraryData = await response.json();

        loadingEl.style.display = 'none';
        contentEl.style.display = 'block';

        renderItinerary();
    } catch (error) {
        loadingEl.style.display = 'none';
        errorEl.style.display = 'flex';
        document.getElementById('error-message').textContent = error.message;
    }
}

function renderItinerary() {
    document.getElementById('itinerary-title').textContent = formatTitleWithDate(itineraryData.title);
    document.getElementById('itinerary-destination').querySelector('span').textContent =
        toTitleCase(itineraryData.destination) + (itineraryData.country ? `, ${toTitleCase(itineraryData.country)}` : '');
    document.getElementById('itinerary-duration').querySelector('span').textContent =
        `${itineraryData.days.length} Days`;
    document.getElementById('itinerary-summary').textContent = itineraryData.summary;

    renderSourceVideos();
    renderDays();
    renderBudget();
    renderNavigation();
    renderTips();
    renderPacking();
    renderPhrases();

    if (isSharedView) {
        document.getElementById('share-btn').style.display = 'none';
    }
}

function getYouTubeVideoId(url) {
    const patterns = [
        /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})/,
        /youtube\.com\/shorts\/([a-zA-Z0-9_-]{11})/
    ];
    
    for (const pattern of patterns) {
        const match = url.match(pattern);
        if (match) return match[1];
    }
    return null;
}

function getYouTubeThumbnail(videoId, quality = 'mqdefault') {
    return `https://img.youtube.com/vi/${videoId}/${quality}.jpg`;
}

function renderSourceVideos() {
    const youtubeUrls = itineraryData.youtube_urls || [];
    const cardEl = document.getElementById('source-videos-card');
    const listEl = document.getElementById('source-videos-list');
    
    if (!youtubeUrls || youtubeUrls.length === 0) {
        cardEl.style.display = 'none';
        return;
    }
    
    cardEl.style.display = 'block';
    
    listEl.innerHTML = youtubeUrls.map((url, index) => {
        const videoId = getYouTubeVideoId(url);
        if (!videoId) return '';
        
        const thumbnail = getYouTubeThumbnail(videoId);
        const videoTitle = itineraryData.video_titles && itineraryData.video_titles[index]
            ? itineraryData.video_titles[index]
            : `Video ${index + 1}`;
        
        return `
            <a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer" class="source-video-item">
                <div class="video-thumbnail">
                    <img src="${thumbnail}" alt="${escapeHtml(videoTitle)}" loading="lazy">
                    <div class="play-overlay">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                            <polygon points="5 3 19 12 5 21 5 3"></polygon>
                        </svg>
                    </div>
                </div>
                <div class="video-info">
                    <span class="video-title">${escapeHtml(videoTitle)}</span>
                </div>
            </a>
        `;
    }).join('');
}

function renderDays() {
    const container = document.getElementById('days-container');
    container.innerHTML = itineraryData.days.map(day => `
        <div class="day-card" id="day-${day.day_number}">
            <div class="day-header">
                <h2><span>Day ${day.day_number}</span> — ${escapeHtml(day.theme)}</h2>
                <span class="day-cost">${formatCurrency(day.total_estimated_cost)}</span>
            </div>
            ${day.summary ? `<div class="day-summary">${escapeHtml(day.summary)}</div>` : ''}
            <div class="day-content">
                ${renderActivities(day.activities)}
                ${day.meals && day.meals.length > 0 ? renderMeals(day.meals) : ''}
            </div>
        </div>
    `).join('');
}

function formatActivityTitle(act) {
    const placeName = toTitleCase(act.place_name);
    if (act.event_name) {
        return `${placeName} — ${toTitleCase(act.event_name)}`;
    }
    return placeName;
}

function formatCost(cost, isUnknown) {
    if (isUnknown) {
        return '<span class="cost-unknown">Price not confirmed</span>';
    }
    return formatCurrency(cost);
}

function renderActivities(activities) {
    if (!activities || activities.length === 0) return '<p class="no-activities">No activities planned</p>';

    return activities.map(act => `
        <div class="activity-item ${act.is_hidden_gem ? 'hidden-gem' : ''}">

            <div class="activity-content">
                <h4>
                    ${act.is_hidden_gem ? '<span class="gem-badge">💎 Hidden Gem</span>' : ''}
                    ${escapeHtml(formatActivityTitle(act))}
                </h4>
                <p>${escapeHtml(act.description)}</p>
                <div class="activity-meta">
                    <span class="activity-cost">💰 ${formatCost(act.estimated_cost, act.cost_unknown)}</span>
                    ${act.travel_time_from_previous ? `<span>🚶 ${escapeHtml(act.travel_time_from_previous)}</span>` : ''}
                    ${act.transport_mode ? `<span>🚗 ${escapeHtml(act.transport_mode)}${act.transport_cost_unknown ? ' (Price not confirmed)' : (act.transport_cost ? ` - ${formatCurrency(act.transport_cost)}` : '')}</span>` : ''}
                    ${act.booking_required ? `<span>📋 Booking required</span>` : ''}
                    ${act.source === 'internet_search' ? `<span class="source-badge">🌐 Web</span>` : ''}
                </div>
                ${act.tips && act.tips.length > 0 ? `
                    <div class="activity-tips">
                        <h5>Tips</h5>
                        <ul>${act.tips.map(t => `<li>${escapeHtml(t)}</li>`).join('')}</ul>
                    </div>
                ` : ''}
                ${act.warnings && act.warnings.length > 0 ? `
                    <div class="activity-warnings">
                        <h5>Warnings</h5>
                        <ul>${act.warnings.map(w => `<li>${escapeHtml(w)}</li>`).join('')}</ul>
                    </div>
                ` : ''}
            </div>
        </div>
    `).join('');
}

function renderMeals(meals) {
    const mealIcons = {
        'breakfast': '🍳',
        'lunch': '🍜',
        'dinner': '🍽️',
        'snack': '🍿'
    };

    return `
        <div class="meals-section">
            <h3>🍴 Meal Recommendations</h3>
            ${meals.map(meal => `
                <div class="meal-item ${meal.is_local_delicacy ? 'local-delicacy' : ''}">
                    <div class="meal-icon">${mealIcons[meal.meal_type] || '🍴'}</div>
                    <div class="meal-content">
                        <h4>
                            ${meal.is_local_delicacy ? '<span class="delicacy-badge">🏆 Local Delicacy</span>' : ''}
                            ${escapeHtml(toTitleCase(meal.place_name))}
                        </h4>
                        <p>${meal.cuisine ? escapeHtml(meal.cuisine) : ''} ${meal.dietary_notes ? `• ${escapeHtml(meal.dietary_notes)}` : ''}</p>
                        <div class="meal-meta">
                            <span>💰 ${formatCost(meal.estimated_cost, meal.cost_unknown)}/person</span>
                            ${meal.recommendation_reason ? `<span>⭐ ${escapeHtml(meal.recommendation_reason)}</span>` : ''}
                            ${meal.source === 'internet_search' ? `<span class="source-badge">🌐 Web</span>` : ''}
                        </div>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}

function renderBudget() {
    const total = itineraryData.total_budget_estimate;
    const breakdown = itineraryData.budget_breakdown || {};

    document.getElementById('total-budget').textContent = formatCurrency(total);

    const breakdownEl = document.getElementById('budget-breakdown');
    const categories = [
        { key: 'food', label: 'Food & Dining', icon: '🍽️' },
        { key: 'activities', label: 'Activities', icon: '🎯' },
        { key: 'transportation', label: 'Transportation', icon: '🚗' },
        { key: 'shopping', label: 'Shopping', icon: '🛍️' },
        { key: 'miscellaneous', label: 'Miscellaneous', icon: '📦' }
    ];

    let budgetHtml = categories
        .filter(cat => breakdown[cat.key] > 0)
        .map(cat => `
            <div class="budget-item">
                <span class="label">${cat.icon} ${cat.label}</span>
                <span class="value">${formatCurrency(breakdown[cat.key])}</span>
            </div>
        `).join('');

    if (breakdown.subtotal_without_accommodation > 0) {
        budgetHtml += `
            <div class="budget-item subtotal">
                <span class="label">📊 Subtotal (excl. stay)</span>
                <span class="value">${formatCurrency(breakdown.subtotal_without_accommodation)}</span>
            </div>
        `;
    }

    if (breakdown.accommodation_budget > 0) {
        budgetHtml += `
            <div class="budget-item accommodation-budget">
                <span class="label">🏨 Budget for Accommodation</span>
                <span class="value">${formatCurrency(breakdown.accommodation_budget)}</span>
            </div>
        `;
    }

    breakdownEl.innerHTML = budgetHtml;

    if (itineraryData.accommodation_note) {
        const existingNote = breakdownEl.parentElement.querySelector('.accommodation-note');
        if (existingNote) {
            existingNote.remove();
        }
        const noteEl = document.createElement('div');
        noteEl.className = 'accommodation-note';
        noteEl.innerHTML = `<p>💡 ${escapeHtml(itineraryData.accommodation_note)}</p>`;
        breakdownEl.parentElement.appendChild(noteEl);
    }
}

function renderNavigation() {
    const navEl = document.getElementById('day-nav');
    const dayLinks = itineraryData.days.map((day, index) => `
        <a href="#day-${day.day_number}" onclick="scrollToDay(${day.day_number}, ${index === 0}); return false;">
            Day ${day.day_number}: ${escapeHtml(day.theme.substring(0, 20))}${day.theme.length > 20 ? '...' : ''}
        </a>
    `).join('');

    const extraLinks = `
        <div class="nav-separator"></div>
        <a href="#tips-section" onclick="scrollToSection('tips-section'); return false;">
            📋 Travel Tips
        </a>
        <a href="#packing-section" onclick="scrollToSection('packing-section'); return false;">
            🎒 Packing Suggestions
        </a>
        <a href="#phrases-section" onclick="scrollToSection('phrases-section'); return false;">
            💬 Useful Phrases
        </a>
    `;

    navEl.innerHTML = dayLinks + extraLinks;
}

function scrollToDay(dayNumber, isFirstDay) {
    if (isFirstDay) {
        window.scrollTo({ top: 0, behavior: 'smooth' });
        return;
    }
    const element = document.getElementById(`day-${dayNumber}`);
    if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

function scrollToSection(sectionId) {
    const element = document.getElementById(sectionId);
    if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

function renderTips() {
    const tipsEl = document.getElementById('general-tips');
    const tips = itineraryData.general_tips || [];

    if (tips.length === 0) {
        tipsEl.innerHTML = '<li>No tips available</li>';
        return;
    }

    tipsEl.innerHTML = tips.map(tip => `<li>${escapeHtml(tip)}</li>`).join('');
}

function renderPacking() {
    const packingEl = document.getElementById('packing-list');
    const items = itineraryData.packing_suggestions || [];

    if (items.length === 0) {
        packingEl.innerHTML = '<li>No suggestions available</li>';
        return;
    }

    packingEl.innerHTML = items.map(item => `<li>${escapeHtml(item)}</li>`).join('');
}

function renderPhrases() {
    const phrasesEl = document.getElementById('phrases-list');
    const phrases = itineraryData.language_phrases || [];

    if (phrases.length === 0) {
        phrasesEl.innerHTML = '<li>No phrases available</li>';
        return;
    }

    phrasesEl.innerHTML = phrases.map(phrase => `<li>${escapeHtml(phrase)}</li>`).join('');
}

function initExport() {
    document.getElementById('export-btn').addEventListener('click', exportToPDF);
}

async function exportToPDF() {
    const btn = document.getElementById('export-btn');
    const originalText = btn.innerHTML;

    btn.innerHTML = `
        <svg class="spinner" width="16" height="16" viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" fill="none" stroke-dasharray="31.4 31.4" stroke-linecap="round" style="animation: spin 1s linear infinite"/>
        </svg>
        Generating PDF...
    `;
    btn.disabled = true;

    try {
        await PDFGenerator.generatePDF(itineraryData);
    } catch (error) {
        console.error('PDF export failed:', error);
        alert('Failed to generate PDF. Please try again.');
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

function initShare() {
    const shareBtn = document.getElementById('share-btn');
    const modal = document.getElementById('share-modal');
    const closeBtn = document.getElementById('close-share-modal');
    const toggle = document.getElementById('public-toggle');
    const linkSection = document.getElementById('share-link-section');
    const linkInput = document.getElementById('share-link');
    const copyBtn = document.getElementById('copy-link-btn');

    shareBtn.addEventListener('click', () => {
        toggle.checked = itineraryData.is_public;
        updateShareLink();
        modal.classList.add('show');
    });

    closeBtn.addEventListener('click', () => {
        modal.classList.remove('show');
    });

    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.classList.remove('show');
        }
    });

    toggle.addEventListener('change', async () => {
        const isPublic = toggle.checked;

        try {
            const response = await fetch(`/api/itinerary/${itineraryData.id}/visibility?is_public=${isPublic}`, {
                method: 'PATCH',
                headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` }
            });

            if (response.ok) {
                const data = await response.json();
                itineraryData.is_public = isPublic;
                itineraryData.share_code = data.share_code;
                updateShareLink();
            } else {
                toggle.checked = !isPublic;
                alert('Failed to update sharing settings');
            }
        } catch (error) {
            toggle.checked = !isPublic;
            alert('Connection error. Please try again.');
        }
    });

    copyBtn.addEventListener('click', () => {
        linkInput.select();
        navigator.clipboard.writeText(linkInput.value).then(() => {
            copyBtn.textContent = 'Copied!';
            setTimeout(() => {
                copyBtn.textContent = 'Copy';
            }, 2000);
        });
    });

    function updateShareLink() {
        if (itineraryData.is_public && itineraryData.share_code) {
            linkSection.style.display = 'block';
            linkInput.value = `${window.location.origin}/shared/${itineraryData.share_code}`;
        } else {
            linkSection.style.display = 'none';
        }
    }
}

function formatCurrency(amount) {
    const currency = itineraryData?.currency || 'USD';
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: currency,
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(amount || 0);
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showError(message) {
    document.getElementById('loading-state').style.display = 'none';
    document.getElementById('error-state').style.display = 'flex';
    document.getElementById('error-message').textContent = message;
}

function initStickyNavigation() {
    const navCard = document.querySelector('.nav-card');
    const budgetCard = document.querySelector('.budget-card');
    const sidebar = document.querySelector('.sidebar');

    if (!navCard || !budgetCard || !sidebar) return;

    let placeholder = null;
    let isSticky = false;
    const stickyOffset = 20;

    function handleScroll() {
        const budgetRect = budgetCard.getBoundingClientRect();
        const stickyTrigger = budgetRect.bottom;
        const sidebarRect = sidebar.getBoundingClientRect();

        if (stickyTrigger <= stickyOffset && !isSticky) {
            isSticky = true;

            placeholder = document.createElement('div');
            placeholder.style.height = navCard.offsetHeight + 'px';
            placeholder.style.visibility = 'hidden';
            navCard.parentNode.insertBefore(placeholder, navCard.nextSibling);

            navCard.classList.add('is-sticky');
            navCard.style.right = (window.innerWidth - sidebarRect.right) + 'px';
        } else if (stickyTrigger > stickyOffset && isSticky) {
            isSticky = false;
            navCard.classList.remove('is-sticky');
            navCard.style.right = '';

            if (placeholder && placeholder.parentNode) {
                placeholder.parentNode.removeChild(placeholder);
                placeholder = null;
            }
        }

        if (isSticky) {
            navCard.style.right = (window.innerWidth - sidebarRect.right) + 'px';
        }
    }

    function handleResize() {
        if (isSticky) {
            const sidebarRect = sidebar.getBoundingClientRect();
            navCard.style.right = (window.innerWidth - sidebarRect.right) + 'px';
        }
    }

    window.addEventListener('scroll', handleScroll, { passive: true });
    window.addEventListener('resize', handleResize, { passive: true });

    handleScroll();
}
