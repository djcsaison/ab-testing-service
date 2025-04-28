class AuthManager {
    constructor(apiClient) {
        this.api = apiClient;
        this.loginModal = new bootstrap.Modal(document.getElementById('login-modal'));
        this.loginForm = document.getElementById('login-form');
        this.loginBtn = document.getElementById('login-btn');
        this.loginError = document.getElementById('login-error');
        
        this.init();
    }
    
    init() {
        // Try to load stored credentials
        const hasCredentials = this.api.loadCredentials();
        
        // Check if login is needed
        if (!hasCredentials) {
            this.showLoginForm();
        } else {
            // Verify stored credentials still work
            this.verifyCredentials();
        }
        
        // Add event listeners
        this.loginBtn.addEventListener('click', () => this.handleLogin());
        this.loginForm.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.handleLogin();
            }
        });
    }
    
    async verifyCredentials() {
        try {
            // Make a test request to see if credentials are valid
            await this.api.getExperiments();
            // If we get here, credentials are valid
            console.log('Authentication successful');
        } catch (error) {
            console.error('Stored credentials are invalid');
            this.showLoginForm();
        }
    }
    
    showLoginForm() {
        this.loginError.classList.add('d-none');
        this.loginModal.show();
    }
    
    async handleLogin() {
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        
        if (!username || !password) {
            this.loginForm.reportValidity();
            return;
        }
        
        try {
            const success = await this.api.login(username, password);
            
            if (success) {
                // Hide modal and refresh page
                this.loginModal.hide();
                window.location.reload();
            } else {
                this.loginError.classList.remove('d-none');
            }
        } catch (error) {
            console.error('Login error:', error);
            this.loginError.classList.remove('d-none');
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // Initialize the experiments manager
    const experimentsManager = new ExperimentsManager(api);
    
    // Initialize auth manager
    const authManager = new AuthManager(api);
    
    // Add Bootstrap icons via CDN
    const iconLink = document.createElement('link');
    iconLink.rel = 'stylesheet';
    iconLink.href = 'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.8.1/font/bootstrap-icons.css';
    document.head.appendChild(iconLink);
    
    // Log initialization
    console.log('A/B Testing dashboard initialized');
});

