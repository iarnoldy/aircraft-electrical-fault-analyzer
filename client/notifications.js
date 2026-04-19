/**
 * Enhanced Notification System for Aircraft Electrical Fault Analyzer
 * Sprint 3 Task 3.4: Toast notifications with slide-in/out animations,
 * Lucide icons, progress bar countdown, and glassmorphism design
 *
 * SCAD ITGM 522 Project 3
 */

/**
 * Notification Manager - Modern toast notification system
 *
 * Features:
 * - 4 notification types (success, error, warning, info)
 * - Lucide icon integration
 * - Progress bar countdown
 * - Slide-in/out animations with cubic-bezier easing
 * - Glassmorphism design
 * - Stacking with 3-notification limit
 * - Auto-dismiss with configurable duration
 * - Pause on hover (optional)
 */
class NotificationManager {
    constructor() {
        this.container = null;
        this.notifications = [];
        this.maxNotifications = 3;  // Sprint 3 Task 3.4 requirement
        this.notificationCounter = 0;
        this.init();
    }

    /**
     * Initialize the notification system
     */
    init() {
        // Get or create notification container
        this.container = document.getElementById('notificationContainer');

        if (!this.container) {
            this.container = document.createElement('div');
            this.container.id = 'notificationContainer';
            this.container.className = 'notification-container';
            document.body.appendChild(this.container);
        }

        console.log('[NotificationManager] Initialized with max notifications:', this.maxNotifications);
    }

    /**
     * Show a notification toast
     * @param {string} type - Notification type: 'success', 'error', 'warning', 'info'
     * @param {string} title - Notification title (bold)
     * @param {string} message - Notification message text
     * @param {number} duration - Duration in milliseconds (default: 5000ms = 5s)
     * @returns {string} - Notification ID for manual dismiss
     */
    showNotification(type, title, message, duration = 5000) {
        // Enforce 3-notification limit (oldest dismissed first)
        if (this.notifications.length >= this.maxNotifications) {
            const oldestNotification = this.notifications[0];
            this.hideNotification(oldestNotification.id);
        }

        // Generate unique ID
        const notificationId = `notification-${Date.now()}-${this.notificationCounter++}`;

        // Create notification element
        const notificationElement = this.createNotificationElement(type, title, message, notificationId);

        // Add to container (stacks vertically)
        this.container.appendChild(notificationElement);

        // Store notification reference
        this.notifications.push({
            id: notificationId,
            element: notificationElement,
            timerId: null,
            progressAnimationId: null,
            startTime: Date.now(),
            duration: duration
        });

        // Trigger slide-in animation (10ms delay for CSS transition)
        setTimeout(() => {
            notificationElement.classList.add('show');
        }, 10);

        // Start progress bar countdown animation
        if (duration > 0) {
            this.startProgressBarAnimation(notificationId, duration);
        }

        // Auto-dismiss after duration
        if (duration > 0) {
            const notificationData = this.notifications.find(n => n.id === notificationId);
            notificationData.timerId = setTimeout(() => {
                this.hideNotification(notificationId);
            }, duration);
        }

        console.log(`[NotificationManager] Showed ${type} notification:`, title);
        return notificationId;
    }

    /**
     * Create notification DOM element with glassmorphism, Lucide icon, and progress bar
     * @param {string} type - Notification type
     * @param {string} title - Notification title
     * @param {string} message - Notification message
     * @param {string} notificationId - Unique notification ID
     * @returns {HTMLElement} - Notification element
     */
    createNotificationElement(type, title, message, notificationId) {
        const notification = document.createElement('div');
        notification.className = `notification-toast notification-${type}`;
        notification.id = notificationId;
        notification.setAttribute('role', 'alert');
        notification.setAttribute('aria-live', 'assertive');

        // Get Lucide icon name for type
        const iconName = this.getLucideIconName(type);

        // Build notification HTML
        notification.innerHTML = `
            <div class="notification-header">
                <div class="notification-icon" data-lucide="${iconName}"></div>
                <div class="notification-title">${this.escapeHtml(title)}</div>
                <button class="notification-close" aria-label="Close notification" data-notification-id="${notificationId}">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                </button>
            </div>
            <div class="notification-message">${this.escapeHtml(message)}</div>
            <div class="notification-progress-bar">
                <div class="notification-progress-fill" data-notification-id="${notificationId}"></div>
            </div>
        `;

        // Attach close button event listener
        const closeButton = notification.querySelector('.notification-close');
        closeButton.addEventListener('click', () => {
            this.hideNotification(notificationId);
        });

        // Initialize Lucide icons for this notification
        setTimeout(() => {
            if (typeof lucide !== 'undefined' && lucide.createIcons) {
                lucide.createIcons({ nameAttr: 'data-lucide' });
            }
        }, 0);

        return notification;
    }

