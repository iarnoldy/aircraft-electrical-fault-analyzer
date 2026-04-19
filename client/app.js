/**
 * Main Application Logic for Aircraft Electrical Fault Analyzer
 * Manages UI state, real-time monitoring, and user interactions
 */

// Application State Management
const AppState = {
    systemStatus: null,
    diagnosticHistory: [],
    isPolling: true,
    activeFault: 'none',
    lastUpdate: null,
    pollingInterval: null,
    connectionStatus: 'checking',
    gauges: {
        battery: null,
        alternator: null
    }
};

// DOM Element Cache
const DOM = {
    // Status Elements
    connectionStatus: null,
    connectionStatusBadge: null,
    systemTime: null,

    // Battery Elements
    batteryGauge: null,
    batteryVoltage: null,
    batteryState: null,
    batteryStateBadge: null,
    batteryHealth: null,
    batteryHealthValue: null,
    batteryHealthText: null,
    batteryTemp: null,

    // Alternator Elements
    alternatorGauge: null,
    alternatorVoltage: null,
    alternatorState: null,
    alternatorStateBadge: null,
    fieldVoltage: null,
    alternatorCurrent: null,

    // Bus Elements
    mainBusVoltage: null,
    mainBusLoad: null,
    mainBusBreakers: null,
    essentialBusVoltage: null,
    essentialBusLoad: null,
    essentialBusBreakers: null,
    totalSystemLoad: null,

    // Diagnostic Form Elements
    diagnosticForm: null,
    symptomsInput: null,
    batteryVoltageInput: null,
    alternatorOutputInput: null,
    ambientTempInput: null,
    aircraftTypeSelect: null,
    diagnoseBtn: null,

    // Results Elements
    resultsContent: null,
    safetyWarnings: null,
    warningsList: null,
    troubleshootingSteps: null,
    stepsList: null,
    expectedResults: null,
    expectedList: null,
    recommendations: null,
    recommendationsList: null,
    noResults: null,

    // Fault Control Elements
    faultButtons: null,
    clearFaultsBtn: null,
    activeFault: null,

    // Utility Elements
    loadingOverlay: null,
    notification: null
};

/**
 * Initialize the application
 */
async function initializeApp() {
    console.log('[App] Initializing Aircraft Electrical Fault Analyzer...');

    // Cache DOM elements
    cacheDOMElements();

    // Set up event listeners
    setupEventListeners();

    // Initialize gauges
    initializeGauges();

    // Start clock
    startClock();

    // Check backend connection
    await checkBackendConnection();

    // Load initial system status
    await loadSystemStatus();

    // Start polling for updates
    startPolling();

    // Load diagnostic history
    await loadDiagnosticHistory();

    console.log('[App] Initialization complete');
}

/**
 * Cache all DOM element references
 */
function cacheDOMElements() {
    // Status Elements
    DOM.connectionStatus = document.getElementById('connectionStatus');
    DOM.connectionStatusBadge = document.getElementById('connectionStatusBadge');
    DOM.systemTime = document.getElementById('systemTime');

    // Battery Elements
    DOM.batteryGauge = document.getElementById('batteryGauge');
    DOM.batteryVoltage = document.getElementById('batteryVoltage');
    DOM.batteryState = document.getElementById('batteryState');
    DOM.batteryStateBadge = document.querySelector('.battery-state-badge');
    DOM.batteryHealth = document.getElementById('batteryHealth');
    DOM.batteryHealthValue = document.getElementById('batteryHealthValue');
    DOM.batteryHealthText = document.getElementById('batteryHealthText');
    DOM.batteryTemp = document.getElementById('batteryTemp');

    // Alternator Elements
    DOM.alternatorGauge = document.getElementById('alternatorGauge');
    DOM.alternatorVoltage = document.getElementById('alternatorVoltage');
    DOM.alternatorState = document.getElementById('alternatorState');
    DOM.alternatorStateBadge = document.querySelector('.alternator-state-badge');
    DOM.fieldVoltage = document.getElementById('fieldVoltage');
    DOM.alternatorCurrent = document.getElementById('alternatorCurrent');

    // Bus Elements
    DOM.mainBusVoltage = document.getElementById('mainBusVoltage');
    DOM.mainBusLoad = document.getElementById('mainBusLoad');
    DOM.mainBusBreakers = document.getElementById('mainBusBreakers');
    DOM.essentialBusVoltage = document.getElementById('essentialBusVoltage');
    DOM.essentialBusLoad = document.getElementById('essentialBusLoad');
    DOM.essentialBusBreakers = document.getElementById('essentialBusBreakers');
    DOM.totalSystemLoad = document.getElementById('totalSystemLoad');

    // Diagnostic Form Elements
    DOM.diagnosticForm = document.getElementById('diagnosticForm');
    DOM.symptomsInput = document.getElementById('symptoms');
    DOM.batteryVoltageInput = document.getElementById('batteryVoltageInput');
    DOM.alternatorOutputInput = document.getElementById('alternatorOutputInput');
    DOM.ambientTempInput = document.getElementById('ambientTempInput');
    DOM.aircraftTypeSelect = document.getElementById('aircraftType');
    DOM.diagnoseBtn = document.getElementById('diagnoseBtn');

    // Results Elements
    DOM.resultsContent = document.getElementById('resultsContent');
    DOM.safetyWarnings = document.getElementById('safetyWarnings');
    DOM.warningsList = document.getElementById('warningsList');
    DOM.troubleshootingSteps = document.getElementById('troubleshootingSteps');
    DOM.stepsList = document.getElementById('stepsList');
    DOM.expectedResults = document.getElementById('expectedResults');
    DOM.expectedList = document.getElementById('expectedList');
    DOM.recommendations = document.getElementById('recommendations');
    DOM.recommendationsList = document.getElementById('recommendationsList');
    DOM.noResults = document.getElementById('noResults');

    // Fault Control Elements
    DOM.faultButtons = document.querySelectorAll('.btn-fault');
    DOM.clearFaultsBtn = document.getElementById('clearFaultsBtn');
    DOM.activeFault = document.getElementById('activeFault');

    // Utility Elements
    DOM.loadingOverlay = document.getElementById('loadingOverlay');
    DOM.notification = document.getElementById('notification');
}

