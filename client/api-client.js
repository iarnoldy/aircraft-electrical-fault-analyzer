/**
 * API Client for Aircraft Electrical Fault Analyzer
 * Handles all communication with the Flask backend
 */

class APIClient {
    constructor() {
        this.baseURL = 'http://localhost:5000';
        this.timeout = 60000; // 60 seconds (increased for Claude API diagnostic requests)
        this.retryAttempts = 3;
        this.retryDelay = 1000; // Start with 1 second
    }

    /**
     * Make an HTTP request with retry logic and error handling
     * @param {string} endpoint - API endpoint
     * @param {Object} options - Fetch options
     * @param {number} attempt - Current attempt number
     * @returns {Promise} Response data
     */
    async request(endpoint, options = {}, attempt = 1) {
        const url = `${this.baseURL}${endpoint}`;

        // Add default headers
        const defaultHeaders = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        };

        options.headers = { ...defaultHeaders, ...options.headers };

        // Create AbortController for timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.timeout);

        try {
            console.log(`[API] ${options.method || 'GET'} ${url}`, options.body ? JSON.parse(options.body) : '');
            const startTime = performance.now();

            const response = await fetch(url, {
                ...options,
                signal: controller.signal
            });

            clearTimeout(timeoutId);
            const responseTime = performance.now() - startTime;
            console.log(`[API] Response time: ${responseTime.toFixed(2)}ms`);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            console.log('[API] Response:', data);
            return data;

        } catch (error) {
            clearTimeout(timeoutId);
            console.error(`[API] Error on attempt ${attempt}:`, error);

            // Handle different error types
            if (error.name === 'AbortError') {
                error.userMessage = 'Request timed out. Please check your connection.';
            } else if (error.message.includes('Failed to fetch')) {
                error.userMessage = 'Cannot connect to server. Please ensure the backend is running.';
            } else {
                error.userMessage = error.message;
            }

            // Retry logic with exponential backoff
            if (attempt < this.retryAttempts) {
                const delay = this.retryDelay * Math.pow(2, attempt - 1);
                console.log(`[API] Retrying in ${delay}ms...`);
                await new Promise(resolve => setTimeout(resolve, delay));
                return this.request(endpoint, options, attempt + 1);
            }

            throw error;
        }
    }

    /**
     * Get current electrical system status
     * @returns {Promise} System status data
     */
    async getSystemStatus() {
        try {
            return await this.request('/api/system/status');
        } catch (error) {
            console.error('[API] Failed to get system status:', error);
            throw error;
        }
    }

    /**
     * Submit diagnostic request
     * @param {Object} diagnosticData - Diagnostic input data
     * @returns {Promise} Diagnostic results
     */
    async submitDiagnosis(diagnosticData) {
        try {
            // Validate required fields
            if (!diagnosticData.symptoms || !diagnosticData.aircraft_type) {
                throw new Error('Symptoms and aircraft type are required');
            }

            // Clean up measured values (remove empty values)
            const measuredValues = {};
            if (diagnosticData.battery_voltage) {
                measuredValues.battery_voltage = parseFloat(diagnosticData.battery_voltage);
            }
            if (diagnosticData.alternator_output) {
                measuredValues.alternator_output = parseFloat(diagnosticData.alternator_output);
            }
            if (diagnosticData.ambient_temperature) {
                measuredValues.ambient_temperature = parseFloat(diagnosticData.ambient_temperature);
            }

            const requestData = {
                symptoms: diagnosticData.symptoms,
                measured_values: measuredValues,
                aircraft_type: diagnosticData.aircraft_type
            };

            return await this.request('/api/diagnose', {
                method: 'POST',
                body: JSON.stringify(requestData)
            });
        } catch (error) {
            console.error('[API] Failed to submit diagnosis:', error);
            throw error;
        }
    }

    /**
     * Inject a fault into the system
     * @param {string} faultType - Type of fault to inject
     * @returns {Promise} Updated system status
     */
    async injectFault(faultType) {
        try {
            const validFaults = ['dead_battery', 'alternator_failure', 'bus_fault', 'circuit_breaker_trip'];
            if (!validFaults.includes(faultType)) {
                throw new Error(`Invalid fault type: ${faultType}`);
            }

            return await this.request('/api/system/inject-fault', {
                method: 'POST',
                body: JSON.stringify({ fault_type: faultType })
            });
        } catch (error) {
            console.error('[API] Failed to inject fault:', error);
            throw error;
        }
    }

    /**
     * Clear all faults from the system
     * @returns {Promise} Updated system status
     */
    async clearFaults() {
        try {
            return await this.request('/api/system/clear-faults', {
                method: 'POST'
            });
        } catch (error) {
            console.error('[API] Failed to clear faults:', error);
            throw error;
        }
    }

    /**
     * Get diagnostic history
     * @param {number} limit - Maximum number of records to retrieve
     * @returns {Promise} Diagnostic history array
     */
    async getHistory(limit = 10) {
        try {
            return await this.request(`/api/history?limit=${limit}`);
        } catch (error) {
            console.error('[API] Failed to get history:', error);
            throw error;
        }
    }

    /**
     * Reset the entire electrical system
     * @returns {Promise} System status after reset
     */
    async resetSystem() {
        try {
            return await this.request('/api/system/reset', {
                method: 'POST'
            });
        } catch (error) {
            console.error('[API] Failed to reset system:', error);
            throw error;
        }
    }

    /**
     * Check if the backend server is available
     * @returns {Promise<boolean>} True if server is available
     */
    async checkConnection() {
        try {
            await this.request('/api/system/status');
            return true;
        } catch (error) {
            return false;
        }
    }

    /**
     * Get simulated weather data
     * @param {string} location - Airport code or location
     * @returns {Promise} Weather data
     */
    async getWeatherData(location = 'KATL') {
        try {
            return await this.request(`/api/weather?location=${location}`);
        } catch (error) {
            console.error('[API] Failed to get weather data:', error);
            // Return default weather data if API fails
            return {
                location: location,
                temperature: 25,
                humidity: 50,
                pressure: 29.92,
                conditions: 'Clear'
            };
        }
    }
}

// Create singleton instance
const apiClient = new APIClient();

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = APIClient;
}