    /**
     * Get Lucide icon name for notification type
     * @param {string} type - Notification type
     * @returns {string} - Lucide icon name
     */
    getLucideIconName(type) {
        const iconMap = {
            'success': 'check-circle',     // Teal checkmark
            'error': 'alert-circle',       // Red alert circle
            'warning': 'alert-triangle',   // Yellow warning triangle
            'info': 'info'                 // Blue info circle
        };
        return iconMap[type] || iconMap.info;
    }

    /**
     * Start progress bar countdown animation
     * @param {string} notificationId - Notification ID
     * @param {number} duration - Duration in milliseconds
     */
    startProgressBarAnimation(notificationId, duration) {
        const notificationData = this.notifications.find(n => n.id === notificationId);
        if (!notificationData) return;

        const progressBar = document.querySelector(`[data-notification-id="${notificationId}"].notification-progress-fill`);
        if (!progressBar) return;

        // Animate from 100% to 0% width using transform: scaleX()
        progressBar.style.transition = `transform ${duration}ms linear`;
        progressBar.style.transform = 'scaleX(1)';

        // Trigger animation (10ms delay for CSS transition)
        setTimeout(() => {
            progressBar.style.transform = 'scaleX(0)';
        }, 10);

        // Optional: Pause progress on hover
        const notificationElement = notificationData.element;
        notificationElement.addEventListener('mouseenter', () => {
            const currentScale = this.getCurrentScale(progressBar);
            progressBar.style.transition = 'none';
            progressBar.style.transform = `scaleX(${currentScale})`;
        });

        notificationElement.addEventListener('mouseleave', () => {
            const currentScale = this.getCurrentScale(progressBar);
            const remainingTime = currentScale * duration;
            progressBar.style.transition = `transform ${remainingTime}ms linear`;
            progressBar.style.transform = 'scaleX(0)';
        });
    }

    /**
     * Get current scale of progress bar (for pause on hover)
     * @param {HTMLElement} element - Progress bar element
     * @returns {number} - Current scale (0-1)
     */
    getCurrentScale(element) {
        const transform = window.getComputedStyle(element).transform;
        if (transform === 'none') return 1;

        const matrix = new DOMMatrixReadOnly(transform);
        return matrix.a; // scaleX value
    }

    /**
     * Hide and remove notification with slide-out animation
     * @param {string} notificationId - Notification ID
     */
    hideNotification(notificationId) {
        const notificationData = this.notifications.find(n => n.id === notificationId);
        if (!notificationData) return;

        const { element, timerId } = notificationData;

        // Clear auto-dismiss timer
        if (timerId) {
            clearTimeout(timerId);
        }

        // Trigger slide-out animation
        element.classList.remove('show');
        element.classList.add('hide');

        // Remove from DOM after animation completes (250ms)
        setTimeout(() => {
            if (element.parentNode) {
                element.parentNode.removeChild(element);
            }

            // Remove from notifications array
            this.notifications = this.notifications.filter(n => n.id !== notificationId);

            console.log(`[NotificationManager] Dismissed notification: ${notificationId}`);
        }, 250); // Match exit animation duration
    }

    /**
     * Clear all notifications
     */
    clearAllNotifications() {
        // Dismiss all notifications with staggered timing for smooth effect
        this.notifications.forEach((notificationData, index) => {
            setTimeout(() => {
                this.hideNotification(notificationData.id);
            }, index * 50); // 50ms stagger
        });
    }

    /**
     * Convenience method: Show success notification (teal)
     * @param {string} title - Notification title
     * @param {string} message - Notification message
     * @param {number} duration - Duration (default: 5s)
     */
    success(title, message, duration = 5000) {
        return this.showNotification('success', title, message, duration);
    }

    /**
     * Convenience method: Show error notification (red)
     * @param {string} title - Notification title
     * @param {string} message - Notification message
     * @param {number} duration - Duration (default: 8s for errors)
     */
    error(title, message, duration = 8000) {
        return this.showNotification('error', title, message, duration);
    }

    /**
     * Convenience method: Show warning notification (yellow)
     * @param {string} title - Notification title
     * @param {string} message - Notification message
     * @param {number} duration - Duration (default: 6s)
     */
    warning(title, message, duration = 6000) {
        return this.showNotification('warning', title, message, duration);
    }

