let currentUser = null;
let generatingItineraryId = null;
let pollInterval = null;

document.addEventListener('DOMContentLoaded', async function() {
    currentUser = await checkAuth();
    if (!currentUser) return;
    
    displayUserInfo();
    initLogout();
    initUrlInputs();
    initForm();
    loadItineraries();
});

async function checkAuth() {
    const token = localStorage.getItem('access_token');
    if (!token) {
        window.location.href = '/login';
        return null;
    }

    try {
        const response = await fetch('/api/auth/me', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (!response.ok) {
            localStorage.removeItem('access_token');
            window.location.href = '/login';
            return null;
        }
        
        return await response.json();
    } catch (error) {
        window.location.href = '/login';
        return null;
    }
}

function displayUserInfo() {
    document.getElementById('user-email').textContent = currentUser.email;
}

function initLogout() {
    document.getElementById('logout-btn').addEventListener('click', async function() {
        try {
            await fetch('/api/auth/logout', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` }
            });
        } catch (e) {}
        
        localStorage.removeItem('access_token');
        window.location.href = '/login';
    });
}

function initUrlInputs() {
    const addBtn = document.getElementById('add-url-btn');
    const urlInputsContainer = document.getElementById('url-inputs');
    
    addBtn.addEventListener('click', function() {
        const inputs = urlInputsContainer.querySelectorAll('.url-input-group');
        if (inputs.length >= 5) return;
        
        const newInput = createUrlInput();
        urlInputsContainer.appendChild(newInput);
        updateAddButtonState();
        updateRemoveButtons();
    });
    
    urlInputsContainer.querySelector('.youtube-url').addEventListener('blur', validateUrl);
    updateRemoveButtons();
}

function createUrlInput() {
    const div = document.createElement('div');
    div.className = 'url-input-group';
    div.innerHTML = `
        <input type="url" class="youtube-url" placeholder="https://youtube.com/watch?v=..." required>
        <span class="url-status"></span>
        <button type="button" class="btn-remove-url">×</button>
    `;
    
    div.querySelector('.youtube-url').addEventListener('blur', validateUrl);
    div.querySelector('.btn-remove-url').addEventListener('click', function() {
        div.remove();
        updateAddButtonState();
        updateRemoveButtons();
    });
    
    return div;
}

function updateAddButtonState() {
    const addBtn = document.getElementById('add-url-btn');
    const inputs = document.querySelectorAll('.url-input-group');
    addBtn.disabled = inputs.length >= 5;
}

function updateRemoveButtons() {
    const inputs = document.querySelectorAll('.url-input-group');
    inputs.forEach((group, index) => {
        const removeBtn = group.querySelector('.btn-remove-url');
        removeBtn.style.display = inputs.length > 1 ? 'block' : 'none';
    });
}

async function validateUrl(event) {
    const input = event.target;
    const status = input.nextElementSibling;
    const url = input.value.trim();
    
    if (!url) {
        status.className = 'url-status';
        return;
    }
    
    status.className = 'url-status loading';
    
    try {
        const response = await fetch('/api/youtube/validate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            },
            body: JSON.stringify({ url })
        });
        
        const data = await response.json();
        
        if (data.valid) {
            status.className = 'url-status valid';
            input.title = data.title;
        } else {
            status.className = 'url-status invalid';
            input.title = data.error || 'Invalid URL';
        }
    } catch (error) {
        status.className = 'url-status invalid';
    }
}

function initForm() {
    const form = document.getElementById('generate-form');
    form.addEventListener('submit', handleGenerate);
}

async function handleGenerate(event) {
    event.preventDefault();
    
    const btn = document.getElementById('generate-btn');
    clearError();
    
    const urls = Array.from(document.querySelectorAll('.youtube-url'))
        .map(input => input.value.trim())
        .filter(url => url);
    
    if (urls.length === 0) {
        showError('Please add at least one YouTube URL');
        return;
    }
    
    const preferences = {
        budget: parseFloat(document.getElementById('budget').value),
        currency: document.getElementById('currency').value,
        trip_duration_days: parseInt(document.getElementById('trip-duration').value),
        trip_type: document.getElementById('trip-type').value,
        num_travelers: parseInt(document.getElementById('num-travelers').value),
        activity_style: document.getElementById('activity-style').value,
        accommodation_preference: document.getElementById('accommodation').value,
        start_date: document.getElementById('start-date').value || null,
        dietary_restrictions: Array.from(document.querySelectorAll('input[name="dietary"]:checked'))
            .map(cb => cb.value),
        mobility_constraints: document.getElementById('mobility').value || null,
        must_visit_places: document.getElementById('must-visit').value
            ? document.getElementById('must-visit').value.split(',').map(s => s.trim())
            : [],
        additional_notes: document.getElementById('additional-notes').value || null
    };
    
    if (!preferences.budget || !preferences.trip_duration_days || !preferences.trip_type || !preferences.num_travelers) {
        showError('Please fill in all required fields');
        return;
    }
    
    setLoading(btn, true);
    showModal();
    
    try {
        const response = await fetch('/api/itinerary/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            },
            body: JSON.stringify({
                youtube_urls: urls,
                preferences: preferences
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            generatingItineraryId = data.itinerary_id;
            startPolling();
        } else {
            hideModal();
            showError(data.detail || 'Failed to start generation');
            setLoading(btn, false);
        }
    } catch (error) {
        hideModal();
        showError('Connection error. Please try again.');
        setLoading(btn, false);
    }
}

function startPolling() {
    if (pollInterval) clearInterval(pollInterval);
    
    pollInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/itinerary/status/${generatingItineraryId}`, {
                headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` }
            });
            
            const data = await response.json();
            
            updateProgress(data.progress || 0, data.message);
            
            if (data.status === 'completed') {
                clearInterval(pollInterval);
                pollInterval = null;
                window.location.href = `/itinerary/${generatingItineraryId}`;
            } else if (data.status === 'failed') {
                clearInterval(pollInterval);
                pollInterval = null;
                hideModal();
                showError(data.message || 'Generation failed. Please try again.');
                setLoading(document.getElementById('generate-btn'), false);
            }
        } catch (error) {
            clearInterval(pollInterval);
            pollInterval = null;
            hideModal();
            showError('Connection error. Please try again.');
            setLoading(document.getElementById('generate-btn'), false);
        }
    }, 2000);
}

function updateProgress(progress, message) {
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    
    progressFill.style.width = `${progress}%`;
    progressText.textContent = message || `${progress}% complete`;
    
    const steps = ['step-1', 'step-2', 'step-3', 'step-4'];
    const thresholds = [10, 40, 75, 90];
    
    steps.forEach((stepId, index) => {
        const step = document.getElementById(stepId);
        if (progress >= thresholds[index]) {
            if (index === steps.length - 1 || progress < thresholds[index + 1]) {
                step.className = 'progress-step active';
            } else {
                step.className = 'progress-step completed';
            }
        } else {
            step.className = 'progress-step';
        }
    });
}

function showModal() {
    document.getElementById('progress-modal').classList.add('show');
    updateProgress(0, 'Starting...');
}

function hideModal() {
    document.getElementById('progress-modal').classList.remove('show');
}

async function loadItineraries() {
    const container = document.getElementById('itinerary-list');
    
    try {
        const response = await fetch('/api/itinerary/list', {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` }
        });
        
        if (!response.ok) throw new Error('Failed to load');
        
        const itineraries = await response.json();
        
        if (itineraries.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                        <polyline points="14 2 14 8 20 8"></polyline>
                    </svg>
                    <p>No itineraries yet.<br>Create your first one!</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = itineraries.map(it => `
            <div class="itinerary-item" onclick="window.location.href='/itinerary/${it.id}'">
                <h4>${escapeHtml(it.title)}</h4>
                <p>${escapeHtml(it.destination)} • ${it.total_days} days</p>
                <div class="itinerary-meta">
                    <span>💰 ${it.total_budget_estimate.toLocaleString()} ${it.currency}</span>
                    <span>📅 ${formatDate(it.created_at)}</span>
                </div>
            </div>
        `).join('');
    } catch (error) {
        container.innerHTML = `
            <div class="empty-state">
                <p>Failed to load itineraries</p>
            </div>
        `;
    }
}

function setLoading(button, isLoading) {
    const btnText = button.querySelector('.btn-text');
    const btnLoader = button.querySelector('.btn-loader');
    const btnIcon = button.querySelector('svg:not(.spinner)');

    if (isLoading) {
        button.disabled = true;
        if (btnText) btnText.style.display = 'none';
        if (btnIcon) btnIcon.style.display = 'none';
        if (btnLoader) btnLoader.style.display = 'flex';
    } else {
        button.disabled = false;
        if (btnText) btnText.style.display = 'inline';
        if (btnIcon) btnIcon.style.display = 'inline';
        if (btnLoader) btnLoader.style.display = 'none';
    }
}

function showError(message) {
    const errorEl = document.getElementById('error-message');
    errorEl.textContent = message;
    errorEl.classList.add('show');
    errorEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function clearError() {
    document.getElementById('error-message').classList.remove('show');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { 
        month: 'short', 
        day: 'numeric',
        year: 'numeric'
    });
}
