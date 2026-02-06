let itineraryData = null;
let isSharedView = false;
let chatHistory = [];

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

    if (!isSharedView && itineraryData) {
        initChat();
    }
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
    const titleEl = document.getElementById('itinerary-title');
    titleEl.textContent = formatTitleWithDate(itineraryData.title);

    const destEl = document.getElementById('itinerary-destination').querySelector('span');
    destEl.textContent = toTitleCase(itineraryData.destination) + (itineraryData.country ? `, ${toTitleCase(itineraryData.country)}` : '');

    document.getElementById('itinerary-duration').querySelector('span').textContent =
        `${itineraryData.days.length} Days`;

    const summaryEl = document.getElementById('itinerary-summary');
    summaryEl.textContent = itineraryData.summary;

    if (!isSharedView) {
        addEditButton(titleEl, 'title', 'text');
        addEditButton(summaryEl, 'summary', 'textarea');
    }

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

async function saveDaysField() {
    return await saveItineraryField('days', itineraryData.days);
}

function attachDayEditButtons() {
    document.querySelectorAll('.day-header').forEach(header => {
        const themeEl = header.querySelector('[data-edit="day-theme"]');
        if (themeEl) {
            const btn = document.createElement('button');
            btn.className = 'edit-btn day-theme-edit-btn';
            btn.title = 'Edit day theme';
            btn.appendChild(createPencilIcon());
            themeEl.parentElement.appendChild(btn);

            btn.addEventListener('click', () => {
                if (btn.classList.contains('active')) return;
                btn.classList.add('active');
                const dayIdx = parseInt(themeEl.dataset.day);
                const currentVal = itineraryData.days[dayIdx].theme || '';
                const origHTML = themeEl.innerHTML;

                themeEl.innerHTML = `
                    <input type="text" class="edit-field" value="${escapeHtml(currentVal)}" style="min-width:200px">
                    <div class="edit-actions">
                        <button class="edit-cancel">Cancel</button>
                        <button class="edit-save">Save</button>
                    </div>
                `;
                themeEl.querySelector('.edit-field').focus();

                themeEl.querySelector('.edit-cancel').addEventListener('click', () => {
                    themeEl.innerHTML = origHTML;
                    btn.classList.remove('active');
                });

                themeEl.querySelector('.edit-save').addEventListener('click', async () => {
                    const newVal = themeEl.querySelector('.edit-field').value.trim();
                    if (!newVal) return;
                    const saveBtn = themeEl.querySelector('.edit-save');
                    saveBtn.textContent = 'Saving...';
                    saveBtn.disabled = true;
                    itineraryData.days[dayIdx].theme = newVal;
                    const ok = await saveDaysField();
                    if (ok) {
                        themeEl.textContent = newVal;
                        btn.classList.remove('active');
                    } else {
                        themeEl.innerHTML = origHTML;
                        btn.classList.remove('active');
                        alert('Failed to save. Please try again.');
                    }
                });

                themeEl.querySelector('.edit-field').addEventListener('keydown', (e) => {
                    if (e.key === 'Enter') themeEl.querySelector('.edit-save').click();
                    if (e.key === 'Escape') themeEl.querySelector('.edit-cancel').click();
                });
            });
        }
    });

    document.querySelectorAll('[data-edit="day-summary"]').forEach(el => {
        const dayIdx = parseInt(el.dataset.day);
        const btn = document.createElement('button');
        btn.className = 'edit-btn';
        btn.title = 'Edit day summary';
        btn.appendChild(createPencilIcon());
        btn.style.display = 'inline-flex';
        btn.style.verticalAlign = 'middle';
        btn.style.marginLeft = '6px';
        el.appendChild(btn);

        btn.addEventListener('click', () => {
            if (btn.classList.contains('active')) return;
            btn.classList.add('active');
            const currentVal = itineraryData.days[dayIdx].summary || '';
            const origHTML = el.innerHTML;

            el.innerHTML = `
                <textarea class="edit-field" rows="3">${escapeHtml(currentVal)}</textarea>
                <div class="edit-actions">
                    <button class="edit-cancel">Cancel</button>
                    <button class="edit-save">Save</button>
                </div>
            `;
            el.querySelector('.edit-field').focus();

            el.querySelector('.edit-cancel').addEventListener('click', () => {
                el.innerHTML = origHTML;
            });

            el.querySelector('.edit-save').addEventListener('click', async () => {
                const newVal = el.querySelector('.edit-field').value.trim();
                if (!newVal) return;
                const saveBtn = el.querySelector('.edit-save');
                saveBtn.textContent = 'Saving...';
                saveBtn.disabled = true;
                itineraryData.days[dayIdx].summary = newVal;
                const ok = await saveDaysField();
                if (ok) {
                    el.textContent = newVal;
                    const newBtn = document.createElement('button');
                    newBtn.className = 'edit-btn';
                    newBtn.title = 'Edit day summary';
                    newBtn.appendChild(createPencilIcon());
                    newBtn.style.display = 'inline-flex';
                    newBtn.style.verticalAlign = 'middle';
                    newBtn.style.marginLeft = '6px';
                    el.appendChild(newBtn);
                    reattachDaySummaryBtn(el, dayIdx, newBtn);
                } else {
                    el.innerHTML = origHTML;
                    alert('Failed to save. Please try again.');
                }
            });
        });
    });

    document.querySelectorAll('.activity-item[data-day][data-act]').forEach(item => {
        const dayIdx = parseInt(item.dataset.day);
        const actIdx = parseInt(item.dataset.act);
        const btn = document.createElement('button');
        btn.className = 'edit-btn';
        btn.title = 'Edit activity';
        btn.appendChild(createPencilIcon());
        item.appendChild(btn);

        btn.addEventListener('click', () => {
            if (btn.classList.contains('active')) return;
            btn.classList.add('active');
            const act = itineraryData.days[dayIdx].activities[actIdx];
            const contentEl = item.querySelector('.activity-content');
            const origHTML = contentEl.innerHTML;

            contentEl.innerHTML = `
                <div class="inline-edit-overlay">
                    <div class="edit-field-group">
                        <label>Place Name</label>
                        <input type="text" data-field="place_name" value="${escapeHtml(act.place_name || '')}">
                    </div>
                    ${act.event_name !== undefined && act.event_name !== null ? `
                    <div class="edit-field-group">
                        <label>Event Name</label>
                        <input type="text" data-field="event_name" value="${escapeHtml(act.event_name || '')}">
                    </div>` : ''}
                    <div class="edit-field-group">
                        <label>Description</label>
                        <textarea data-field="description" rows="3">${escapeHtml(act.description || '')}</textarea>
                    </div>
                    <div class="edit-field-group">
                        <label>Estimated Cost</label>
                        <input type="number" data-field="estimated_cost" value="${act.estimated_cost || 0}" min="0" step="0.01">
                    </div>
                    <div class="edit-field-group">
                        <label>Tips (one per line)</label>
                        <textarea data-field="tips" rows="2">${(act.tips || []).join('\n')}</textarea>
                    </div>
                    <div class="edit-field-group">
                        <label>Warnings (one per line)</label>
                        <textarea data-field="warnings" rows="2">${(act.warnings || []).join('\n')}</textarea>
                    </div>
                    <div class="edit-actions">
                        <button class="edit-cancel">Cancel</button>
                        <button class="edit-save">Save</button>
                    </div>
                </div>
            `;

            contentEl.querySelector('.edit-cancel').addEventListener('click', () => {
                contentEl.innerHTML = origHTML;
                btn.classList.remove('active');
            });

            contentEl.querySelector('.edit-save').addEventListener('click', async () => {
                const saveBtn = contentEl.querySelector('.edit-save');
                saveBtn.textContent = 'Saving...';
                saveBtn.disabled = true;

                const fields = contentEl.querySelectorAll('[data-field]');
                fields.forEach(f => {
                    const key = f.dataset.field;
                    if (key === 'tips' || key === 'warnings') {
                        act[key] = f.value.split('\n').map(l => l.trim()).filter(l => l.length > 0);
                    } else if (key === 'estimated_cost') {
                        act[key] = parseFloat(f.value) || 0;
                    } else {
                        act[key] = f.value.trim();
                    }
                });

                const ok = await saveDaysField();
                if (ok) {
                    renderDays();
                } else {
                    contentEl.innerHTML = origHTML;
                    btn.classList.remove('active');
                    alert('Failed to save. Please try again.');
                }
            });
        });
    });

    document.querySelectorAll('.meal-item[data-day][data-meal]').forEach(item => {
        const dayIdx = parseInt(item.dataset.day);
        const mealIdx = parseInt(item.dataset.meal);
        const btn = document.createElement('button');
        btn.className = 'edit-btn';
        btn.title = 'Edit meal';
        btn.appendChild(createPencilIcon());
        item.appendChild(btn);

        btn.addEventListener('click', () => {
            if (btn.classList.contains('active')) return;
            btn.classList.add('active');
            const meal = itineraryData.days[dayIdx].meals[mealIdx];
            const contentEl = item.querySelector('.meal-content');
            const origHTML = contentEl.innerHTML;

            contentEl.innerHTML = `
                <div class="inline-edit-overlay">
                    <div class="edit-field-group">
                        <label>Place Name</label>
                        <input type="text" data-field="place_name" value="${escapeHtml(meal.place_name || '')}">
                    </div>
                    <div class="edit-field-group">
                        <label>Cuisine</label>
                        <input type="text" data-field="cuisine" value="${escapeHtml(meal.cuisine || '')}">
                    </div>
                    <div class="edit-field-group">
                        <label>Estimated Cost (per person)</label>
                        <input type="number" data-field="estimated_cost" value="${meal.estimated_cost || 0}" min="0" step="0.01">
                    </div>
                    <div class="edit-field-group">
                        <label>Dietary Notes</label>
                        <input type="text" data-field="dietary_notes" value="${escapeHtml(meal.dietary_notes || '')}">
                    </div>
                    <div class="edit-field-group">
                        <label>Recommendation Reason</label>
                        <input type="text" data-field="recommendation_reason" value="${escapeHtml(meal.recommendation_reason || '')}">
                    </div>
                    <div class="edit-actions">
                        <button class="edit-cancel">Cancel</button>
                        <button class="edit-save">Save</button>
                    </div>
                </div>
            `;

            contentEl.querySelector('.edit-cancel').addEventListener('click', () => {
                contentEl.innerHTML = origHTML;
                btn.classList.remove('active');
            });

            contentEl.querySelector('.edit-save').addEventListener('click', async () => {
                const saveBtn = contentEl.querySelector('.edit-save');
                saveBtn.textContent = 'Saving...';
                saveBtn.disabled = true;

                const fields = contentEl.querySelectorAll('[data-field]');
                fields.forEach(f => {
                    const key = f.dataset.field;
                    if (key === 'estimated_cost') {
                        meal[key] = parseFloat(f.value) || 0;
                    } else {
                        meal[key] = f.value.trim();
                    }
                });

                const ok = await saveDaysField();
                if (ok) {
                    renderDays();
                } else {
                    contentEl.innerHTML = origHTML;
                    btn.classList.remove('active');
                    alert('Failed to save. Please try again.');
                }
            });
        });
    });
}