    /**
     * Convenience method: Show info notification (blue)
     * @param {string} title - Notification title
     * @param {string} message - Notification message
     * @param {number} duration - Duration (default: 5s)
     */
    info(title, message, duration = 5000) {
        return this.showNotification('info', title, message, duration);
    }

    /**
     * Escape HTML to prevent XSS attacks
     * @param {string} text - Text to escape
     * @returns {string} - Escaped HTML
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

/**
 * Loading Manager for showing loading states
 * (Kept from original for compatibility)
 */
class LoadingManager {
    /**
     * Show loading indicator on an element
     * @param {HTMLElement} element - Element to show loading on
     * @param {string} message - Loading message
     */
    showLoading(element, message = 'Loading...') {
        if (!element) return;

        // Remove existing spinner
        this.hideLoading(element);

        const spinner = document.createElement('div');
        spinner.className = 'loading-spinner';
        spinner.innerHTML = `
            <div class="spinner-animation"></div>
            <span class="spinner-message">${message}</span>
        `;

        element.appendChild(spinner);
        element.classList.add('loading');
    }

    /**
     * Hide loading indicator
     * @param {HTMLElement} element - Element to hide loading from
     */
    hideLoading(element) {
        if (!element) return;

        const spinner = element.querySelector('.loading-spinner');
        if (spinner) {
            spinner.remove();
        }

        element.classList.remove('loading');
    }

    /**
     * Show loading overlay
     */
    showOverlay() {
        let overlay = document.getElementById('loadingOverlay');

        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'loadingOverlay';
            overlay.className = 'loading-overlay';
            overlay.innerHTML = `
                <div class="spinner"></div>
                <p>Processing...</p>
            `;
            document.body.appendChild(overlay);
        }

        overlay.style.display = 'flex';
    }

    /**
     * Hide loading overlay
     */
    hideOverlay() {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) {
            overlay.style.display = 'none';
        }
    }
}

/**
 * Error Handler for comprehensive error management
 * (Kept from original for compatibility)
 */
class ErrorHandler {
    constructor(notificationManager) {
        this.notify = notificationManager;
        this.errors = [];
    }

    /**
     * Handle API error
     * @param {Error} error - Error object
     * @param {string} context - Context where error occurred
     */
    handleAPIError(error, context = 'API Request') {
        console.error(`${context} error:`, error);

        let message = 'An unexpected error occurred';

        if (error.message) {
            message = error.message;
        } else if (error.error) {
            message = error.error;
        } else if (typeof error === 'string') {
            message = error;
        }

        // Log error
        this.logError({
            type: 'API_ERROR',
            context: context,
            message: message,
            timestamp: new Date().toISOString(),
            stack: error.stack
        });

        // Show user-friendly error notification (Task 3.4 format)
        this.notify.error('API Error', message);
    }

    /**
     * Handle validation error
     * @param {string} field - Field that failed validation
     * @param {string} message - Validation message
     */
    handleValidationError(field, message) {
        this.logError({
            type: 'VALIDATION_ERROR',
            field: field,
            message: message,
            timestamp: new Date().toISOString()
        });

        this.notify.warning('Validation Error', `${field}: ${message}`);
    }

    /**
     * Handle connection error
     */
    handleConnectionError() {
        const message = 'Cannot connect to server. Please check your connection.';

        this.logError({
            type: 'CONNECTION_ERROR',
            message: message,
            timestamp: new Date().toISOString()
        });

        this.notify.error('Connection Error', message);
    }

    /**
     * Handle timeout error
     */
    handleTimeoutError() {
        const message = 'Request timed out. Please try again.';

        this.logError({
            type: 'TIMEOUT_ERROR',
            message: message,
            timestamp: new Date().toISOString()
        });

        this.notify.error('Timeout Error', message);
    }

    /**
     * Log error for debugging
     * @param {Object} errorObj - Error object
     */
    logError(errorObj) {
        this.errors.push(errorObj);

        // Keep only last 100 errors
        if (this.errors.length > 100) {
            this.errors.shift();
        }

        // Log to console in development
        if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
            console.error('[ErrorHandler]', errorObj);
        }
    }

    /**
     * Get error history
     * @returns {Array} - Array of error objects
     */
    getErrorHistory() {
        return [...this.errors];
    }

    /**
     * Clear error history
     */
    clearErrorHistory() {
        this.errors = [];
    }
}

// Initialize global instances
const notify = new NotificationManager();
const loading = new LoadingManager();
const errorHandler = new ErrorHandler(notify);

// Export for use in other modules
if (typeof window !== 'undefined') {
    window.notify = notify;
    window.loading = loading;
    window.errorHandler = errorHandler;
}

console.log('[notifications.js] Sprint 3 Task 3.4 notification system initialized');