/**
 * Set up all event listeners
 */
function setupEventListeners() {
    // Diagnostic form submission
    DOM.diagnosticForm.addEventListener('submit', handleDiagnosticSubmit);

    // Fault injection buttons
    DOM.faultButtons.forEach(button => {
        button.addEventListener('click', handleFaultInjection);
    });

    // Clear faults button
    DOM.clearFaultsBtn.addEventListener('click', handleClearFaults);

    // Auto-save diagnostic form to localStorage
    DOM.symptomsInput.addEventListener('input', saveDraftDiagnostic);

    // Load draft on page load
    loadDraftDiagnostic();
}

/**
 * Initialize Chart.js gauges with modern semi-circle design
 */
function initializeGauges() {
    // Show gauge skeletons initially
    showGaugeSkeletons();

    // Battery Gauge - 12V System (10.5V - 14.4V range)
    AppState.gauges.battery = createChartJsGauge(DOM.batteryGauge, {
        minValue: 10.5,
        maxValue: 14.4,
        label: 'Battery',
        unit: 'V'
    });

    // Alternator Gauge - 0V - 16V range, target 14.4V
    AppState.gauges.alternator = createChartJsGauge(DOM.alternatorGauge, {
        minValue: 0,
        maxValue: 16,
        label: 'Alternator',
        unit: 'V'
    });

    // Remove skeletons after gauges are ready (slight delay for smooth transition)
    setTimeout(() => {
        hideGaugeSkeletons();
    }, 100);
}

/**
 * Create a modern Chart.js semi-circle gauge with teal gradient
 * @param {HTMLCanvasElement} canvas - Canvas element for the chart
 * @param {Object} options - Configuration options
 * @returns {Object} Chart instance with setValue method
 */
function createChartJsGauge(canvas, options) {
    const { minValue, maxValue, label, unit } = options;

    // Calculate initial data (starts at minValue)
    const range = maxValue - minValue;
    const currentValue = minValue;
    const remainingValue = range - (currentValue - minValue);

    // Create teal gradient for the gauge
    const createTealGradient = (ctx, chartArea) => {
        if (!chartArea) return '#4ecdc4';
        const gradient = ctx.createLinearGradient(0, chartArea.bottom, 0, chartArea.top);
        gradient.addColorStop(0, '#3db8af');  // Darker teal
        gradient.addColorStop(1, '#4ecdc4');  // Professional teal
        return gradient;
    };

    // Chart.js configuration for semi-circle gauge
    const config = {
        type: 'doughnut',
        data: {
            datasets: [{
                data: [currentValue - minValue, remainingValue],
                backgroundColor: (context) => {
                    const chart = context.chart;
                    const { ctx, chartArea } = chart;

                    if (!chartArea) {
                        return ['#4ecdc4', 'rgba(51, 65, 85, 0.2)'];
                    }

                    return [
                        createTealGradient(ctx, chartArea),  // Teal gradient for value
                        'rgba(51, 65, 85, 0.2)'              // Dark gray for remaining
                    ];
                },
                borderWidth: 0,
                circumference: 180,      // Semi-circle (180 degrees)
                rotation: 270,           // Start from bottom-left
                cutout: '75%',           // Donut thickness
                borderRadius: 8          // Rounded ends for modern look
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: false },
                tooltip: { enabled: false }
            },
            animation: {
                animateRotate: true,
                animateScale: true,
                duration: 750,           // Smooth 750ms animation
                easing: 'easeInOutQuart' // Smooth easing function
            }
        }
    };

    // Create the chart instance
    const chart = new Chart(canvas, config);

    // Return object with setValue method for compatibility with existing code
    return {
        chart: chart,
        options: options,
        setValue: function(newValue) {
            // Clamp value to min/max range
            const clampedValue = Math.max(minValue, Math.min(maxValue, newValue));
            const valueInRange = clampedValue - minValue;
            const remaining = range - valueInRange;

            // Update chart data with smooth animation
            chart.data.datasets[0].data = [valueInRange, remaining];
            chart.update('active');  // Use 'active' mode for smooth transition
        }
    };
}

/**
 * Legacy VoltageGauge class removed - replaced with Chart.js implementation
 * See createChartJsGauge() function above for modern gauge implementation
 */

/**
 * Start the system clock
 */
function startClock() {
    const updateTime = () => {
        const now = new Date();
        const hours = now.getHours().toString().padStart(2, '0');
        const minutes = now.getMinutes().toString().padStart(2, '0');
        const seconds = now.getSeconds().toString().padStart(2, '0');
        DOM.systemTime.textContent = `${hours}:${minutes}:${seconds}`;
    };

    updateTime();
    setInterval(updateTime, 1000);
}

/**
 * Check backend connection
 */
async function checkBackendConnection() {
    // Show connecting state
    updateConnectionStatus(null);

    const isConnected = await apiClient.checkConnection();
    updateConnectionStatus(isConnected);

    if (!isConnected) {
        // Use new notification system (Sprint 3 Task 3.4)
        if (typeof window.notify !== 'undefined') {
            window.notify.error('Connection Failed', 'Backend server is not running. Please start the Flask server.');
        }
    }
}