function reattachDaySummaryBtn(el, dayIdx, btn) {
    btn.addEventListener('click', () => {
        if (btn.classList.contains('active')) return;
        btn.classList.add('active');
        const currentVal = itineraryData.days[dayIdx].summary || '';
        const origHTML = el.innerHTML;

        el.innerHTML = `
            <textarea class="edit-field" rows="3">${escapeHtml(currentVal)}</textarea>
            <div class="edit-actions">
                <button class="edit-cancel">Cancel</button>
                <button class="edit-save">Save</button>
            </div>
        `;
        el.querySelector('.edit-field').focus();

        el.querySelector('.edit-cancel').addEventListener('click', () => {
            el.innerHTML = origHTML;
        });

        el.querySelector('.edit-save').addEventListener('click', async () => {
            const newVal = el.querySelector('.edit-field').value.trim();
            if (!newVal) return;
            const saveBtn = el.querySelector('.edit-save');
            saveBtn.textContent = 'Saving...';
            saveBtn.disabled = true;
            itineraryData.days[dayIdx].summary = newVal;
            const ok = await saveDaysField();
            if (ok) {
                el.textContent = newVal;
                const newBtn = document.createElement('button');
                newBtn.className = 'edit-btn';
                newBtn.title = 'Edit day summary';
                newBtn.appendChild(createPencilIcon());
                newBtn.style.display = 'inline-flex';
                newBtn.style.verticalAlign = 'middle';
                newBtn.style.marginLeft = '6px';
                el.appendChild(newBtn);
                reattachDaySummaryBtn(el, dayIdx, newBtn);
            } else {
                el.innerHTML = origHTML;
                alert('Failed to save. Please try again.');
            }
        });
    });
}

