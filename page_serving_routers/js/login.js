document.addEventListener('DOMContentLoaded', function() {
    initPageLoader();
    checkExistingSession();
    initTabs();
    initForms();
    initPasswordToggles();
});

function initPageLoader() {
    const body = document.body;
    setTimeout(() => {
        body.classList.remove('loading');
    }, 800);
    createParticles(document.getElementById('particles'), 30);
}

function createParticles(container, count) {
    if (!container) return;
    const colors = ['var(--cyan)', 'var(--magenta)', 'var(--violet)'];
    for (let i = 0; i < count; i++) {
        const p = document.createElement('div');
        p.classList.add('particle');
        p.style.left = Math.random() * 100 + '%';
        p.style.top = Math.random() * 100 + '%';
        const size = Math.random() * 4 + 1;
        p.style.width = size + 'px';
        p.style.height = size + 'px';
        p.style.background = colors[Math.floor(Math.random() * colors.length)];
        p.style.animationDuration = (Math.random() * 6 + 4) + 's';
        p.style.animationDelay = (Math.random() * 4) + 's';
        container.appendChild(p);
    }
}

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

function initTabs() {
    const tabs = document.querySelectorAll('.nav-item');
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');

    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            if (this.classList.contains('active')) return;

            tabs.forEach(t => {
                t.classList.remove('active');
                t.setAttribute('aria-selected', 'false');
            });

            this.classList.add('active');
            this.setAttribute('aria-selected', 'true');

            clearMessages();

            const tabName = this.getAttribute('data-tab');
            if (tabName === 'login') {
                loginForm.classList.add('active');
                registerForm.classList.remove('active');
            } else {
                registerForm.classList.add('active');
                loginForm.classList.remove('active');
            }
        });
    });
}

function initForms() {
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');

    loginForm.addEventListener('submit', handleLogin);
    registerForm.addEventListener('submit', handleRegister);
}

async function handleLogin(event) {
    event.preventDefault();
    
    const btn = document.getElementById('login-btn');
    const email = document.getElementById('login-email').value.trim();
    const password = document.getElementById('login-password').value;

    if (!email || !password) {
        showError('Please fill in all fields');
        return;
    }

    setLoading(btn, true);
    clearMessages();

    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();

        if (response.ok) {
            localStorage.setItem('access_token', data.access_token);
            showSuccess('Welcome back! Redirecting to your adventures...');
            setTimeout(() => {
                window.location.href = '/dashboard';
            }, 500);
        } else {
            showError(data.detail || 'Login failed. Please check your credentials.');
        }
    } catch (error) {
        showError('Connection error. Please try again.');
    } finally {
        setLoading(btn, false);
    }
}

async function handleRegister(event) {
    event.preventDefault();

    const btn = document.getElementById('register-btn');
    const name = document.getElementById('register-name').value.trim();
    const email = document.getElementById('register-email').value.trim();
    const password = document.getElementById('register-password').value;
    const confirmPassword = document.getElementById('register-confirm-password').value;

    if (!name || !email || !password || !confirmPassword) {
        showError('Please fill in all fields');
        return;
    }

    if (password !== confirmPassword) {
        showError('Passwords do not match');
        return;
    }

    if (password.length < 8) {
        showError('Password must be at least 8 characters');
        return;
    }

    setLoading(btn, true);
    clearMessages();

    try {
        const response = await fetch('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, email, password })
        });

        const data = await response.json();

        if (response.ok) {
            showSuccess('Account created! Time to explore the world!');
            document.getElementById('register-form').reset();
            
            setTimeout(() => {
                document.querySelector('[data-tab="login"]').click();
                document.getElementById('login-email').value = email;
            }, 1500);
        } else {
            showError(data.detail || 'Registration failed. Please try again.');
        }
    } catch (error) {
        showError('Connection error. Please try again.');
    } finally {
        setLoading(btn, false);
    }
}

function setLoading(button, isLoading) {
    const btnText = button.querySelector('.btn-text');
    const btnLoader = button.querySelector('.btn-loader');

    if (isLoading) {
        button.disabled = true;
        btnText.style.display = 'none';
        btnLoader.style.display = 'flex';
    } else {
        button.disabled = false;
        btnText.style.display = 'inline';
        btnLoader.style.display = 'none';
    }
}

function showError(message) {
    const errorEl = document.getElementById('error-message');
    errorEl.textContent = message;
    errorEl.classList.add('show');
}

function showSuccess(message) {
    const successEl = document.getElementById('success-message');
    successEl.textContent = message;
    successEl.classList.add('show');
}

function clearMessages() {
    document.getElementById('error-message').classList.remove('show');
    document.getElementById('success-message').classList.remove('show');
}

function initPasswordToggles() {
    const toggleButtons = document.querySelectorAll('.password-toggle');
    
    toggleButtons.forEach(button => {
        button.addEventListener('click', function() {
            const targetId = this.getAttribute('data-target');
            const passwordInput = document.getElementById(targetId);
            const eyeOpenElements = this.querySelectorAll('.eye-open');
            const eyeClosedElements = this.querySelectorAll('.eye-closed');
            
            if (passwordInput.type === 'password') {
                passwordInput.type = 'text';
                eyeOpenElements.forEach(el => el.style.display = 'none');
                eyeClosedElements.forEach(el => el.style.display = 'block');
            } else {
                passwordInput.type = 'password';
                eyeOpenElements.forEach(el => el.style.display = 'block');
                eyeClosedElements.forEach(el => el.style.display = 'none');
            }
        });
    });
}