/**
 * Update connection status indicator with enhanced badge states
 */
function updateConnectionStatus(isConnected) {
    AppState.connectionStatus = isConnected ? 'online' : 'offline';

    const statusBadge = DOM.connectionStatusBadge;
    if (!statusBadge) return;

    statusBadge.classList.remove('connected', 'disconnected', 'connecting');

    if (isConnected === true) {
        statusBadge.classList.add('connected');
        statusBadge.innerHTML = `
            <span class="badge-icon">●</span>
            <span>Connected</span>
        `;
    } else if (isConnected === false) {
        statusBadge.classList.add('disconnected');
        statusBadge.innerHTML = `
            <span class="badge-icon">⚠</span>
            <span>Disconnected</span>
        `;
    } else {
        statusBadge.classList.add('connecting');
        statusBadge.innerHTML = `
            <span class="badge-icon spinner-icon">○</span>
            <span>Connecting</span>
        `;
    }

    // Legacy support for old status indicator if it exists
    if (DOM.connectionStatus) {
        DOM.connectionStatus.classList.toggle('offline', !isConnected);
    }
}

/**
 * Update battery state badge based on health percentage
 * @param {number} health - Battery health percentage (0-100)
 */
function updateBatteryStateBadge(health) {
    const badgeElement = DOM.batteryStateBadge;
    if (!badgeElement) return;

    // Remove all state classes
    badgeElement.classList.remove('badge-normal', 'badge-warning', 'badge-critical');

    // Apply appropriate class and content based on health
    if (health >= 90) {
        badgeElement.classList.add('badge-normal');
        badgeElement.innerHTML = `<span class="badge-icon">✓</span><span>GOOD</span>`;
    } else if (health >= 70) {
        badgeElement.classList.add('badge-warning');
        badgeElement.innerHTML = `<span class="badge-icon">⚠</span><span>FAIR</span>`;
    } else if (health >= 50) {
        badgeElement.classList.add('badge-warning');
        badgeElement.innerHTML = `<span class="badge-icon">⚠</span><span>POOR</span>`;
    } else {
        badgeElement.classList.add('badge-critical');
        badgeElement.innerHTML = `<span class="badge-icon">⚠</span><span>DEAD</span>`;
    }
}

/**
 * Update alternator state badge based on voltage
 * @param {number} voltage - Alternator output voltage
 */
function updateAlternatorStateBadge(voltage) {
    const badgeElement = DOM.alternatorStateBadge;
    if (!badgeElement) return;

    // Remove all state classes
    badgeElement.classList.remove('badge-normal', 'badge-charging', 'badge-warning', 'badge-critical');

    // Apply appropriate class and content based on voltage
    if (voltage >= 13.8) {
        badgeElement.classList.add('badge-charging');
        badgeElement.innerHTML = `<span class="badge-icon">⚡</span><span>CHARGING</span>`;
    } else if (voltage >= 12.0) {
        badgeElement.classList.add('badge-warning');
        badgeElement.innerHTML = `<span class="badge-icon">⚠</span><span>LOW OUTPUT</span>`;
    } else {
        badgeElement.classList.add('badge-critical');
        badgeElement.innerHTML = `<span class="badge-icon">⚠</span><span>FAILED</span>`;
    }
}

/**
 * Load system status from backend
 */
async function loadSystemStatus() {
    try {
        const response = await apiClient.getSystemStatus();
        AppState.systemStatus = response.data;  // Extract .data
        AppState.lastUpdate = new Date();
        updateSystemDisplay(response.data);     // Pass unwrapped data
        updateConnectionStatus(true);
    } catch (error) {
        console.error('[App] Failed to load system status:', error);
        updateConnectionStatus(false);
    }
}

/**
 * Update system display with new status data
 */
function updateSystemDisplay(status) {
    if (!status) return;

    // Update battery display
    if (status.battery) {
        updateBatteryDisplay(status.battery);
    }

    // Update alternator display
    if (status.alternator) {
        updateAlternatorDisplay(status.alternator);
    }

    // Update bus displays
    if (status.buses?.main_bus) {
        updateBusDisplay('main', status.buses.main_bus);
    }

    if (status.buses?.essential_bus) {
        updateBusDisplay('essential', status.buses.essential_bus);
    }

    // Update total system load
    const totalLoad = (status.buses?.main_bus?.load_current || 0) + (status.buses?.essential_bus?.load_current || 0);
    DOM.totalSystemLoad.textContent = `${totalLoad.toFixed(1)} A`;
}

/**
 * Update battery display
 */
function updateBatteryDisplay(batteryData) {
    // Update gauge
    AppState.gauges.battery.setValue(batteryData.voltage);

    // Update text values
    DOM.batteryVoltage.textContent = batteryData.voltage.toFixed(1);
    DOM.batteryTemp.textContent = `${batteryData.temperature.toFixed(1)}°C`;

    // Update legacy state indicator (if exists)
    if (DOM.batteryState) {
        DOM.batteryState.textContent = batteryData.state;
        DOM.batteryState.className = 'value state-indicator';

        if (batteryData.state === 'NORMAL') {
            DOM.batteryState.classList.add('normal');
        } else if (batteryData.state === 'LOW') {
            DOM.batteryState.classList.add('warning');
        } else if (batteryData.state === 'CRITICAL' || batteryData.state === 'DEAD') {
            DOM.batteryState.classList.add('critical');
        }
    }

    // Update health bar with animated gradient transitions
    const healthPercentage = batteryData.health || 100;
    updateHealthBar(healthPercentage);

    // Update battery state badge based on health
    updateBatteryStateBadge(healthPercentage);
}