function renderDays() {
    const container = document.getElementById('days-container');
    container.innerHTML = itineraryData.days.map((day, dayIdx) => `
        <div class="day-card" id="day-${day.day_number}" data-day-idx="${dayIdx}">
            <div class="day-header">
                <h2><span>Day ${day.day_number}</span> — <span class="day-theme-text" data-edit="day-theme" data-day="${dayIdx}">${escapeHtml(day.theme)}</span></h2>
                <span class="day-cost">${formatCurrency(day.total_estimated_cost)}</span>
            </div>
            ${day.summary ? `<div class="day-summary" data-edit="day-summary" data-day="${dayIdx}">${escapeHtml(day.summary)}</div>` : ''}
            <div class="day-content">
                ${renderActivities(day.activities, dayIdx)}
                ${day.meals && day.meals.length > 0 ? renderMeals(day.meals, dayIdx) : ''}
            </div>
        </div>
    `).join('');

    if (!isSharedView) {
        attachDayEditButtons();
    }
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

function renderActivities(activities, dayIdx) {
    if (!activities || activities.length === 0) return '<p class="no-activities">No activities planned</p>';

    return activities.map((act, actIdx) => `
        <div class="activity-item ${act.is_hidden_gem ? 'hidden-gem' : ''}" data-day="${dayIdx}" data-act="${actIdx}">

            <div class="activity-content">
                <h4>
                    ${act.is_hidden_gem ? '<span class="gem-badge">💎 Hidden Gem</span>' : ''}
                    <span data-edit="act-name" data-day="${dayIdx}" data-act="${actIdx}">${escapeHtml(formatActivityTitle(act))}</span>
                </h4>
                <p data-edit="act-desc" data-day="${dayIdx}" data-act="${actIdx}">${escapeHtml(act.description || '')}</p>
                <div class="activity-meta">
                    <span class="activity-cost" data-edit="act-cost" data-day="${dayIdx}" data-act="${actIdx}">💰 ${formatCost(act.estimated_cost, act.cost_unknown)}</span>
                    ${act.travel_time_from_previous ? `<span>🚶 ${escapeHtml(act.travel_time_from_previous)}</span>` : ''}
                    ${act.transport_mode ? `<span>🚗 ${escapeHtml(act.transport_mode)}${act.transport_cost_unknown ? ' (Price not confirmed)' : (act.transport_cost ? ` - ${formatCurrency(act.transport_cost)}` : '')}</span>` : ''}
                    ${act.booking_required ? `<span>📋 Booking required</span>` : ''}
                    ${act.source === 'internet_search' ? `<span class="source-badge">🌐 Web</span>` : ''}
                </div>
                ${act.tips && act.tips.length > 0 ? `
                    <div class="activity-tips" data-edit="act-tips" data-day="${dayIdx}" data-act="${actIdx}">
                        <h5>Tips</h5>
                        <ul>${act.tips.map(t => `<li>${escapeHtml(t)}</li>`).join('')}</ul>
                    </div>
                ` : ''}
                ${act.warnings && act.warnings.length > 0 ? `
                    <div class="activity-warnings" data-edit="act-warnings" data-day="${dayIdx}" data-act="${actIdx}">
                        <h5>Warnings</h5>
                        <ul>${act.warnings.map(w => `<li>${escapeHtml(w)}</li>`).join('')}</ul>
                    </div>
                ` : ''}
            </div>
        </div>
    `).join('');
}

function renderMeals(meals, dayIdx) {
    const mealIcons = {
        'breakfast': '🍳',
        'lunch': '🍜',
        'dinner': '🍽️',
        'snack': '🍿'
    };

    return `
        <div class="meals-section">
            <h3>🍴 Meal Recommendations</h3>
            ${meals.map((meal, mealIdx) => `
                <div class="meal-item ${meal.is_local_delicacy ? 'local-delicacy' : ''}" data-day="${dayIdx}" data-meal="${mealIdx}">
                    <div class="meal-icon">${mealIcons[meal.meal_type] || '🍴'}</div>
                    <div class="meal-content">
                        <h4>
                            ${meal.is_local_delicacy ? '<span class="delicacy-badge">🏆 Local Delicacy</span>' : ''}
                            <span data-edit="meal-name" data-day="${dayIdx}" data-meal="${mealIdx}">${escapeHtml(toTitleCase(meal.place_name))}</span>
                        </h4>
                        <p data-edit="meal-desc" data-day="${dayIdx}" data-meal="${mealIdx}">${meal.cuisine ? escapeHtml(meal.cuisine) : ''} ${meal.dietary_notes ? `• ${escapeHtml(meal.dietary_notes)}` : ''}</p>
                        <div class="meal-meta">
                            <span data-edit="meal-cost" data-day="${dayIdx}" data-meal="${mealIdx}">💰 ${formatCost(meal.estimated_cost, meal.cost_unknown)}/person</span>
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

    if (!isSharedView) {
        attachBudgetEditButton();
    }
}

function attachBudgetEditButton() {
    const budgetCard = document.querySelector('.budget-card');
    if (!budgetCard) return;

    const existingBtn = budgetCard.querySelector(':scope > .edit-btn');
    if (existingBtn) existingBtn.remove();

    const header = budgetCard.querySelector('.card-header');
    const btn = document.createElement('button');
    btn.className = 'edit-btn';
    btn.title = 'Edit budget';
    btn.appendChild(createPencilIcon());
    header.appendChild(btn);

    const categories = [
        { key: 'food', label: 'Food & Dining', icon: '🍽️' },
        { key: 'activities', label: 'Activities', icon: '🎯' },
        { key: 'transportation', label: 'Transportation', icon: '🚗' },
        { key: 'shopping', label: 'Shopping', icon: '🛍️' },
        { key: 'miscellaneous', label: 'Miscellaneous', icon: '📦' },
        { key: 'accommodation_budget', label: 'Accommodation Budget', icon: '🏨' }
    ];

    btn.addEventListener('click', () => {
        if (btn.classList.contains('active')) return;
        btn.classList.add('active');
        const breakdown = itineraryData.budget_breakdown || {};
        const breakdownEl = document.getElementById('budget-breakdown');
        const origHTML = breakdownEl.innerHTML;

        let formHtml = '<div class="inline-edit-overlay">';
        categories.forEach(cat => {
            formHtml += `
                <div class="edit-field-group">
                    <label>${cat.icon} ${cat.label}</label>
                    <input type="number" data-budget-key="${cat.key}" value="${breakdown[cat.key] || 0}" min="0" step="0.01">
                </div>
            `;
        });
        formHtml += `
            <div class="edit-actions">
                <button class="edit-cancel">Cancel</button>
                <button class="edit-save">Save</button>
            </div>
        </div>`;

        breakdownEl.innerHTML = formHtml;

        breakdownEl.querySelector('.edit-cancel').addEventListener('click', () => {
            breakdownEl.innerHTML = origHTML;
            btn.classList.remove('active');
        });

        breakdownEl.querySelector('.edit-save').addEventListener('click', async () => {
            const saveBtn = breakdownEl.querySelector('.edit-save');
            saveBtn.textContent = 'Saving...';
            saveBtn.disabled = true;

            const inputs = breakdownEl.querySelectorAll('[data-budget-key]');
            const newBreakdown = { ...breakdown };
            inputs.forEach(input => {
                newBreakdown[input.dataset.budgetKey] = parseFloat(input.value) || 0;
            });

            const subtotal = (newBreakdown.food || 0) +
                (newBreakdown.activities || 0) +
                (newBreakdown.transportation || 0) +
                (newBreakdown.shopping || 0) +
                (newBreakdown.miscellaneous || 0);
            newBreakdown.subtotal_without_accommodation = subtotal;
            newBreakdown.total = subtotal + (newBreakdown.accommodation_budget || 0);

            itineraryData.budget_breakdown = newBreakdown;
            itineraryData.total_budget_estimate = newBreakdown.total;

            const ok = await saveItineraryField('budget_breakdown', newBreakdown);
            if (ok) {
                renderBudget();
            } else {
                breakdownEl.innerHTML = origHTML;
                btn.classList.remove('active');
                alert('Failed to save. Please try again.');
            }
        });
    });
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

    if (!isSharedView) {
        const header = document.querySelector('#tips-section .card-header');
        addListEditButton(header, 'general_tips', tips);
    }
}

function renderPacking() {
    const packingEl = document.getElementById('packing-list');
    const items = itineraryData.packing_suggestions || [];

    if (items.length === 0) {
        packingEl.innerHTML = '<li>No suggestions available</li>';
        return;
    }

    packingEl.innerHTML = items.map(item => `<li>${escapeHtml(item)}</li>`).join('');

    if (!isSharedView) {
        const header = document.querySelector('#packing-section .card-header');
        addListEditButton(header, 'packing_suggestions', items);
    }
}

function renderPhrases() {
    const phrasesEl = document.getElementById('phrases-list');
    const phrases = itineraryData.language_phrases || [];

    if (phrases.length === 0) {
        phrasesEl.innerHTML = '<li>No phrases available</li>';
        return;
    }

    phrasesEl.innerHTML = phrases.map(phrase => `<li>${escapeHtml(phrase)}</li>`).join('');

    if (!isSharedView) {
        const header = document.querySelector('#phrases-section .card-header');
        addListEditButton(header, 'language_phrases', phrases);
    }
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
    const DESKTOP_BREAKPOINT = 1025;

    function clearSticky() {
        if (isSticky) {
            isSticky = false;
            navCard.classList.remove('is-sticky');
            navCard.style.right = '';
            if (placeholder && placeholder.parentNode) {
                placeholder.parentNode.removeChild(placeholder);
                placeholder = null;
            }
        }
    }

    function handleScroll() {
        if (window.innerWidth < DESKTOP_BREAKPOINT) {
            clearSticky();
            return;
        }

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
            clearSticky();
        }

        if (isSticky) {
            navCard.style.right = (window.innerWidth - sidebarRect.right) + 'px';
        }
    }

    function handleResize() {
        if (window.innerWidth < DESKTOP_BREAKPOINT) {
            clearSticky();
            return;
        }
        if (isSticky) {
            const sidebarRect = sidebar.getBoundingClientRect();
            navCard.style.right = (window.innerWidth - sidebarRect.right) + 'px';
        }
    }

    window.addEventListener('scroll', handleScroll, { passive: true });
    window.addEventListener('resize', handleResize, { passive: true });

    handleScroll();
}

