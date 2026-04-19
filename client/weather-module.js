// === Weather API Integration ===

// API Configuration
const API_BASE_URL = 'http://localhost:5000';

// Weather DOM Elements
const WeatherDOM = {
    weatherSource: document.getElementById('weatherSource'),
    refreshWeather: document.getElementById('refreshWeather'),
    temperature: document.getElementById('temperature'),
    humidity: document.getElementById('humidity'),
    pressure: document.getElementById('pressure'),
    wind: document.getElementById('wind'),
    batteryCapacityEffect: document.getElementById('batteryCapacityEffect'),
    alternatorEfficiency: document.getElementById('alternatorEfficiency'),
    correctedVoltage: document.getElementById('correctedVoltage'),
    locationInput: document.getElementById('locationInput')
};

// Weather state
let currentLocation = null;  // No default - wait for user input

/**
 * Load weather data for a location
 */
async function loadWeatherData(icao = 'KATL') {
    try {
        console.log(`[Weather] Fetching weather for ${icao}`);

        // Show weather skeleton (Sprint 3 Task 3.2)
        if (typeof showWeatherSkeleton === 'function') {
            showWeatherSkeleton();
        }

        const response = await fetch(`${API_BASE_URL}/api/weather?icao=${icao}`);

        if (!response.ok) {
            throw new Error(`Weather API returned ${response.status}`);
        }

        const result = await response.json();

        // Hide skeleton before showing data (Sprint 3 Task 3.2)
        if (typeof hideWeatherSkeleton === 'function') {
            hideWeatherSkeleton();
        }

        if (result.success && result.data) {
            updateWeatherDisplay(result.data);
            currentLocation = icao;
        } else {
            console.error('[Weather] Invalid weather data:', result);
            showWeatherError('Failed to load weather data');
        }
    } catch (error) {
        console.error('[Weather] Error loading weather:', error);

        // Hide skeleton on error (Sprint 3 Task 3.2)
        if (typeof hideWeatherSkeleton === 'function') {
            hideWeatherSkeleton();
        }

        showWeatherError('Weather data unavailable');
    }
}

/**
 * Update weather display with fetched data
 */
function updateWeatherDisplay(weatherData) {
    // Rebuild weather grid with actual data (Sprint 3 Task 3.2)
    const weatherGrid = document.querySelector('.weather-grid');

    if (weatherGrid) {
        weatherGrid.innerHTML = `
            <div class="weather-item fade-in">
                <i class="weather-icon" data-lucide="thermometer" aria-hidden="true"></i>
                <div class="weather-data">
                    <label>Temperature</label>
                    <span class="weather-value" id="temperature">${weatherData.temperature_celsius}°C</span>
                </div>
            </div>
            <div class="weather-item fade-in">
                <i class="weather-icon" data-lucide="droplets" aria-hidden="true"></i>
                <div class="weather-data">
                    <label>Humidity</label>
                    <span class="weather-value" id="humidity">${weatherData.humidity_percent}%</span>
                </div>
            </div>
            <div class="weather-item fade-in">
                <i class="weather-icon" data-lucide="gauge" aria-hidden="true"></i>
                <div class="weather-data">
                    <label>Pressure</label>
                    <span class="weather-value" id="pressure">${weatherData.pressure_mb} mb</span>
                </div>
            </div>
            <div class="weather-item fade-in">
                <i class="weather-icon" data-lucide="wind" aria-hidden="true"></i>
                <div class="weather-data">
                    <label>Wind</label>
                    <span class="weather-value" id="wind">${weatherData.wind_speed_knots} kts</span>
                </div>
            </div>
        `;

        // Re-initialize Lucide icons for new elements
        if (typeof lucide !== 'undefined' && lucide.createIcons) {
            lucide.createIcons();
        }
    }

    // Update source
    WeatherDOM.weatherSource.textContent = `Source: ${weatherData.source || 'Unknown'}`;

    // Update temperature effects if available
    if (weatherData.temperature_effects) {
        const effects = weatherData.temperature_effects;
        WeatherDOM.batteryCapacityEffect.textContent = `${effects.battery_capacity_percent}%`;
        WeatherDOM.alternatorEfficiency.textContent = `${effects.alternator_efficiency_percent}%`;
        WeatherDOM.correctedVoltage.textContent = `${effects.corrected_battery_voltage} V`;
    }

    console.log('[Weather] Display updated successfully');
}

/**
 * Show weather error state
 */
function showWeatherError(message) {
    WeatherDOM.weatherSource.textContent = message;
    WeatherDOM.temperature.textContent = '-- °C';
    WeatherDOM.humidity.textContent = '-- %';
    WeatherDOM.pressure.textContent = '---- mb';
    WeatherDOM.wind.textContent = '-- kts';
    WeatherDOM.batteryCapacityEffect.textContent = '--%';
    WeatherDOM.alternatorEfficiency.textContent = '--%';
    WeatherDOM.correctedVoltage.textContent = '-- V';
}

/**
 * Handle weather refresh button click
 */
function handleWeatherRefresh() {
    const location = WeatherDOM.locationInput?.value?.trim().toUpperCase();

    if (location && location.length === 4) {
        loadWeatherData(location);
    } else if (currentLocation) {
        // Use last known location
        loadWeatherData(currentLocation);
    } else {
        // No location provided
        WeatherDOM.weatherSource.textContent = 'Please enter a 4-letter airport code (e.g., KATL)';
    }
}

/**
 * Initialize weather module
 */
function initializeWeather() {
    // Don't auto-load weather - wait for user to enter a location
    WeatherDOM.weatherSource.textContent = 'Enter airport code (e.g., KATL) and click refresh';

    // Set up refresh button
    if (WeatherDOM.refreshWeather) {
        WeatherDOM.refreshWeather.addEventListener('click', handleWeatherRefresh);
    }

    // Update weather when location input changes
    if (WeatherDOM.locationInput) {
        WeatherDOM.locationInput.addEventListener('blur', function() {
            const location = this.value.trim().toUpperCase();
            if (location && location.length === 4) {
                loadWeatherData(location);
            }
        });
    }

    console.log('[Weather] Module initialized - waiting for user location input');
}

// Initialize weather when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeWeather);
} else {
    initializeWeather();
}
