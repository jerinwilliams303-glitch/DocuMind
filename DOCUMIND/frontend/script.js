/**
 * DocuMind Frontend Logic
 * Connects the UI to the Flask Backend API
 */

const app = {
    init() {
        this.checkSession();
        this.bindEvents();
    },
    bindEvents() {
        // Auth Toggles
        document.getElementById('show-register').addEventListener('click', (e) => {
            e.preventDefault();
            this.toggleAuth('register');
        });
        document.getElementById('show-login').addEventListener('click', (e) => {
            e.preventDefault();
            this.toggleAuth('login');
        });

        // Password Toggles
        document.querySelectorAll('.toggle-password').forEach(icon => {
            icon.addEventListener('click', () => {
                const targetId = icon.getAttribute('data-target');
                const input = document.getElementById(targetId);
                const isPassword = input.type === 'password';
                input.type = isPassword ? 'text' : 'password';
                icon.classList.toggle('fa-eye');
                icon.classList.toggle('fa-eye-slash');
            });
        });

        // Clear Errors on Input
        document.querySelectorAll('.auth-form input').forEach(input => {
            input.addEventListener('input', () => {
                this.clearFieldError(input.id);
                this.clearFormError(input.closest('form').id);
                
                // Real-time password match check
                if (input.id === 'reg-confirm-password' || input.id === 'reg-password') {
                    this.checkPasswordMatch();
                }
            });
        });


        // Auth Submissions
        document.getElementById('login-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleLogin();
        });
        document.getElementById('register-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleRegister();
        });
        document.getElementById('logout-btn').addEventListener('click', () => this.handleLogout());

        // Navigation Switcher
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.addEventListener('click', () => this.switchView(btn.dataset.view));
        });


        // File Selection/Upload
        const dropzone = document.getElementById('dropzone');
        const fileInput = document.getElementById('file-input');
        
        dropzone.addEventListener('click', () => fileInput.click());
        dropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropzone.classList.add('dragover');
        });
        dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.classList.remove('dragover');
            if (e.dataTransfer.files.length) this.handleUpload(e.dataTransfer.files[0]);
        });
        fileInput.addEventListener('change', () => {
            if (fileInput.files.length) this.handleUpload(fileInput.files[0]);
        });

        // Search Handlers
        document.getElementById('search-btn').addEventListener('click', () => this.handleSearch());
        document.getElementById('search-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.handleSearch();
        });


    },

    switchView(viewId) {
        // Update UI Classes
        document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
        document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
        
        document.getElementById(viewId).classList.add('active');
        document.querySelector(`[data-view="${viewId}"]`).classList.add('active');
        
        // Refresh data based on view
        if (viewId === 'home-view') this.loadAnalytics();
        if (viewId === 'files-view') this.loadFiles();
    },

    async loadFiles() {
        const list = document.getElementById('file-list');
        try {
            const resp = await fetch('/files');
            const data = await resp.json();
            
            if (!data.files || data.files.length === 0) {
                list.innerHTML = '<div class="empty-state">No documents uploaded yet.</div>';
                return;
            }

            list.innerHTML = data.files.map(file => `
                <li class="file-item">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <i class="fas ${file.filename.toLowerCase().endsWith('.pdf') ? 'fa-file-pdf' : 'fa-file-image'}" style="color: var(--primary);"></i>
                        <div>
                            <strong>${file.filename}</strong>
                            <div style="font-size: 0.8rem; color: var(--text-muted);">${new Date(file.upload_date).toLocaleDateString()}</div>
                        </div>
                    </div>
                    <div style="display: flex; gap: 8px;">
                        <button class="pin-btn ${file.is_pinned ? 'pinned' : ''}" onclick="app.togglePin(${file.id})" title="Pin document">
                            <i class="fas fa-thumbtack"></i>
                        </button>
                        <a href="/view/${file.id}" target="_blank" class="btn btn-secondary btn-sm">View</a>
                        <a href="/download/${file.id}" class="btn btn-secondary btn-sm"><i class="fas fa-download"></i></a>
                        <button class="btn btn-danger btn-sm" onclick="app.deleteFile(${file.id})"><i class="fas fa-trash"></i></button>
                    </div>
                </li>
            `).join('');

        } catch (e) {
            console.error('Error loading files:', e);
        }
    },

    async handleUpload(file) {
        const formData = new FormData();
        formData.append('file', file);
        
        const dropzone = document.getElementById('dropzone');
        const originalContent = dropzone.innerHTML;
        dropzone.innerHTML = '<i class="fas fa-spinner fa-spin fa-2x"></i><p>Processing document...</p>';

        try {
            const resp = await fetch('/upload', { method: 'POST', body: formData });
            const data = await resp.json();
            if (data.error) alert(data.error);
            else {
                this.loadFiles();
                this.loadAnalytics();
            }
        } catch (e) {
            alert('Upload failed. Please check your connection.');
        } finally {
            dropzone.innerHTML = originalContent;
        }
    },

    async handleSearch() {
        const input = document.getElementById('search-input');
        const query = input.value.trim();
        if (!query) return;

        const resultsContainer = document.getElementById('search-results');
        resultsContainer.innerHTML = '<div class="empty-state"><i class="fas fa-spinner fa-spin"></i> Searching across documents...</div>';

        try {
            const resp = await fetch(`/search?q=${encodeURIComponent(query)}`);
            const data = await resp.json();
            
            if (!data.results || data.results.length === 0) {
                resultsContainer.innerHTML = '<div class="empty-state">No relevant matches found.</div>';
                return;
            }

            resultsContainer.innerHTML = data.results.map(res => {
                const confClass = this.getConfidenceClass(res.score);
                const highlightedSnippet = this.highlightSnippet(res.snippet, query);
                const matchTypeClass = res.match_type === 'keyword' ? 'keyword-match' : 'similarity-match';

                return `
                    <div class="result-card ${matchTypeClass}">
                        <div class="result-meta">${res.filename}</div>
                        <div class="confidence-container" style="margin-bottom: 12px;">
                            <div class="progress-bar">
                                <div class="progress-fill ${confClass}" style="width: ${Math.min(res.score * 100, 100)}%"></div>
                            </div>
                            <span class="confidence-text ${confClass}">${Math.round(res.score * 100)}% match</span>
                        </div>
                        <p class="result-text">${highlightedSnippet}</p>
                        <div class="explanation-panel">${res.explanation}</div>
                    </div>
                `;
            }).join('');
        } catch (e) {
            resultsContainer.innerHTML = '<div class="empty-state">Error performing search.</div>';
        }
    },

    // --- Auth Logic ---

    async checkSession() {
        try {
            const resp = await fetch('/me');
            const data = await resp.json();
            if (data.logged_in) {
                this.updateUIForLoggedIn(data.user);
            } else {
                this.updateUIForLoggedOut();
            }
        } catch (e) {
            this.updateUIForLoggedOut();
        }
    },

    toggleAuth(mode) {
        const card = document.querySelector('.auth-card');
        const loginContainer = document.getElementById('login-form-container');
        const registerContainer = document.getElementById('register-form-container');
        
        card.classList.add('switching');
        
        setTimeout(() => {
            if (mode === 'register') {
                loginContainer.style.display = 'none';
                registerContainer.style.display = 'block';
            } else {
                loginContainer.style.display = 'block';
                registerContainer.style.display = 'none';
            }
            card.classList.remove('switching');
            // Clear all errors when switching
            this.clearAllErrors();
        }, 150);
    },

    async handleLogin() {
        const usernameInput = document.getElementById('login-username');
        const passwordInput = document.getElementById('login-password');
        const username = this.sanitize(usernameInput.value);
        const password = passwordInput.value;
        const btn = document.getElementById('login-btn');
        
        if (!username) return this.setFieldError('login-username', 'Username is required');
        if (!password) return this.setFieldError('login-password', 'Password is required');

        this.setLoading(btn, true, 'Signing In...');
        this.clearFormError('login-form');

        try {
            const resp = await fetch('/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            const data = await resp.json();
            if (data.error) {
                this.setFormError('login-form', data.error);
            } else {
                this.updateUIForLoggedIn(data.user);
            }
        } catch (e) {
            this.setFormError('login-form', 'Connection error. Please try again.');
        } finally {
            this.setLoading(btn, false, 'Sign In');
        }
    },

    async handleRegister() {
        const usernameInput = document.getElementById('reg-username');
        const emailInput = document.getElementById('reg-email');
        const passwordInput = document.getElementById('reg-password');
        const confirmInput = document.getElementById('reg-confirm-password');
        
        const username = this.sanitize(usernameInput.value);
        const email = this.sanitize(emailInput.value);
        const password = passwordInput.value;
        const confirm = confirmInput.value;
        const btn = document.getElementById('register-btn');
        
        // Validation
        let hasError = false;
        if (!username) { this.setFieldError('reg-username', 'Username is required'); hasError = true; }
        if (!email || !email.includes('@')) { this.setFieldError('reg-email', 'Valid email is required'); hasError = true; }
        if (password.length < 6) { this.setFieldError('reg-password', 'Password must be 6+ characters'); hasError = true; }
        if (password !== confirm) { this.setFieldError('reg-confirm-password', 'Passwords do not match'); hasError = true; }
        
        if (hasError) return;

        this.setLoading(btn, true, 'Creating Account...');
        this.clearFormError('register-form');

        try {
            const resp = await fetch('/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, email, password })
            });
            const data = await resp.json();
            if (data.error) {
                this.setFormError('register-form', data.error);
            } else {
                // Show success and toggle to login
                this.setFormSuccess('register-form', 'Account created successfully! Please login.');
                setTimeout(() => this.toggleAuth('login'), 2000);
            }
        } catch (e) {
            this.setFormError('register-form', 'Connection error. Please try again.');
        } finally {
            this.setLoading(btn, false, 'Create Account');
        }
    },

    // --- Auth Helpers ---

    sanitize(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    },

    setLoading(btn, isLoading, text) {
        if (isLoading) {
            btn.classList.add('loading');
            btn.disabled = true;
            btn.querySelector('.btn-text').textContent = text;
        } else {
            btn.classList.remove('loading');
            btn.disabled = false;
            btn.querySelector('.btn-text').textContent = text;
        }
    },

    setFieldError(id, message) {
        const input = document.getElementById(id);
        const errorSpan = document.getElementById(`err-${id}`);
        input.classList.add('invalid');
        errorSpan.textContent = message;
        errorSpan.classList.add('active');
    },

    clearFieldError(id) {
        const input = document.getElementById(id);
        const errorSpan = document.getElementById(`err-${id}`);
        if (input) input.classList.remove('invalid', 'valid');
        if (errorSpan) {
            errorSpan.textContent = '';
            errorSpan.classList.remove('active');
        }
    },

    setFormError(formId, message) {
        const errorDiv = document.getElementById(`${formId === 'login-form' ? 'login' : 'register'}-error`);
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
        errorDiv.classList.add('form-error');
        errorDiv.classList.remove('form-success');
    },

    setFormSuccess(formId, message) {
        const errorDiv = document.getElementById(`${formId === 'login-form' ? 'login' : 'register'}-error`);
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
        errorDiv.classList.add('form-success');
        errorDiv.classList.remove('form-error');
    },

    clearFormError(formId) {
        const errorDiv = document.getElementById(`${formId === 'login-form' ? 'login' : 'register'}-error`);
        if (errorDiv) errorDiv.style.display = 'none';
    },

    clearAllErrors() {
        document.querySelectorAll('.field-error').forEach(s => { s.textContent = ''; s.classList.remove('active'); });
        document.querySelectorAll('.auth-form input').forEach(i => i.classList.remove('invalid', 'valid'));
        document.querySelectorAll('.form-error, .form-success').forEach(d => d.style.display = 'none');
    },

    checkPasswordMatch() {
        const pass = document.getElementById('reg-password').value;
        const confirm = document.getElementById('reg-confirm-password').value;
        const confirmInput = document.getElementById('reg-confirm-password');
        
        if (confirm.length > 0) {
            if (pass === confirm) {
                confirmInput.classList.remove('invalid');
                confirmInput.classList.add('valid');
                this.clearFieldError('reg-confirm-password');
            } else {
                confirmInput.classList.remove('valid');
                confirmInput.classList.add('invalid');
            }
        }
    },


    async handleLogout() {
        try {
            await fetch('/logout', { method: 'POST' });
            this.updateUIForLoggedOut();
        } catch (e) {
            location.reload();
        }
    },

    updateUIForLoggedIn(user) {
        document.getElementById('auth-container').style.display = 'none';
        document.getElementById('app-container').style.display = 'flex';
        document.getElementById('username-display').textContent = user.username;
        this.loadFiles();
        this.loadAnalytics();
    },

    updateUIForLoggedOut() {
        document.getElementById('auth-container').style.display = 'flex';
        document.getElementById('app-container').style.display = 'none';
    },

    // --- File Management ---

    async deleteFile(id) {
        if (!confirm('Are you sure you want to permanently delete this document?')) return;

        try {
            const resp = await fetch(`/file/${id}`, { method: 'DELETE' });
            const data = await resp.json();
            if (data.error) alert(data.error);
            else {
                this.loadFiles();
                this.loadAnalytics();
            }
        } catch (e) {
            alert('Failed to delete file.');
        }
    },


    async togglePin(id) {
        try {
            await fetch(`/pin/${id}`, { method: 'POST' });
            this.loadFiles();
        } catch (e) {
            console.error('Error pinning file:', e);
        }
    },

    getConfidenceClass(score) {
        if (score > 0.5) return 'conf-high';
        if (score > 0.2) return 'conf-medium';
        return 'conf-low';
    },

    highlightSnippet(text, query) {
        if (!text || !query) return text;

        // 1. Escape HTML for XSS protection
        const div = document.createElement('div');
        div.textContent = text;
        const escapedText = div.innerHTML;

        // 2. Extract words from query (non-trivial ones)
        const terms = query.split(/\s+/).filter(t => t.length > 2);
        if (terms.length === 0) return escapedText;

        // 3. Highlight each term safely
        // Sort by length descending
        terms.sort((a, b) => b.length - a.length);

        // Build a single regex for all terms
        const escapedTerms = terms.map(t => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|');
        const regex = new RegExp(`(${escapedTerms})`, 'gi');

        // Replace only if not inside a tag (basic check: not preceded by < and not followed by >)
        // More robust: use the replace callback to only act on text nodes or similar, 
        // but since we start with escaped text, we can just replace terms in one go.
        return escapedText.replace(regex, '<mark class="highlight">$1</mark>');
    },

    async loadAnalytics() {
        try {
            const resp = await fetch('/analytics');
            const data = await resp.json();
            document.getElementById('stat-total-docs').textContent = data.total_documents || 0;
            document.getElementById('stat-total-searches').textContent = data.total_searches || 0;
        } catch (e) {
            console.error('Error loading analytics:', e);
        }
    }
};


window.onload = () => app.init();