/**
 * Update health bar with animated gradient transitions
 * @param {number} percentage - Health percentage (0-100)
 */
function updateHealthBar(percentage) {
    // Clamp percentage to valid range
    const clampedPercentage = Math.max(0, Math.min(100, percentage));

    const healthBar = DOM.batteryHealth;
    const healthText = DOM.batteryHealthText;
    const healthValue = DOM.batteryHealthValue;

    if (!healthBar) return;

    // Update width with smooth transition
    healthBar.style.width = `${clampedPercentage}%`;

    // Update text elements
    const percentageText = `${clampedPercentage.toFixed(1)}%`;
    if (healthText) {
        healthText.textContent = percentageText;
    }
    if (healthValue) {
        healthValue.textContent = percentageText;
    }

    // Remove all health state classes
    healthBar.classList.remove('excellent', 'good', 'warning', 'critical');

    // Add appropriate class based on percentage
    if (clampedPercentage >= 90) {
        healthBar.classList.add('excellent');
    } else if (clampedPercentage >= 70) {
        healthBar.classList.add('good');
    } else if (clampedPercentage >= 50) {
        healthBar.classList.add('warning');
    } else {
        healthBar.classList.add('critical');
    }
}

/**
 * Update alternator display
 */
function updateAlternatorDisplay(alternatorData) {
    // Update gauge - use output_voltage from backend
    AppState.gauges.alternator.setValue(alternatorData.output_voltage);

    // Update text values - use backend property names
    DOM.alternatorVoltage.textContent = alternatorData.output_voltage.toFixed(1);
    DOM.fieldVoltage.textContent = `${alternatorData.field_voltage.toFixed(1)} V`;
    DOM.alternatorCurrent.textContent = `${(alternatorData.output_current || 0).toFixed(1)} A`;

    // Convert boolean is_operating to state string
    const alternatorState = alternatorData.is_operating ? 'CHARGING' : 'FAILED';

    // Update legacy state indicator (if exists)
    if (DOM.alternatorState) {
        DOM.alternatorState.textContent = alternatorState;
        DOM.alternatorState.className = 'value state-indicator';

        if (alternatorState === 'CHARGING') {
            DOM.alternatorState.classList.add('normal');
        } else {
            DOM.alternatorState.classList.add('critical');
        }
    }

    // Update alternator state badge based on voltage
    updateAlternatorStateBadge(alternatorData.output_voltage);
}

/**
 * Update bus display
 */
function updateBusDisplay(busType, busData) {
    const voltageElement = busType === 'main' ? DOM.mainBusVoltage : DOM.essentialBusVoltage;
    const loadElement = busType === 'main' ? DOM.mainBusLoad : DOM.essentialBusLoad;
    const breakersElement = busType === 'main' ? DOM.mainBusBreakers : DOM.essentialBusBreakers;

    voltageElement.textContent = `${busData.voltage.toFixed(1)} V`;
    loadElement.textContent = `${busData.load_current.toFixed(1)} A`;

    // Update circuit breakers
    updateCircuitBreakers(breakersElement, busData.circuit_breakers);
}

/**
 * Update circuit breaker display with modern glassmorphism design
 */
function updateCircuitBreakers(container, breakers) {
    container.innerHTML = '';

    // Backend sends array of breakers, not object
    for (const breaker of breakers) {
        const breakerDiv = document.createElement('div');

        // Convert is_closed boolean to state string
        const breakerState = breaker.is_closed ? 'closed' : 'tripped';
        const stateText = breakerState.toUpperCase();

        breakerDiv.className = `breaker ${breakerState}`;
        breakerDiv.innerHTML = `
            <span class="breaker-label">${breaker.name}</span>
            <span class="rating">${breaker.rating}A</span>
            <span class="breaker-status">${stateText}</span>
        `;

        // Enhanced accessibility
        breakerDiv.setAttribute('role', 'button');
        breakerDiv.setAttribute('tabindex', '0');
        breakerDiv.setAttribute('aria-label', `${breaker.rating}A breaker ${stateText.toLowerCase()} - ${breaker.is_closed ? 'operating normally' : 'requires attention'}`);

        // Add click handler to reset tripped breakers
        if (!breaker.is_closed) {  // Breaker is tripped
            breakerDiv.style.cursor = 'pointer';
            breakerDiv.addEventListener('click', () => resetCircuitBreaker(breaker.name));
            // Keyboard accessibility
            breakerDiv.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    resetCircuitBreaker(breaker.name);
                }
            });
        }

        container.appendChild(breakerDiv);
    }
}

/**
 * Reset a tripped circuit breaker
 */
async function resetCircuitBreaker(breakerName) {
    console.log(`[App] Resetting circuit breaker: ${breakerName}`);

    // Use new notification system (Sprint 3 Task 3.4)
    if (typeof window.notify !== 'undefined') {
        window.notify.info('Circuit Breaker', `Resetting ${breakerName}...`);
    }

    // For now, just clear faults (backend doesn't have individual breaker reset)
    await handleClearFaults();
}

/**
 * Start polling for system updates
 */
function startPolling() {
    if (AppState.pollingInterval) {
        clearInterval(AppState.pollingInterval);
    }

    AppState.pollingInterval = setInterval(async () => {
        if (AppState.isPolling) {
            await loadSystemStatus();
        }
    }, 2000); // Poll every 2 seconds
}

/**
 * Stop polling for system updates
 */