function createPencilIcon() {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('width', '14');
    svg.setAttribute('height', '14');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('fill', 'none');
    svg.setAttribute('stroke', 'currentColor');
    svg.setAttribute('stroke-width', '2');
    svg.setAttribute('stroke-linecap', 'round');
    svg.setAttribute('stroke-linejoin', 'round');

    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', 'M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7');
    svg.appendChild(path);

    const path2 = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path2.setAttribute('d', 'M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z');
    svg.appendChild(path2);

    return svg;
}

function addEditButton(element, field, type) {
    const wrapper = document.createElement('div');
    wrapper.className = 'editable-section';

    element.parentNode.insertBefore(wrapper, element);
    wrapper.appendChild(element);

    const btn = document.createElement('button');
    btn.className = 'edit-btn';
    btn.title = 'Edit';
    btn.appendChild(createPencilIcon());
    wrapper.appendChild(btn);

    btn.addEventListener('click', () => {
        if (btn.classList.contains('active')) return;
        btn.classList.add('active');

        const currentValue = itineraryData[field] || '';
        const originalHTML = element.innerHTML;

        if (type === 'textarea') {
            element.innerHTML = `
                <textarea class="edit-field" rows="4">${escapeHtml(currentValue)}</textarea>
                <div class="edit-actions">
                    <button class="edit-cancel">Cancel</button>
                    <button class="edit-save">Save</button>
                </div>
            `;
        } else {
            element.innerHTML = `
                <input type="text" class="edit-field" value="${escapeHtml(currentValue)}">
                <div class="edit-actions">
                    <button class="edit-cancel">Cancel</button>
                    <button class="edit-save">Save</button>
                </div>
            `;
        }

        const inputEl = element.querySelector('.edit-field');
        inputEl.focus();

        element.querySelector('.edit-cancel').addEventListener('click', () => {
            element.innerHTML = originalHTML;
            btn.classList.remove('active');
        });

        element.querySelector('.edit-save').addEventListener('click', async () => {
            const newValue = inputEl.value.trim();
            if (!newValue) return;

            const saveBtn = element.querySelector('.edit-save');
            saveBtn.textContent = 'Saving...';
            saveBtn.disabled = true;

            const success = await saveItineraryField(field, newValue);
            if (success) {
                itineraryData[field] = newValue;
                if (field === 'title') {
                    element.textContent = formatTitleWithDate(newValue);
                } else {
                    element.textContent = newValue;
                }
                btn.classList.remove('active');
            } else {
                element.innerHTML = originalHTML;
                btn.classList.remove('active');
                alert('Failed to save. Please try again.');
            }
        });

        inputEl.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && type !== 'textarea') {
                element.querySelector('.edit-save').click();
            }
            if (e.key === 'Escape') {
                element.querySelector('.edit-cancel').click();
            }
        });
    });
}

