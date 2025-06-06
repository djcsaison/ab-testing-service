/**
 * API client for the A/B Testing Service
 */
class ApiClient {
    constructor(baseUrl = '') {
        this.baseUrl = baseUrl;
        this.apiPath = '/api';
        this.credentials = null;
    }

    /**
     * Set authentication credentials
     * @param {string} username - Username for basic auth
     * @param {string} password - Password for basic auth
     */
    setCredentials(username, password) {
        this.credentials = btoa(`${username}:${password}`);
        // Store credentials in sessionStorage for persistence across page reloads
        sessionStorage.setItem('ab_testing_auth', this.credentials);
    }

    /**
     * Load credentials from session storage
     * @returns {boolean} - Whether credentials were loaded
     */
    loadCredentials() {
        const savedAuth = sessionStorage.getItem('ab_testing_auth');
        if (savedAuth) {
            this.credentials = savedAuth;
            return true;
        }
        return false;
    }

    /**
     * Clear stored credentials
     */
    clearCredentials() {
        this.credentials = null;
        sessionStorage.removeItem('ab_testing_auth');
    }
    
    /**
     * Check if user is authenticated
     * @returns {boolean} - Whether user has credentials set
     */
    isAuthenticated() {
        return this.credentials !== null;
    }

    /**
     * Make an API request
     * @param {string} endpoint - API endpoint
     * @param {Object} options - Fetch options
     * @returns {Promise} - Fetch promise
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${this.apiPath}${endpoint}`;
        
        // Default headers
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        // Add authentication if credentials are set
        if (this.credentials) {
            headers['Authorization'] = `Basic ${this.credentials}`;
        }

        const config = {
            ...options,
            headers
        };

        try {
            const response = await fetch(url, config);
            
            // Handle authentication errors
            if (response.status === 401) {
                this.clearCredentials();
                throw new Error('Authentication failed. Please log in again.');
            }
            
            // Handle non-JSON responses for 204 No Content
            if (response.status === 204) {
                return { success: true };
            }
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.detail || 'API request failed');
            }
            
            return data;
        } catch (error) {
            console.error(`API request failed: ${error.message}`);
            throw error;
        }
    }

    /**
     * Log in using basic authentication
     * @param {string} username - Username
     * @param {string} password - Password
     * @returns {Promise<boolean>} - Whether login was successful
     */
    async login(username, password) {
        try {
            // Set temporary credentials for this request
            const tempCredentials = btoa(`${username}:${password}`);
            
            // Test credentials with a simple request
            const response = await fetch(`${this.baseUrl}${this.apiPath}/experiments`, {
                headers: {
                    'Authorization': `Basic ${tempCredentials}`
                }
            });
            
            if (response.ok) {
                // Save credentials if successful
                this.setCredentials(username, password);
                return true;
            } else {
                return false;
            }
        } catch (error) {
            console.error('Login failed:', error);
            return false;
        }
    }

    /**
     * Experiment API methods
     */
    
    // Get all experiments, optionally filtered by status
    async getExperiments(status = null) {
        const queryParams = status ? `?status=${status}` : '';
        return this.request(`/experiments${queryParams}`, { method: 'GET' });
    }

    // Get a single experiment by ID
    async getExperiment(experimentId) {
        return this.request(`/experiments/${experimentId}`, { method: 'GET' });
    }

    // Create a new experiment
    async createExperiment(experimentData) {
        return this.request('/experiments', {
            method: 'POST',
            body: JSON.stringify(experimentData)
        });
    }

    // Update an experiment
    async updateExperiment(experimentId, updateData) {
        return this.request(`/experiments/${experimentId}`, {
            method: 'PATCH',
            body: JSON.stringify(updateData)
        });
    }

    // Delete an experiment
    async deleteExperiment(experimentId) {
        return this.request(`/experiments/${experimentId}`, {
            method: 'DELETE'
        });
    }

    // Update experiment status
    async updateExperimentStatus(experimentId, status) {
        // Make sure we're sending the status as a string, not an object
        const statusValue = typeof status === 'object' ? status.status : status;
        
        return this.request(`/experiments/${experimentId}/status`, {
            method: 'POST',
            body: JSON.stringify({ "status": statusValue })
        });
    }

    // Get experiment statistics
    async getExperimentStats(experimentId, options = {}) {
        const queryParams = new URLSearchParams();
        
        if (options.eventTypes) {
            options.eventTypes.forEach(type => {
                queryParams.append('event_types', type);
            });
        }
        
        if (options.includeAssignments !== undefined) {
            queryParams.append('include_assignments', options.includeAssignments);
        }
        
        if (options.includeAnalysis !== undefined) {
            queryParams.append('include_analysis', options.includeAnalysis);
        }
        
        const queryString = queryParams.toString() ? `?${queryParams.toString()}` : '';
        
        return this.request(`/experiments/${experimentId}/stats${queryString}`, { 
            method: 'GET' 
        });
    }

    /**
     * Assignment API methods
     */
    
    // Get assignments for a user
    async getUserAssignments(userId) {
        return this.request(`/assignments/user/${userId}`, { method: 'GET' });
    }

    // Get or create an assignment
    async getOrCreateAssignment(userId, experimentId) {
        return this.request(`/assignments/get`, {
            method: 'POST',
            body: JSON.stringify({
                subid: userId,
                experiment_id: experimentId
            })
        });
    }

    /**
     * Events API methods
     */
    
    // Query events for an experiment
    async queryEvents(experimentId, filters = {}) {
        const queryParams = new URLSearchParams();
        queryParams.append('experiment_id', experimentId);
        
        if (filters.startDate) {
            queryParams.append('start_date', filters.startDate.toISOString());
        }
        
        if (filters.endDate) {
            queryParams.append('end_date', filters.endDate.toISOString());
        }
        
        if (filters.eventType) {
            queryParams.append('event_type', filters.eventType);
        }
        
        if (filters.variant) {
            queryParams.append('variant', filters.variant);
        }
        
        if (filters.subid) {
            queryParams.append('subid', filters.subid);
        }
        
        return this.request(`/events?${queryParams.toString()}`, { method: 'GET' });
    }
}

// Create a global API client instance
const api = new ApiClient();