function stopPolling() {
    AppState.isPolling = false;
    if (AppState.pollingInterval) {
        clearInterval(AppState.pollingInterval);
        AppState.pollingInterval = null;
    }
}

/**
 * Handle diagnostic form submission
 */
async function handleDiagnosticSubmit(event) {
    event.preventDefault();

    // Show diagnostic skeleton loader (Sprint 3 Task 3.2)
    showDiagnosticLoading();

    // Show loading overlay
    showLoading(true);

    try {
        // Gather form data - structure it correctly for backend API
        const diagnosticData = {
            symptoms: DOM.symptomsInput.value.trim(),
            measured_values: {
                battery_voltage: parseFloat(DOM.batteryVoltageInput.value) || 0,
                alternator_output: parseFloat(DOM.alternatorOutputInput.value) || 0,
                ambient_temperature: parseFloat(DOM.ambientTempInput.value) || 25
            },
            aircraft_type: DOM.aircraftTypeSelect.value
        };

        console.log('[App] Submitting diagnostic data:', diagnosticData);

        // Submit diagnosis
        const response = await apiClient.submitDiagnosis(diagnosticData);

        // Hide skeleton loader before showing results (Sprint 3 Task 3.2)
        hideDiagnosticLoading();

        // Display results (extract data from response)
        displayDiagnosticResults(response.data);

        // Clear draft
        localStorage.removeItem('diagnosticDraft');

        // Show success notification (Sprint 3 Task 3.4)
        if (typeof window.notify !== 'undefined') {
            window.notify.success('Diagnostic Complete', 'Analysis results are ready');
        }

        // Show safety warning notification if present
        if (response.data.safety_warnings && response.data.safety_warnings.length > 0) {
            window.notify.warning('Safety Warning', response.data.safety_warnings[0]);
        }

    } catch (error) {
        console.error('[App] Diagnostic submission failed:', error);

        // Hide skeleton on error too
        hideDiagnosticLoading();

        // Show error notification (Sprint 3 Task 3.4)
        if (typeof window.notify !== 'undefined') {
            window.notify.error('Diagnostic Failed', error.userMessage || 'Failed to submit diagnostic request');
        }
    } finally {
        showLoading(false);
    }
}

/**
 * Display diagnostic results with smooth animations
 * Sprint 3 Task 3.3: Staggered slide-in animations for results panel
 */