function addListEditButton(headerEl, field, items) {
    const existingBtn = headerEl.querySelector('.edit-btn');
    if (existingBtn) existingBtn.remove();

    const btn = document.createElement('button');
    btn.className = 'edit-btn';
    btn.title = 'Edit';
    btn.appendChild(createPencilIcon());
    headerEl.appendChild(btn);

    btn.addEventListener('click', () => {
        if (btn.classList.contains('active')) return;
        btn.classList.add('active');

        const listElId = {
            'general_tips': 'general-tips',
            'packing_suggestions': 'packing-list',
            'language_phrases': 'phrases-list'
        }[field];

        const listEl = document.getElementById(listElId);
        const originalHTML = listEl.innerHTML;
        const currentItems = [...(itineraryData[field] || [])];

        let editHTML = currentItems.map((item, i) => `
            <div class="edit-list-item" data-index="${i}">
                <input type="text" value="${escapeHtml(item)}">
                <button class="edit-list-remove" title="Remove">×</button>
            </div>
        `).join('');

        editHTML += `
            <button class="edit-list-add">+ Add Item</button>
            <div class="edit-actions">
                <button class="edit-cancel">Cancel</button>
                <button class="edit-save">Save</button>
            </div>
        `;

        listEl.innerHTML = editHTML;

        listEl.querySelector('.edit-list-add').addEventListener('click', () => {
            const newItem = document.createElement('div');
            newItem.className = 'edit-list-item';
            newItem.innerHTML = `
                <input type="text" value="" placeholder="New item...">
                <button class="edit-list-remove" title="Remove">×</button>
            `;
            listEl.querySelector('.edit-list-add').before(newItem);
            newItem.querySelector('input').focus();

            newItem.querySelector('.edit-list-remove').addEventListener('click', () => {
                newItem.remove();
            });
        });

        listEl.querySelectorAll('.edit-list-remove').forEach(removeBtn => {
            removeBtn.addEventListener('click', () => {
                removeBtn.parentElement.remove();
            });
        });

        listEl.querySelector('.edit-cancel').addEventListener('click', () => {
            listEl.innerHTML = originalHTML;
            btn.classList.remove('active');
        });

        listEl.querySelector('.edit-save').addEventListener('click', async () => {
            const inputs = listEl.querySelectorAll('.edit-list-item input');
            const newItems = Array.from(inputs)
                .map(input => input.value.trim())
                .filter(v => v.length > 0);

            if (newItems.length === 0) return;

            const saveBtn = listEl.querySelector('.edit-save');
            saveBtn.textContent = 'Saving...';
            saveBtn.disabled = true;

            const success = await saveItineraryField(field, newItems);
            if (success) {
                itineraryData[field] = newItems;
                listEl.innerHTML = newItems.map(item => `<li>${escapeHtml(item)}</li>`).join('');
                btn.classList.remove('active');
            } else {
                listEl.innerHTML = originalHTML;
                btn.classList.remove('active');
                alert('Failed to save. Please try again.');
            }
        });
    });
}

