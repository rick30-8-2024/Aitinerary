(function () {
    const API_BASE = '';
    let accessToken = localStorage.getItem('access_token');
    let currentStep = 1;
    const totalSteps = 3;
    let itineraries = [];
    let videoData = [];
    const MAX_VIDEOS = 5;
    let pollingInterval = null;
    const POLLING_INTERVAL_MS = 5000;
    let updatePillFn = null;

    function initPageLoader() {
        const shaderFrame = document.querySelector('.shader-frame');
        const body = document.body;
        let shaderLoaded = false;
        let minTimeElapsed = false;
        
        const minLoadTime = 800;
        
        setTimeout(() => {
            minTimeElapsed = true;
            tryRevealPage();
        }, minLoadTime);
        
        function tryRevealPage() {
            if (shaderLoaded && minTimeElapsed) {
                body.classList.remove('loading');
            }
        }
        
        if (shaderFrame) {
            shaderFrame.addEventListener('load', function() {
                setTimeout(() => {
                    shaderLoaded = true;
                    tryRevealPage();
                }, 100);
            });
            
            setTimeout(() => {
                if (!shaderLoaded) {
                    shaderLoaded = true;
                    tryRevealPage();
                }
            }, 5000);
        } else {
            shaderLoaded = true;
            tryRevealPage();
        }
    }

    async function verifyAndInit() {
        if (!accessToken) {
            window.location.href = '/login';
            return;
        }

        try {
            const response = await fetch(`${API_BASE}/api/auth/verify`, {
                headers: { 'Authorization': `Bearer ${accessToken}` }
            });
            
            const data = await response.json();
            
            if (!response.ok || !data.valid) {
                localStorage.removeItem('access_token');
                window.location.href = '/login';
                return;
            }
            
            init();
        } catch (error) {
            console.error('Auth verification failed:', error);
            localStorage.removeItem('access_token');
            window.location.href = '/login';
        }
    }

    async function init() {
        await loadUserInfo();
        setupTabSwitching();
        setupLogoutModal();
        setupDeleteModal();
        setupWizardNavigation();
        setupVideoCards();
        setupAddVideoModal();
        setupFormSubmission();
        setupSuccessModal();
        setupSearch();
        loadItineraries();
    }

    async function loadUserInfo() {
        try {
            const res = await fetch(`${API_BASE}/api/auth/me`, {
                headers: { 'Authorization': `Bearer ${accessToken}` }
            });
            if (!res.ok) throw new Error('Failed to fetch user info');
            const data = await res.json();
            document.getElementById('user-name').textContent = data.name || data.email.split('@')[0];
        } catch (err) {
            console.error(err);
            document.getElementById('user-name').textContent = 'User';
        }
    }

    function setupTabSwitching() {
        const island = document.querySelector('.floating-island');
        const tabs = document.querySelectorAll('.island-tab');
        const createSection = document.getElementById('section-create');
        const historySection = document.getElementById('section-history');

        const pill = document.createElement('div');
        pill.className = 'island-pill';
        island.insertBefore(pill, island.firstChild);

        const ICON_SIZE = 18;
        const TAB_PADDING_H = 14;
        const TAB_GAP = 4;
        const COLLAPSED_TAB_WIDTH = ICON_SIZE + (TAB_PADDING_H * 2);
        
        let expandedWidths = { create: 0, history: 0 };
        
        function measureExpandedWidths() {
            tabs.forEach(tab => {
                const span = tab.querySelector('span');
                const section = tab.dataset.section;
                const wasActive = tab.classList.contains('active');
                
                span.style.cssText = 'transition: none !important; max-width: 150px !important; opacity: 1 !important; margin-left: 4px !important;';
                if (!wasActive) tab.classList.add('active');
                
                void tab.offsetWidth;
                
                expandedWidths[section] = tab.getBoundingClientRect().width;
                
                span.style.cssText = '';
                if (!wasActive) tab.classList.remove('active');
            });
        }

        function updatePill(animate = true) {
            const activeTab = document.querySelector('.island-tab.active');
            if (!activeTab) return;

            const section = activeTab.dataset.section;
            const width = expandedWidths[section] || 150;
            
            let offsetX = 0;
            if (section === 'history') {
                offsetX = COLLAPSED_TAB_WIDTH + TAB_GAP;
            }

            if (!animate) {
                pill.style.transition = 'none';
            }
            
            pill.style.transform = `translateX(${offsetX}px)`;
            pill.style.width = `${width}px`;

            if (!animate) {
                void pill.offsetWidth;
                pill.style.transition = '';
            }
        }

        updatePillFn = updatePill;

        measureExpandedWidths();
        updatePill(false);

        if (document.fonts && document.fonts.ready) {
            document.fonts.ready.then(() => {
                measureExpandedWidths();
                updatePill(false);
            });
        } else {
            setTimeout(() => {
                measureExpandedWidths();
                updatePill(false);
            }, 100);
        }

        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                if (tab.classList.contains('active')) return;
                
                tabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');

                updatePill(true);

                const section = tab.dataset.section;
                if (section === 'create') {
                    createSection.classList.add('active');
                    historySection.classList.remove('active');
                    stopPolling();
                } else {
                    createSection.classList.remove('active');
                    historySection.classList.add('active');
                    loadItineraries();
                }
            });
        });

        window.addEventListener('resize', () => {
            measureExpandedWidths();
            updatePill(false);
        });
    }

    function setupLogoutModal() {
        const logoutBtn = document.getElementById('logout-btn');
        const logoutModal = document.getElementById('logout-modal');
        const cancelLogout = document.getElementById('cancel-logout');
        const confirmLogout = document.getElementById('confirm-logout');

        logoutBtn.addEventListener('click', () => {
            logoutModal.classList.add('show');
        });

        cancelLogout.addEventListener('click', () => {
            logoutModal.classList.remove('show');
        });

        confirmLogout.addEventListener('click', () => {
            localStorage.removeItem('access_token');
            window.location.href = '/login';
        });

        logoutModal.addEventListener('click', (e) => {
            if (e.target === logoutModal) {
                logoutModal.classList.remove('show');
            }
        });
    }

    let deleteTargetId = null;

    function setupDeleteModal() {
        const deleteModal = document.getElementById('delete-modal');
        const cancelDelete = document.getElementById('cancel-delete');
        const confirmDelete = document.getElementById('confirm-delete');

        cancelDelete.addEventListener('click', () => {
            deleteModal.classList.remove('show');
            deleteTargetId = null;
        });

        confirmDelete.addEventListener('click', async () => {
            if (!deleteTargetId) return;
            
            const btnText = confirmDelete.querySelector('.btn-text');
            const btnLoader = confirmDelete.querySelector('.btn-loader');
            
            confirmDelete.disabled = true;
            cancelDelete.disabled = true;
            btnText.style.display = 'none';
            btnLoader.style.display = 'flex';
            
            try {
                const res = await fetch(`${API_BASE}/api/itinerary/${deleteTargetId}`, {
                    method: 'DELETE',
                    headers: { 'Authorization': `Bearer ${accessToken}` }
                });

                if (!res.ok) {
                    throw new Error('Failed to delete itinerary');
                }

                const card = document.querySelector(`.itinerary-card[data-id="${deleteTargetId}"]`);
                if (card) {
                    card.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                    card.style.opacity = '0';
                    card.style.transform = 'scale(0.9)';
                    setTimeout(() => card.remove(), 300);
                }

                itineraries = itineraries.filter(it => it.id !== deleteTargetId);

                if (itineraries.length === 0) {
                    const emptyState = document.getElementById('empty-history');
                    emptyState.style.display = 'block';
                    emptyState.querySelector('p').innerHTML = 'No itineraries yet.<br>Create your first one!';
                }

            } catch (err) {
                console.error('Delete failed:', err);
                alert('Failed to delete itinerary. Please try again.');
            } finally {
                confirmDelete.disabled = false;
                cancelDelete.disabled = false;
                btnText.style.display = 'inline';
                btnLoader.style.display = 'none';
                deleteModal.classList.remove('show');
                deleteTargetId = null;
            }
        });

        deleteModal.addEventListener('click', (e) => {
            if (e.target === deleteModal) {
                deleteModal.classList.remove('show');
                deleteTargetId = null;
            }
        });
    }

    function showDeleteModal(id) {
        deleteTargetId = id;
        document.getElementById('delete-modal').classList.add('show');
    }

    function setupWizardNavigation() {
        const prevBtn = document.getElementById('btn-prev');
        const nextBtn = document.getElementById('btn-next');
        const generateBtn = document.getElementById('generate-btn');

        prevBtn.addEventListener('click', () => {
            if (currentStep > 1) {
                goToStep(currentStep - 1);
            }
        });

        nextBtn.addEventListener('click', () => {
            if (validateCurrentStep()) {
                goToStep(currentStep + 1);
            }
        });
    }

    function goToStep(step) {
        const panels = document.querySelectorAll('.wizard-panel');
        const steps = document.querySelectorAll('.wizard-step');
        const prevBtn = document.getElementById('btn-prev');
        const nextBtn = document.getElementById('btn-next');
        const generateBtn = document.getElementById('generate-btn');

        panels.forEach(p => p.classList.remove('active'));
        document.querySelector(`.wizard-panel[data-step="${step}"]`).classList.add('active');

        steps.forEach((s, i) => {
            s.classList.remove('active', 'completed');
            if (i + 1 < step) s.classList.add('completed');
            if (i + 1 === step) s.classList.add('active');
        });

        currentStep = step;

        prevBtn.style.visibility = step === 1 ? 'hidden' : 'visible';

        if (step === totalSteps) {
            nextBtn.style.display = 'none';
            generateBtn.style.display = 'flex';
        } else {
            nextBtn.style.display = 'flex';
            generateBtn.style.display = 'none';
        }
    }

    function validateCurrentStep() {
        const errorEl = document.getElementById('error-message');
        errorEl.classList.remove('show');
        errorEl.textContent = '';

        document.querySelectorAll('.error').forEach(el => el.classList.remove('error'));

        if (currentStep === 1) {
            const validVideos = videoData.filter(v => v.status === 'completed');
            if (videoData.length === 0) {
                errorEl.textContent = 'Please add at least one YouTube video.';
                errorEl.classList.add('show');
                return false;
            }
            if (validVideos.length === 0) {
                errorEl.textContent = 'Please wait for at least one video to finish processing or try different videos.';
                errorEl.classList.add('show');
                return false;
            }
        }

        if (currentStep === 2) {
            const requiredFields = ['destination-name', 'budget', 'trip-duration', 'num-travelers'];
            let allValid = true;

            requiredFields.forEach(fieldId => {
                const field = document.getElementById(fieldId);
                if (!field.value || field.value.trim() === '') {
                    field.classList.add('error');
                    allValid = false;
                }
            });

            if (!allValid) {
                errorEl.textContent = 'Please fill in all required fields including your destination.';
                errorEl.classList.add('show');
                return false;
            }
        }

        return true;
    }

    function isValidYouTubeUrl(url) {
        const patterns = [
            /^(https?:\/\/)?(www\.)?youtube\.com\/watch\?v=[\w-]+/,
            /^(https?:\/\/)?(www\.)?youtu\.be\/[\w-]+/,
            /^(https?:\/\/)?(www\.)?youtube\.com\/embed\/[\w-]+/,
            /^(https?:\/\/)?(www\.)?youtube\.com\/shorts\/[\w-]+/
        ];
        return patterns.some(p => p.test(url));
    }

    function setupVideoCards() {
        const addBtn = document.getElementById('add-video-btn');
        
        addBtn.addEventListener('click', () => {
            if (videoUrls.length >= MAX_VIDEOS) return;
            document.getElementById('add-video-modal').classList.add('show');
            document.getElementById('video-url-input').focus();
        });

        renderVideoCards();
    }

    function setupAddVideoModal() {
        const modal = document.getElementById('add-video-modal');
        const input = document.getElementById('video-url-input');
        const hint = document.getElementById('video-url-hint');
        const cancelBtn = document.getElementById('cancel-add-video');
        const confirmBtn = document.getElementById('confirm-add-video');
        let validationTimeout;

        cancelBtn.addEventListener('click', () => {
            closeAddVideoModal();
        });

        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeAddVideoModal();
            }
        });

        input.addEventListener('input', () => {
            clearTimeout(validationTimeout);
            const url = input.value.trim();

            if (!url) {
                input.className = '';
                hint.className = 'hint';
                hint.textContent = 'Paste a YouTube video link';
                confirmBtn.disabled = true;
                return;
            }

            validationTimeout = setTimeout(() => {
                if (isValidYouTubeUrl(url)) {
                    const videoId = extractVideoId(url);
                    if (videoData.some(v => v.id === videoId)) {
                        input.className = 'invalid';
                        hint.className = 'hint error';
                        hint.textContent = 'This video has already been added';
                        confirmBtn.disabled = true;
                    } else {
                        input.className = 'valid';
                        hint.className = 'hint success';
                        hint.textContent = 'Valid YouTube URL';
                        confirmBtn.disabled = false;
                    }
                } else {
                    input.className = 'invalid';
                    hint.className = 'hint error';
                    hint.textContent = 'Please enter a valid YouTube URL';
                    confirmBtn.disabled = true;
                }
            }, 300);
        });

        confirmBtn.addEventListener('click', async () => {
            const url = input.value.trim();
            if (!url || !isValidYouTubeUrl(url)) return;

            const videoId = extractVideoId(url);
            if (videoData.some(v => v.id === videoId)) return;

            const btnText = confirmBtn.querySelector('.btn-text');
            const btnLoader = confirmBtn.querySelector('.btn-loader');

            confirmBtn.disabled = true;
            btnText.style.display = 'none';
            btnLoader.style.display = 'flex';

            try {
                const thumbnail = getYouTubeThumbnail(videoId);
                
                const videoEntry = {
                    id: videoId,
                    url: url,
                    thumbnail: thumbnail,
                    status: 'loading',
                    title: null,
                    transcript: null,
                    error: null
                };

                videoData.push(videoEntry);
                renderVideoCards();
                closeAddVideoModal();

                fetchVideoTranscript(videoEntry);

            } catch (err) {
                console.error('Error adding video:', err);
                hint.className = 'hint error';
                hint.textContent = 'Failed to add video. Please try again.';
            } finally {
                confirmBtn.disabled = false;
                btnText.style.display = 'inline';
                btnLoader.style.display = 'none';
            }
        });

        function closeAddVideoModal() {
            modal.classList.remove('show');
            input.value = '';
            input.className = '';
            hint.className = 'hint';
            hint.textContent = 'Paste a YouTube video link';
            confirmBtn.disabled = true;
        }
    }

    function extractVideoId(url) {
        const patterns = [
            /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/shorts\/)([a-zA-Z0-9_-]{11})/
        ];
        for (const pattern of patterns) {
            const match = url.match(pattern);
            if (match) return match[1];
        }
        return null;
    }

    function getYouTubeThumbnail(videoId) {
        return `https://img.youtube.com/vi/${videoId}/mqdefault.jpg`;
    }

    async function fetchVideoTranscript(videoEntry) {
        try {
            const response = await fetch(`${API_BASE}/api/youtube/process`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${accessToken}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    url: videoEntry.url,
                    languages: ['en']
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to process video');
            }

            const data = await response.json();
            videoEntry.status = 'completed';
            videoEntry.title = data.metadata.title;
            videoEntry.transcript = data.transcript;
            videoEntry.metadata = data.metadata;
            
        } catch (error) {
            console.error('Error fetching transcript:', error);
            videoEntry.status = 'error';
            videoEntry.error = error.message;
        }
        
        renderVideoCards();
    }

    function renderVideoCards() {
        const grid = document.getElementById('video-cards-grid');
        const addBtn = document.getElementById('add-video-btn');

        grid.innerHTML = '';

        videoData.forEach((video, index) => {
            const card = document.createElement('div');
            let cardClass = 'video-card video-card-thumbnail';
            let statusOverlay = '';
            let clickable = true;
            
            if (video.status === 'loading') {
                cardClass += ' loading';
                statusOverlay = `
                    <div class="video-status-badge loading">
                        <div class="spinner"></div>
                    </div>
                `;
                clickable = false;
            } else if (video.status === 'error') {
                cardClass += ' error';
                statusOverlay = `
                    <div class="video-status-badge error" title="${video.error}">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                            <line x1="18" y1="6" x2="6" y2="18"></line>
                            <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                    </div>
                `;
                clickable = false;
            } else if (video.status === 'completed') {
                statusOverlay = `
                    <div class="video-status-badge success">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                            <polyline points="20 6 9 17 4 12"></polyline>
                        </svg>
                    </div>
                `;
            }

            card.className = cardClass;
            card.innerHTML = `
                <img src="${video.thumbnail}" alt="Video thumbnail" onerror="this.src='https://via.placeholder.com/320x180?text=No+Thumbnail'">
                <div class="video-card-overlay"></div>
                ${statusOverlay}
                <button type="button" class="video-card-remove" data-index="${index}">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                </button>
                <div class="video-card-play">
                    <svg viewBox="0 0 24 24" fill="currentColor">
                        <polygon points="5 3 19 12 5 21 5 3"></polygon>
                    </svg>
                </div>
            `;
            grid.appendChild(card);

            card.querySelector('.video-card-remove').addEventListener('click', (e) => {
                e.stopPropagation();
                removeVideo(index);
            });

            if (clickable) {
                card.addEventListener('click', () => {
                    window.open(`https://www.youtube.com/watch?v=${video.id}`, '_blank');
                });
            }
        });

        if (videoData.length < MAX_VIDEOS) {
            const addCard = document.createElement('button');
            addCard.type = 'button';
            addCard.className = 'video-card video-card-add';
            addCard.id = 'add-video-btn';
            addCard.innerHTML = `
                <div class="video-card-add-content">
                    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="12" y1="5" x2="12" y2="19"></line>
                        <line x1="5" y1="12" x2="19" y2="12"></line>
                    </svg>
                    <span>Add Video</span>
                </div>
            `;
            grid.appendChild(addCard);

            addCard.addEventListener('click', () => {
                document.getElementById('add-video-modal').classList.add('show');
                document.getElementById('video-url-input').focus();
            });
        }
    }

    function removeVideo(index) {
        videoData.splice(index, 1);
        renderVideoCards();
    }

    function setupFormSubmission() {
        const generateBtn = document.getElementById('generate-btn');
        const successModal = document.getElementById('success-modal');

        generateBtn.addEventListener('click', async () => {
            if (!validateCurrentStep()) return;

            const validVideos = videoData.filter(v => v.status === 'completed');
            if (validVideos.length === 0) {
                const errorEl = document.getElementById('error-message');
                if (videoData.length === 1 && videoData[0].status === 'error') {
                    errorEl.textContent = 'Sorry, the video could not be processed. Please try with a different video or check if the video has transcripts available.';
                } else if (videoData.some(v => v.status === 'error')) {
                    errorEl.textContent = 'Some videos failed to process. Please remove failed videos or add working ones to proceed.';
                } else {
                    errorEl.textContent = 'Please wait for videos to finish processing before generating your itinerary.';
                }
                errorEl.classList.add('show');
                return;
            }

            const urls = validVideos.map(v => v.url);

            const dietary = Array.from(document.querySelectorAll('input[name="dietary"]:checked'))
                .map(c => c.value);

            const mustVisit = document.getElementById('must-visit').value
                .split(',')
                .map(s => s.trim())
                .filter(s => s);

            const destinationName = document.getElementById('destination-name').value.trim();

            const payload = {
                youtube_urls: urls,
                destination_name: destinationName || null,
                preferences: {
                    budget: parseFloat(document.getElementById('budget').value) || 1000,
                    currency: document.getElementById('currency').value,
                    trip_duration_days: parseInt(document.getElementById('trip-duration').value) || 7,
                    num_travelers: parseInt(document.getElementById('num-travelers').value) || 1,
                    activity_style: document.getElementById('activity-style').value,
                    accommodation_preference: document.getElementById('accommodation').value,
                    dietary_restrictions: dietary,
                    mobility_constraints: document.getElementById('mobility').value || null,
                    must_visit_places: mustVisit,
                    start_date: document.getElementById('start-date').value || null,
                    additional_notes: document.getElementById('additional-notes').value || null
                }
            };

            generateBtn.disabled = true;
            generateBtn.querySelector('.btn-text').style.display = 'none';
            generateBtn.querySelector('.btn-loader').style.display = 'flex';

            try {
                const res = await fetch(`${API_BASE}/api/itinerary/generate`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${accessToken}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(payload)
                });

                if (!res.ok) {
                    const err = await res.json();
                    throw new Error(err.detail || 'Failed to generate itinerary');
                }

                successModal.classList.add('show');
                resetForm();

            } catch (err) {
                const errorEl = document.getElementById('error-message');
                errorEl.textContent = err.message;
                errorEl.classList.add('show');
            } finally {
                generateBtn.disabled = false;
                generateBtn.querySelector('.btn-text').style.display = 'flex';
                generateBtn.querySelector('.btn-loader').style.display = 'none';
            }
        });
    }

    function resetForm() {
        document.getElementById('generate-form').reset();
        videoData = [];
        renderVideoCards();
        goToStep(1);

        document.querySelectorAll('.progress-step').forEach(s => {
            s.classList.remove('active', 'completed');
        });
    }

    function setupSuccessModal() {
        const successModal = document.getElementById('success-modal');
        const stayBtn = document.getElementById('stay-create');
        const goBtn = document.getElementById('go-history');

        stayBtn.addEventListener('click', () => {
            successModal.classList.remove('show');
        });

        goBtn.addEventListener('click', () => {
            successModal.classList.remove('show');
            document.querySelectorAll('.island-tab').forEach(t => t.classList.remove('active'));
            document.querySelector('.island-tab[data-section="history"]').classList.add('active');
            document.getElementById('section-create').classList.remove('active');
            document.getElementById('section-history').classList.add('active');
            
            if (updatePillFn) {
                updatePillFn(true);
            }
            
            loadItineraries();
        });
    }

    function setupSearch() {
        const searchInput = document.getElementById('search-input');
        let timeout;

        searchInput.addEventListener('input', () => {
            clearTimeout(timeout);
            timeout = setTimeout(() => {
                filterItineraries(searchInput.value.trim().toLowerCase());
            }, 300);
        });
    }

    function filterItineraries(query) {
        const grid = document.getElementById('itinerary-grid');
        const emptyState = document.getElementById('empty-history');

        if (!query) {
            renderItineraries(itineraries);
            return;
        }

        const filtered = itineraries.filter(it => {
            const title = (it.title || '').toLowerCase();
            const destination = (it.destination || '').toLowerCase();
            return title.includes(query) || destination.includes(query);
        });

        renderItineraries(filtered);

        if (filtered.length === 0 && itineraries.length > 0) {
            grid.innerHTML = '';
            emptyState.style.display = 'block';
            emptyState.querySelector('p').innerHTML = 'No itineraries match your search.';
        }
    }

    function stopPolling() {
        if (pollingInterval) {
            clearInterval(pollingInterval);
            pollingInterval = null;
        }
    }

    function startPolling() {
        stopPolling();
        
        const hasGeneratingItineraries = itineraries.some(it => it.status === 'generating');
        
        if (hasGeneratingItineraries) {
            pollingInterval = setInterval(async () => {
                const historySection = document.getElementById('section-history');
                if (!historySection.classList.contains('active')) {
                    stopPolling();
                    return;
                }
                
                try {
                    const res = await fetch(`${API_BASE}/api/itinerary/list`, {
                        headers: { 'Authorization': `Bearer ${accessToken}` }
                    });

                    if (!res.ok) return;

                    const updatedItineraries = await res.json();
                    
                    const hasChanges = JSON.stringify(updatedItineraries) !== JSON.stringify(itineraries);
                    
                    if (hasChanges) {
                        itineraries = updatedItineraries;
                        renderItineraries(itineraries);
                        
                        const stillGenerating = itineraries.some(it => it.status === 'generating');
                        if (!stillGenerating) {
                            stopPolling();
                        }
                    }
                } catch (err) {
                    console.error('Polling error:', err);
                }
            }, POLLING_INTERVAL_MS);
        }
    }

    async function loadItineraries() {
        const grid = document.getElementById('itinerary-grid');
        const emptyState = document.getElementById('empty-history');

        try {
            const res = await fetch(`${API_BASE}/api/itinerary/list`, {
                headers: { 'Authorization': `Bearer ${accessToken}` }
            });

            if (!res.ok) throw new Error('Failed to load itineraries');

            itineraries = await res.json();

            if (itineraries.length === 0) {
                grid.innerHTML = '';
                emptyState.style.display = 'block';
                emptyState.querySelector('p').innerHTML = 'No itineraries yet.<br>Create your first one!';
                stopPolling();
            } else {
                emptyState.style.display = 'none';
                renderItineraries(itineraries);
                startPolling();
            }
        } catch (err) {
            console.error(err);
            grid.innerHTML = '<p style="color: var(--muted); text-align: center;">Failed to load itineraries.</p>';
            stopPolling();
        }
    }

    function renderItineraries(list) {
        const grid = document.getElementById('itinerary-grid');
        const emptyState = document.getElementById('empty-history');

        if (list.length === 0) {
            grid.innerHTML = '';
            emptyState.style.display = 'block';
            return;
        }

        emptyState.style.display = 'none';
        grid.innerHTML = list.map(it => {
            const date = new Date(it.created_at).toLocaleDateString('en-US', {
                month: 'short', day: 'numeric', year: 'numeric'
            });
            const isNew = it.viewed === false && it.status === 'completed';
            const status = it.status || 'completed';
            
            let statusBadge = '';
            let cardClass = 'itinerary-card';
            let deleteBtn = '';
            
            if (status === 'generating') {
                statusBadge = `<span class="status-badge generating">
                    <svg class="spinner" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10" stroke-dasharray="31.4" stroke-dashoffset="10"></circle>
                    </svg>
                    In Progress${it.progress ? ` (${it.progress}%)` : ''}
                </span>`;
                cardClass += ' generating';
                deleteBtn = `<button class="btn-delete-card" data-delete-id="${it.id}">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="3 6 5 6 21 6"></polyline>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                    </svg>
                </button>`;
            } else if (status === 'failed') {
                statusBadge = `<span class="status-badge failed">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"></circle>
                        <line x1="15" y1="9" x2="9" y2="15"></line>
                        <line x1="9" y1="9" x2="15" y2="15"></line>
                    </svg>
                    Failed
                </span>`;
                cardClass += ' failed';
                deleteBtn = `<button class="btn-delete-card" data-delete-id="${it.id}">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="3 6 5 6 21 6"></polyline>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                    </svg>
                </button>`;
            } else {
                if (isNew) {
                    cardClass += ' new';
                }
                deleteBtn = `<button class="btn-delete-card" data-delete-id="${it.id}">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="3 6 5 6 21 6"></polyline>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                    </svg>
                </button>`;
            }
            
            return `
                <div class="${cardClass}" data-id="${it.id}" data-status="${status}">
                    ${deleteBtn}
                    ${statusBadge}
                    <h4>${escapeHtml(it.title || 'Generating itinerary...')}</h4>
                    <p class="destination">${escapeHtml(it.destination || (status === 'generating' ? 'Processing videos...' : 'Unknown destination'))}</p>
                    <div class="meta">
                        <span>
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
                                <line x1="16" y1="2" x2="16" y2="6"></line>
                                <line x1="8" y1="2" x2="8" y2="6"></line>
                                <line x1="3" y1="10" x2="21" y2="10"></line>
                            </svg>
                            ${date}
                        </span>
                        <span>${status === 'completed' ? (it.total_days || '?') + ' days' : ''}</span>
                    </div>
                </div>
            `;
        }).join('');

        grid.querySelectorAll('.btn-delete-card').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const id = btn.dataset.deleteId;
                showDeleteModal(id);
            });
        });

        grid.querySelectorAll('.itinerary-card').forEach(card => {
            card.addEventListener('click', async () => {
                const id = card.dataset.id;
                const status = card.dataset.status;
                
                if (status === 'generating') {
                    return;
                }
                
                if (status === 'failed') {
                    alert('This itinerary generation failed. Please try again.');
                    return;
                }
                
                if (card.classList.contains('new')) {
                    try {
                        await fetch(`${API_BASE}/api/itinerary/${id}/viewed`, {
                            method: 'PATCH',
                            headers: { 'Authorization': `Bearer ${accessToken}` }
                        });
                    } catch (err) {
                        console.error('Failed to mark as viewed:', err);
                    }
                }
                
                window.location.href = `/itinerary/${id}`;
            });
        });
    }

    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    initPageLoader();
    verifyAndInit();
})();