function displayDiagnosticResults(results) {
    console.log('[App] displayDiagnosticResults called with:', results);

    // Validate results object
    if (!results) {
        console.error('[App] No results provided to displayDiagnosticResults');
        return;
    }

    // Validate DOM elements exist
    if (!DOM.noResults || !DOM.safetyWarnings || !DOM.warningsList ||
        !DOM.troubleshootingSteps || !DOM.stepsList || !DOM.recommendations ||
        !DOM.recommendationsList || !DOM.resultsContent) {
        console.error('[App] Required DOM elements not found!', {
            noResults: !!DOM.noResults,
            safetyWarnings: !!DOM.safetyWarnings,
            warningsList: !!DOM.warningsList,
            troubleshootingSteps: !!DOM.troubleshootingSteps,
            stepsList: !!DOM.stepsList,
            recommendations: !!DOM.recommendations,
            recommendationsList: !!DOM.recommendationsList,
            resultsContent: !!DOM.resultsContent
        });
        return;
    }

    // Hide "no results" message
    DOM.noResults.style.display = 'none';

    // Get results panel container for entrance animation
    const resultsPanel = document.querySelector('.results-panel');

    // Remove any previous animation classes
    cleanupResultsAnimations();

    // Collect visible sections for staggered animation
    const visibleSections = [];
    let sectionIndex = 0;

    // Display safety warnings
    if (results.safety_warnings && results.safety_warnings.length > 0) {
        console.log(`[App] Displaying ${results.safety_warnings.length} safety warnings`);
        DOM.safetyWarnings.style.display = 'block';
        DOM.warningsList.innerHTML = '';
        results.safety_warnings.forEach((warning, index) => {
            const li = document.createElement('li');
            li.textContent = warning;
            // Optional: Add item-level stagger (limit to first 5 items)
            if (index < 5) {
                li.classList.add('fade-in-item', `item-stagger-${index + 1}`);
            }
            DOM.warningsList.appendChild(li);
        });
        console.log(`[App] Appended safety-warnings section to DOM (${results.safety_warnings.length} items)`);
        visibleSections.push({ element: DOM.safetyWarnings, index: sectionIndex++ });
    } else {
        console.log('[App] No safety warnings to display');
        DOM.safetyWarnings.style.display = 'none';
    }

    // Display troubleshooting steps
    if (results.troubleshooting_steps && results.troubleshooting_steps.length > 0) {
        console.log(`[App] Displaying ${results.troubleshooting_steps.length} troubleshooting steps`);
        DOM.troubleshootingSteps.style.display = 'block';
        DOM.stepsList.innerHTML = '';
        results.troubleshooting_steps.forEach((step, index) => {
            const li = document.createElement('li');
            // Format step object with action, expected_result, decision_point, safety_note
            // SECURITY FIX: Use safe DOM manipulation instead of innerHTML to prevent XSS
            if (typeof step === 'object' && step.action) {
                // Create structure safely with textContent (prevents HTML injection)
                const stepDiv = document.createElement('div');

                const titleStrong = document.createElement('strong');
                titleStrong.textContent = `Step ${step.step}: `;
                stepDiv.appendChild(titleStrong);

                const actionText = document.createTextNode(step.action || '');
                stepDiv.appendChild(actionText);

                stepDiv.appendChild(document.createElement('br'));

                const expectedLabel = document.createElement('em');
                expectedLabel.textContent = 'Expected: ';
                stepDiv.appendChild(expectedLabel);

                const expectedText = document.createTextNode(step.expected_result || '');
                stepDiv.appendChild(expectedText);

                stepDiv.appendChild(document.createElement('br'));

                const decisionLabel = document.createElement('em');
                decisionLabel.textContent = 'Decision: ';
                stepDiv.appendChild(decisionLabel);

                const decisionText = document.createTextNode(step.decision_point || '');
                stepDiv.appendChild(decisionText);

                stepDiv.appendChild(document.createElement('br'));

                const safetyLabel = document.createElement('em');
                safetyLabel.textContent = 'Safety: ';
                stepDiv.appendChild(safetyLabel);

                const safetyText = document.createTextNode(step.safety_note || '');
                stepDiv.appendChild(safetyText);

                li.appendChild(stepDiv);
            } else {
                li.textContent = step || '';
            }
            // Optional: Add item-level stagger (limit to first 5 items)
            if (index < 5) {
                li.classList.add('fade-in-item', `item-stagger-${index + 1}`);
            }
            DOM.stepsList.appendChild(li);
            console.log(`[App] Appended troubleshooting step ${index + 1} to stepsList`);
        });
        console.log(`[App] Appended troubleshooting-steps section to DOM`);
        visibleSections.push({ element: DOM.troubleshootingSteps, index: sectionIndex++ });
    } else {
        console.log('[App] No troubleshooting steps to display');
        DOM.troubleshootingSteps.style.display = 'none';
    }

    // Display expected results (if exists in response)
    if (DOM.expectedResults && DOM.expectedList) {
        if (results.expected_results && results.expected_results.length > 0) {
            console.log(`[App] Displaying ${results.expected_results.length} expected results`);
            DOM.expectedResults.style.display = 'block';
            DOM.expectedList.innerHTML = '';
            results.expected_results.forEach((result, index) => {
                const li = document.createElement('li');
                li.textContent = result;
                // Optional: Add item-level stagger (limit to first 5 items)
                if (index < 5) {
                    li.classList.add('fade-in-item', `item-stagger-${index + 1}`);
                }
                DOM.expectedList.appendChild(li);
            });
            visibleSections.push({ element: DOM.expectedResults, index: sectionIndex++ });
        } else {
            DOM.expectedResults.style.display = 'none';
        }
    }

    // Display recommendations
    if (results.recommendations && results.recommendations.length > 0) {
        console.log(`[App] Displaying ${results.recommendations.length} recommendations`);
        DOM.recommendations.style.display = 'block';
        DOM.recommendationsList.innerHTML = '';
        results.recommendations.forEach((rec, index) => {
            const li = document.createElement('li');
            li.textContent = rec;
            // Optional: Add item-level stagger (limit to first 5 items)
            if (index < 5) {
                li.classList.add('fade-in-item', `item-stagger-${index + 1}`);
            }
            DOM.recommendationsList.appendChild(li);
        });
        console.log(`[App] Appended recommendations section to DOM (${results.recommendations.length} items)`);
        visibleSections.push({ element: DOM.recommendations, index: sectionIndex++ });
    } else {
        console.log('[App] No recommendations to display');
        DOM.recommendations.style.display = 'none';
    }

    console.log(`[App] Total visible sections: ${visibleSections.length}`);

    // Apply entrance animation after skeleton fade-out completes (300ms)
    // Add small buffer (50ms) to ensure skeleton is fully removed
    setTimeout(() => {
        // Trigger panel slide-in animation
        if (resultsPanel) {
            resultsPanel.classList.add('results-panel-enter');
            console.log('[App] Added results-panel-enter animation class');
        }

        // Apply staggered section animations
        visibleSections.forEach(({ element, index }) => {
            if (element) {
                console.log(`[App] Applying animation to section ${index + 1}:`, element.id);
                element.classList.add('fade-in-up', `stagger-${index + 1}`);
                console.log(`[App] Section ${element.id} now has classes:`, element.className);
            }
        });

        // Scroll results into view after animations start
        setTimeout(() => {
            if (DOM.resultsContent) {
                DOM.resultsContent.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                console.log('[App] Results scrolled into view');
            }
        }, 200);
    }, 350); // Skeleton fade-out (300ms) + buffer (50ms)

    console.log('[App] displayDiagnosticResults complete - all sections displayed and animations applied');
}

/**
 * Clean up animation classes from previous results display
 * Sprint 3 Task 3.3: Ensures animations can replay on subsequent submissions
 */
function cleanupResultsAnimations() {
    const resultsPanel = document.querySelector('.results-panel');

    // Remove panel entrance class
    if (resultsPanel) {
        resultsPanel.classList.remove('results-panel-enter');
    }

    // Remove section stagger classes from all result sections
    const sections = [DOM.safetyWarnings, DOM.troubleshootingSteps, DOM.expectedResults, DOM.recommendations];
    sections.forEach(section => {
        if (section) {
            section.classList.remove('fade-in-up', 'stagger-1', 'stagger-2', 'stagger-3', 'stagger-4');
        }
    });

    // Remove item-level animation classes
    const allItems = document.querySelectorAll('.results-content li');
    allItems.forEach(item => {
        item.classList.remove('fade-in-item', 'item-stagger-1', 'item-stagger-2', 'item-stagger-3', 'item-stagger-4', 'item-stagger-5');
    });
}

/**
 * Handle fault injection
 */