async function saveItineraryField(field, value) {
    try {
        const token = localStorage.getItem('access_token');
        const body = {};
        body[field] = value;

        const response = await fetch(`/api/itinerary/${itineraryData.id}`, {
            method: 'PATCH',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(body)
        });

        return response.ok;
    } catch (error) {
        console.error('Save failed:', error);
        return false;
    }
}

function initChat() {
    const widget = document.getElementById('chat-widget');
    const fab = document.getElementById('chat-fab');
    const closeBtn = document.getElementById('chat-close');
    const overlay = document.getElementById('chat-panel-overlay');
    const sendBtn = document.getElementById('chat-send');
    const input = document.getElementById('chat-input');

    if (!widget) return;
    widget.style.display = 'block';

    function isMobile() {
        return window.innerWidth <= 600;
    }

    function openPanel() {
        widget.classList.add('open');
        if (isMobile()) document.body.style.overflow = 'hidden';
        input.focus();
    }

    function closePanel() {
        widget.classList.remove('open');
        document.body.style.overflow = '';
    }

    fab.addEventListener('click', () => {
        if (widget.classList.contains('open')) {
            closePanel();
        } else {
            openPanel();
        }
    });

    closeBtn.addEventListener('click', closePanel);
    overlay.addEventListener('click', closePanel);

    sendBtn.addEventListener('click', () => sendChatMessage());

    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendChatMessage();
        }
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && widget.classList.contains('open')) {
            closePanel();
        }
    });

    loadChatHistory();
}

async function loadChatHistory() {
    if (!itineraryData) return;
    const token = localStorage.getItem('access_token');
    try {
        const response = await fetch(`/api/itinerary/${itineraryData.id}/chat/history`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) return;
        const data = await response.json();
        if (!data.history || data.history.length === 0) return;

        const messagesEl = document.getElementById('chat-messages');
        chatHistory = data.history;

        chatHistory.forEach(msg => {
            const el = document.createElement('div');
            el.className = `chat-message ${msg.role === 'user' ? 'user' : 'assistant'}`;
            el.innerHTML = `<div class="chat-bubble">${msg.role === 'user' ? escapeHtml(msg.content) : formatChatResponse(msg.content)}</div>`;
            messagesEl.appendChild(el);
        });
        messagesEl.scrollTop = messagesEl.scrollHeight;
    } catch (e) {
        // silently fail - chat will work without history
    }
}

async function sendChatMessage() {
    const input = document.getElementById('chat-input');
    const messagesEl = document.getElementById('chat-messages');
    const sendBtn = document.getElementById('chat-send');
    const message = input.value.trim();

    if (!message) return;

    input.value = '';
    sendBtn.disabled = true;

    const userMsgEl = document.createElement('div');
    userMsgEl.className = 'chat-message user';
    userMsgEl.innerHTML = `<div class="chat-bubble">${escapeHtml(message)}</div>`;
    messagesEl.appendChild(userMsgEl);

    chatHistory.push({ role: 'user', content: message });

    const typingEl = document.createElement('div');
    typingEl.className = 'chat-message assistant';
    typingEl.innerHTML = `<div class="chat-bubble chat-typing"><span></span><span></span><span></span></div>`;
    messagesEl.appendChild(typingEl);

    messagesEl.scrollTop = messagesEl.scrollHeight;

    try {
        const token = localStorage.getItem('access_token');
        const response = await fetch(`/api/itinerary/${itineraryData.id}/chat`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message,
                history: chatHistory.slice(-10)
            })
        });

        typingEl.remove();

        if (response.ok) {
            const data = await response.json();
            const assistantMsg = data.response;

            chatHistory.push({ role: 'assistant', content: assistantMsg });

            const assistantMsgEl = document.createElement('div');
            assistantMsgEl.className = 'chat-message assistant';
            assistantMsgEl.innerHTML = `<div class="chat-bubble">${formatChatResponse(assistantMsg)}</div>`;
            messagesEl.appendChild(assistantMsgEl);
        } else {
            const errorMsgEl = document.createElement('div');
            errorMsgEl.className = 'chat-message assistant';
            errorMsgEl.innerHTML = `<div class="chat-bubble">Sorry, I couldn't process that request. Please try again.</div>`;
            messagesEl.appendChild(errorMsgEl);
        }
    } catch (error) {
        typingEl.remove();
        const errorMsgEl = document.createElement('div');
        errorMsgEl.className = 'chat-message assistant';
        errorMsgEl.innerHTML = `<div class="chat-bubble">Connection error. Please check your internet and try again.</div>`;
        messagesEl.appendChild(errorMsgEl);
    }

    messagesEl.scrollTop = messagesEl.scrollHeight;
    sendBtn.disabled = false;
    input.focus();
}

function formatChatResponse(text) {
    let formatted = escapeHtml(text);
    formatted = formatted.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    formatted = formatted.replace(/\*(.+?)\*/g, '<em>$1</em>');
    formatted = formatted.replace(/\n/g, '<br>');
    formatted = formatted.replace(
        /(https?:\/\/[^\s<]+)/g,
        '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>'
    );
    return formatted;
}