async function handleFaultInjection(event) {
    const button = event.currentTarget;
    const faultType = button.dataset.fault;

    // Confirm with user
    if (!confirm(`Inject ${faultType.replace('_', ' ')} fault into the system?`)) {
        return;
    }

    try {
        showLoading(true);
        const result = await apiClient.injectFault(faultType);

        // Update active fault display
        AppState.activeFault = faultType;
        DOM.activeFault.textContent = faultType.replace('_', ' ').toUpperCase();
        DOM.activeFault.classList.add('active');

        // Update system display
        updateSystemDisplay(result.new_state || result.data);

        // Show fault injection notification (Sprint 3 Task 3.4)
        if (typeof window.notify !== 'undefined') {
            const faultName = faultType.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
            window.notify.warning('Fault Injected', `${faultName} has been activated`);
        }
    } catch (error) {
        console.error('[App] Failed to inject fault:', error);

        // Show error notification (Sprint 3 Task 3.4)
        if (typeof window.notify !== 'undefined') {
            window.notify.error('Fault Injection Failed', 'Failed to inject fault into system');
        }
    } finally {
        showLoading(false);
    }
}

/**
 * Handle clearing all faults
 */
async function handleClearFaults() {
    try {
        showLoading(true);
        const result = await apiClient.clearFaults();

        // Update active fault display
        AppState.activeFault = 'none';
        DOM.activeFault.textContent = 'None';
        DOM.activeFault.classList.remove('active');

        // Update system display
        updateSystemDisplay(result.new_state || result.data);

        // Show success notification (Sprint 3 Task 3.4)
        if (typeof window.notify !== 'undefined') {
            window.notify.success('Faults Cleared', 'All faults have been reset');
        }
    } catch (error) {
        console.error('[App] Failed to clear faults:', error);

        // Show error notification (Sprint 3 Task 3.4)
        if (typeof window.notify !== 'undefined') {
            window.notify.error('Clear Faults Failed', 'Failed to clear system faults');
        }
    } finally {
        showLoading(false);
    }
}

/**
 * Save draft diagnostic to localStorage
 */
function saveDraftDiagnostic() {
    const draft = {
        symptoms: DOM.symptomsInput.value,
        battery_voltage: DOM.batteryVoltageInput.value,
        alternator_output: DOM.alternatorOutputInput.value,
        ambient_temperature: DOM.ambientTempInput.value,
        aircraft_type: DOM.aircraftTypeSelect.value
    };

    localStorage.setItem('diagnosticDraft', JSON.stringify(draft));
}

/**
 * Load draft diagnostic from localStorage
 */
function loadDraftDiagnostic() {
    const draftStr = localStorage.getItem('diagnosticDraft');
    if (draftStr) {
        try {
            const draft = JSON.parse(draftStr);
            DOM.symptomsInput.value = draft.symptoms || '';
            DOM.batteryVoltageInput.value = draft.battery_voltage || '';
            DOM.alternatorOutputInput.value = draft.alternator_output || '';
            DOM.ambientTempInput.value = draft.ambient_temperature || '';
            DOM.aircraftTypeSelect.value = draft.aircraft_type || '';
        } catch (error) {
            console.error('[App] Failed to load draft:', error);
        }
    }
}

/**
 * Load diagnostic history
 */
async function loadDiagnosticHistory() {
    try {
        const history = await apiClient.getHistory();
        AppState.diagnosticHistory = history;
        console.log('[App] Loaded diagnostic history:', history.length, 'records');
    } catch (error) {
        console.error('[App] Failed to load history:', error);
    }
}

/**
 * Show/hide loading overlay
 */
function showLoading(show) {
    DOM.loadingOverlay.style.display = show ? 'flex' : 'none';
}

/**
 * Legacy showNotification function removed - replaced by notifications.js
 * Sprint 3 Task 3.4: Use window.notify.success/error/warning/info() instead
 */

/**
 * Handle visibility change (pause polling when tab is hidden)
 */
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        AppState.isPolling = false;
    } else {
        AppState.isPolling = true;
        loadSystemStatus(); // Immediate update when tab becomes visible
    }
});

/**
 * Initialize app when DOM is ready
 */
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeApp);
} else {
    initializeApp();
}

/* ===== Sprint 3 Task 3.2: Loading States & Skeleton Loaders ===== */

/**
 * Show gauge skeleton loaders
 * Sprint 3 Task 3.2: Professional shimmer loading states
 */
function showGaugeSkeletons() {
    const gaugeContainers = document.querySelectorAll('.gauge-container');

    gaugeContainers.forEach((container, index) => {
        // Create skeleton element
        const skeleton = document.createElement('div');
        skeleton.className = 'skeleton-gauge';
        skeleton.setAttribute('data-skeleton', 'gauge');
        skeleton.setAttribute('aria-busy', 'true');
        skeleton.setAttribute('aria-label', 'Loading gauge data');

        // Hide the canvas temporarily
        const canvas = container.querySelector('canvas');
        if (canvas) {
            canvas.style.opacity = '0';
        }

        // Hide the gauge value
        const gaugeValue = container.querySelector('.gauge-value');
        if (gaugeValue) {
            gaugeValue.style.opacity = '0';
        }

        // Insert skeleton before canvas
        container.insertBefore(skeleton, container.firstChild);
    });
}

/**
 * Hide gauge skeleton loaders with smooth fade transition
 * Sprint 3 Task 3.2: Seamless skeleton → content transition
 */
function hideGaugeSkeletons() {
    const skeletons = document.querySelectorAll('[data-skeleton="gauge"]');

    skeletons.forEach(skeleton => {
        const container = skeleton.parentElement;

        // Fade out skeleton
        skeleton.classList.add('fade-out');

        // After fade out, show real content
        setTimeout(() => {
            // Remove skeleton
            skeleton.remove();

            // Fade in canvas and value
            const canvas = container.querySelector('canvas');
            const gaugeValue = container.querySelector('.gauge-value');

            if (canvas) {
                canvas.style.opacity = '0';
                canvas.classList.add('fade-in');
                setTimeout(() => {
                    canvas.style.opacity = '1';
                }, 10);
            }

            if (gaugeValue) {
                gaugeValue.style.opacity = '0';
                gaugeValue.classList.add('fade-in');
                setTimeout(() => {
                    gaugeValue.style.opacity = '1';
                }, 10);
            }

            // Remove aria-busy
            container.setAttribute('aria-busy', 'false');
        }, 300); // Match fade-out animation duration
    });
}

/**
 * Show diagnostic results skeleton loader
 * Sprint 3 Task 3.2: Loading state for diagnostic panel
 */
function showDiagnosticLoading() {
    const resultsContent = DOM.resultsContent;

    // Clear all skeleton elements first (in case one exists)
    const existingSkeleton = resultsContent.querySelector('[data-skeleton="results"]');
    if (existingSkeleton) {
        existingSkeleton.remove();
    }

    // Hide all existing content - keep them in the DOM for reuse
    DOM.noResults.style.display = 'none';
    DOM.safetyWarnings.style.display = 'none';
    DOM.troubleshootingSteps.style.display = 'none';
    DOM.expectedResults.style.display = 'none';
    DOM.recommendations.style.display = 'none';

    // Create skeleton structure using safe DOM manipulation
    const skeletonDiv = document.createElement('div');
    skeletonDiv.className = 'skeleton-results';
    skeletonDiv.setAttribute('data-skeleton', 'results');
    skeletonDiv.setAttribute('aria-busy', 'true');
    skeletonDiv.setAttribute('aria-label', 'Loading diagnostic results');

    // Create 3 skeleton sections
    for (let i = 0; i < 3; i++) {
        const section = document.createElement('div');
        section.className = 'skeleton-results-section';

        // Add skeleton text elements
        const numItems = i === 1 ? 5 : 4;  // Middle section has one more item
        for (let j = 0; j < numItems; j++) {
            const textEl = document.createElement('div');
            textEl.className = 'skeleton-text';

            if (j === 0) {
                textEl.classList.add('medium', 'width-60');
            } else {
                const widths = ['width-100', 'width-90', 'width-80', 'width-70'];
                textEl.classList.add(widths[j] || 'width-80');
            }

            section.appendChild(textEl);
        }

        skeletonDiv.appendChild(section);
    }

    // Append skeleton to resultsContent (does NOT clear existing elements)
    resultsContent.appendChild(skeletonDiv);
    resultsContent.setAttribute('aria-busy', 'true');

    console.log('[App] Diagnostic skeleton loader displayed');
}

/**
 * Hide diagnostic results skeleton loader
 * Sprint 3 Task 3.2: Smooth transition to real results
 */
function hideDiagnosticLoading() {
    const skeleton = document.querySelector('[data-skeleton="results"]');

    if (skeleton) {
        skeleton.classList.add('fade-out');

        setTimeout(() => {
            skeleton.remove();
            DOM.resultsContent.setAttribute('aria-busy', 'false');
        }, 300);
    }
}

/**
 * Show weather data skeleton loaders
 * Sprint 3 Task 3.2: Loading state for weather panel
 */
function showWeatherSkeleton() {
    const weatherGrid = document.querySelector('.weather-grid');

    if (!weatherGrid) return;

    // Create 4 skeleton weather items
    const skeletonHTML = `
        <div class="skeleton-weather-item" data-skeleton="weather">
            <div class="skeleton-weather-icon"></div>
            <div class="skeleton-weather-data">
                <div class="skeleton-text small width-60"></div>
                <div class="skeleton-text medium width-80"></div>
            </div>
        </div>
        <div class="skeleton-weather-item" data-skeleton="weather">
            <div class="skeleton-weather-icon"></div>
            <div class="skeleton-weather-data">
                <div class="skeleton-text small width-60"></div>
                <div class="skeleton-text medium width-80"></div>
            </div>
        </div>
        <div class="skeleton-weather-item" data-skeleton="weather">
            <div class="skeleton-weather-icon"></div>
            <div class="skeleton-weather-data">
                <div class="skeleton-text small width-60"></div>
                <div class="skeleton-text medium width-80"></div>
            </div>
        </div>
        <div class="skeleton-weather-item" data-skeleton="weather">
            <div class="skeleton-weather-icon"></div>
            <div class="skeleton-weather-data">
                <div class="skeleton-text small width-60"></div>
                <div class="skeleton-text medium width-80"></div>
            </div>
        </div>
    `;

    weatherGrid.innerHTML = skeletonHTML;
    weatherGrid.setAttribute('aria-busy', 'true');
}

/**
 * Hide weather data skeleton loaders
 * Sprint 3 Task 3.2: Seamless transition to real weather data
 */
function hideWeatherSkeleton() {
    const skeletons = document.querySelectorAll('[data-skeleton="weather"]');
    const weatherGrid = document.querySelector('.weather-grid');

    if (skeletons.length > 0) {
        skeletons.forEach(skeleton => {
            skeleton.classList.add('fade-out');
        });

        setTimeout(() => {
            skeletons.forEach(skeleton => skeleton.remove());
            if (weatherGrid) {
                weatherGrid.setAttribute('aria-busy', 'false');
            }
        }, 300);
    }
}