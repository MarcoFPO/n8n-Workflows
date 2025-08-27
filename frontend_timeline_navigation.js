/**
 * Frontend Timeline Navigation v1.0.0
 * JavaScript Implementation für 4-Zeitrahmen Timeline-Navigation
 * 
 * FEATURES:
 * - 4 Zeitrahmen: 1W, 1M, 3M, 1Y (12M) Navigation
 * - URL Parameter Tracking (nav_timestamp, nav_direction)
 * - State Management für Timeline-Position
 * - Smooth UI Transitions
 * - Error Handling und Fallbacks
 * - Mobile-responsive Design
 * 
 * CLEAN CODE PRINCIPLES:
 * - Single Responsibility: Timeline-Navigation Logik
 * - DRY (Don't Repeat Yourself): Wiederverwendbare Funktionen
 * - Error Handling: Graceful Degradation bei Fehlern
 * - Type Safety: JSDoc Kommentare für bessere IDE-Unterstützung
 * 
 * Autor: Claude Code
 * Datum: 27. August 2025
 * Version: 1.0.0
 */

// =============================================================================
// TIMELINE CONFIGURATION (Centralized)
// =============================================================================

/**
 * Timeline Configuration
 * @typedef {Object} TimeframeConfig
 * @property {string} display_name - Anzeigename
 * @property {number} days - Anzahl Tage
 * @property {string} icon - Icon für UI
 * @property {string} css_class - CSS-Klasse für Styling
 */
const TIMELINE_CONFIG = {
    '1W': {
        display_name: '1 Woche',
        days: 7,
        icon: '📊',
        css_class: 'timeframe-week'
    },
    '1M': {
        display_name: '1 Monat', 
        days: 30,
        icon: '📈',
        css_class: 'timeframe-month'
    },
    '3M': {
        display_name: '3 Monate',
        days: 90,
        icon: '📊',
        css_class: 'timeframe-quarter'
    },
    '1Y': {
        display_name: '12 Monate',
        days: 365,
        icon: '📈',
        css_class: 'timeframe-year'
    }
};

// =============================================================================
// TIMELINE STATE MANAGEMENT
// =============================================================================

/**
 * Timeline State Manager
 * Verwaltet den aktuellen Zustand der Timeline-Navigation
 */
class TimelineStateManager {
    constructor() {
        this.currentTimeframe = '1M';
        this.currentTimestamp = Math.floor(Date.now() / 1000);
        this.navigationHistory = [];
        
        // Initialize from URL parameters
        this.initializeFromURL();
        
        console.log('📊 Timeline State Manager initialized:', {
            timeframe: this.currentTimeframe,
            timestamp: this.currentTimestamp
        });
    }
    
    /**
     * Initialize state from URL parameters
     */
    initializeFromURL() {
        try {
            const urlParams = new URLSearchParams(window.location.search);
            
            // Get timeframe from URL
            const timeframeParam = urlParams.get('timeframe');
            if (timeframeParam && TIMELINE_CONFIG[timeframeParam]) {
                this.currentTimeframe = timeframeParam;
            }
            
            // Get navigation timestamp
            const timestampParam = urlParams.get('nav_timestamp');
            if (timestampParam && !isNaN(parseInt(timestampParam))) {
                this.currentTimestamp = parseInt(timestampParam);
            }
            
            // Get navigation direction for history
            const direction = urlParams.get('nav_direction');
            if (direction) {
                this.addToHistory(direction);
            }
            
        } catch (error) {
            console.warn('⚠️ Error initializing timeline from URL:', error);
        }
    }
    
    /**
     * Add navigation action to history
     * @param {string} direction - Navigation direction ('previous', 'next', 'jump')
     */
    addToHistory(direction) {
        this.navigationHistory.push({
            direction: direction,
            timestamp: this.currentTimestamp,
            timeframe: this.currentTimeframe,
            date: new Date(this.currentTimestamp * 1000)
        });
        
        // Keep only last 10 entries
        if (this.navigationHistory.length > 10) {
            this.navigationHistory.shift();
        }
    }
    
    /**
     * Get current state as object
     * @returns {Object} Current timeline state
     */
    getCurrentState() {
        return {
            timeframe: this.currentTimeframe,
            timestamp: this.currentTimestamp,
            date: new Date(this.currentTimestamp * 1000),
            config: TIMELINE_CONFIG[this.currentTimeframe],
            history: [...this.navigationHistory]
        };
    }
    
    /**
     * Update current state
     * @param {string} timeframe - New timeframe
     * @param {number} timestamp - New timestamp
     */
    updateState(timeframe, timestamp) {
        this.currentTimeframe = timeframe;
        this.currentTimestamp = timestamp;
        
        console.log('📊 Timeline state updated:', {
            timeframe: timeframe,
            timestamp: timestamp,
            date: new Date(timestamp * 1000).toISOString()
        });
    }
}

// Global Timeline State Manager
const timelineState = new TimelineStateManager();

// =============================================================================
// TIMELINE NAVIGATION FUNCTIONS
// =============================================================================

/**
 * Navigate timeline in specified direction
 * @param {string} direction - Direction ('previous', 'next')
 * @param {string} timeframe - Target timeframe
 * @param {string} [pageType='prognosen'] - Type of page (prognosen, vergleichsanalyse)
 */
function navigateTimeline(direction, timeframe, pageType = 'prognosen') {
    try {
        console.log(`🧭 Navigating ${direction} for timeframe ${timeframe} on page ${pageType}`);
        
        // Validate inputs
        if (!['previous', 'next'].includes(direction)) {
            throw new Error(`Invalid direction: ${direction}`);
        }
        
        if (!TIMELINE_CONFIG[timeframe]) {
            throw new Error(`Invalid timeframe: ${timeframe}`);
        }
        
        // Calculate new timestamp
        const timeframeConfig = TIMELINE_CONFIG[timeframe];
        const daysToAdd = direction === 'next' ? timeframeConfig.days : -timeframeConfig.days;
        
        const currentDate = new Date(timelineState.currentTimestamp * 1000);
        currentDate.setDate(currentDate.getDate() + daysToAdd);
        const newTimestamp = Math.floor(currentDate.getTime() / 1000);
        
        // Update state
        timelineState.updateState(timeframe, newTimestamp);
        timelineState.addToHistory(direction);
        
        // Show loading indicator
        showNavigationLoading(direction, timeframe);
        
        // Build new URL
        const newUrl = buildNavigationURL(pageType, timeframe, newTimestamp, direction);
        
        // Navigate to new URL
        console.log('🔄 Navigating to:', newUrl);
        window.location.href = newUrl;
        
    } catch (error) {
        console.error('❌ Error in navigateTimeline:', error);
        showNavigationError(error.message);
    }
}

/**
 * Navigate to specific timeframe without direction
 * @param {string} timeframe - Target timeframe
 * @param {string} [pageType='prognosen'] - Type of page
 */
function loadTimeframe(timeframe, pageType = 'prognosen') {
    try {
        console.log(`📊 Loading timeframe ${timeframe} on page ${pageType}`);
        
        if (!TIMELINE_CONFIG[timeframe]) {
            throw new Error(`Invalid timeframe: ${timeframe}`);
        }
        
        // Reset to current time for new timeframe
        const currentTimestamp = Math.floor(Date.now() / 1000);
        
        // Update state
        timelineState.updateState(timeframe, currentTimestamp);
        timelineState.addToHistory('jump');
        
        // Build URL without navigation parameters (fresh load)
        const newUrl = `/${pageType}?timeframe=${timeframe}`;
        
        console.log('🔄 Loading timeframe:', newUrl);
        window.location.href = newUrl;
        
    } catch (error) {
        console.error('❌ Error in loadTimeframe:', error);
        showNavigationError(error.message);
    }
}

/**
 * Build navigation URL with parameters
 * @param {string} pageType - Type of page
 * @param {string} timeframe - Timeframe
 * @param {number} timestamp - Navigation timestamp
 * @param {string} direction - Navigation direction
 * @returns {string} Complete URL
 */
function buildNavigationURL(pageType, timeframe, timestamp, direction) {
    const baseUrl = `/${pageType}`;
    const params = new URLSearchParams({
        timeframe: timeframe,
        nav_timestamp: timestamp.toString(),
        nav_direction: direction
    });
    
    return `${baseUrl}?${params.toString()}`;
}

// =============================================================================
// UI FEEDBACK FUNCTIONS
// =============================================================================

/**
 * Show loading indicator during navigation
 * @param {string} direction - Navigation direction
 * @param {string} timeframe - Current timeframe
 */
function showNavigationLoading(direction, timeframe) {
    try {
        const timeframeConfig = TIMELINE_CONFIG[timeframe];
        const loadingMessage = `${timeframeConfig.icon} ${direction === 'next' ? 'Vor' : 'Zurück'} - ${timeframeConfig.display_name}...`;
        
        // Create or update loading element
        let loadingElement = document.getElementById('timeline-loading');
        if (!loadingElement) {
            loadingElement = document.createElement('div');
            loadingElement.id = 'timeline-loading';
            loadingElement.style.cssText = `
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: rgba(0, 123, 255, 0.9);
                color: white;
                padding: 20px 40px;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                z-index: 9999;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
                animation: pulse 1.5s ease-in-out infinite alternate;
            `;
            
            // Add CSS animation if not exists
            if (!document.getElementById('timeline-loading-style')) {
                const style = document.createElement('style');
                style.id = 'timeline-loading-style';
                style.textContent = `
                    @keyframes pulse {
                        from { opacity: 0.7; }
                        to { opacity: 1; }
                    }
                `;
                document.head.appendChild(style);
            }
            
            document.body.appendChild(loadingElement);
        }
        
        loadingElement.textContent = loadingMessage;
        loadingElement.style.display = 'block';
        
        // Auto-hide after 5 seconds as fallback
        setTimeout(() => {
            if (loadingElement && loadingElement.parentNode) {
                loadingElement.style.display = 'none';
            }
        }, 5000);
        
    } catch (error) {
        console.warn('⚠️ Error showing navigation loading:', error);
    }
}

/**
 * Hide loading indicator
 */
function hideNavigationLoading() {
    try {
        const loadingElement = document.getElementById('timeline-loading');
        if (loadingElement) {
            loadingElement.style.display = 'none';
        }
    } catch (error) {
        console.warn('⚠️ Error hiding navigation loading:', error);
    }
}

/**
 * Show navigation error message
 * @param {string} message - Error message
 */
function showNavigationError(message) {
    try {
        console.error('❌ Navigation Error:', message);
        
        // Create error notification
        const errorElement = document.createElement('div');
        errorElement.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #dc3545;
            color: white;
            padding: 15px 20px;
            border-radius: 5px;
            font-size: 14px;
            z-index: 10000;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            max-width: 300px;
        `;
        errorElement.innerHTML = `
            <strong>⚠️ Timeline Navigation Fehler</strong><br>
            ${message}
        `;
        
        document.body.appendChild(errorElement);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (errorElement && errorElement.parentNode) {
                errorElement.remove();
            }
        }, 5000);
        
    } catch (error) {
        console.error('❌ Error showing navigation error:', error);
        // Fallback to alert if DOM manipulation fails
        alert(`Timeline Navigation Fehler: ${message}`);
    }
}

// =============================================================================
// SPECIFIC PAGE NAVIGATION FUNCTIONS
// =============================================================================

/**
 * Navigation für KI-Prognosen Seite
 * @param {string} direction - Navigation direction
 * @param {string} timeframe - Current timeframe
 */
function navigatePrognosen(direction, timeframe) {
    navigateTimeline(direction, timeframe, 'prognosen');
}

/**
 * Load Prognosen für spezifischen Zeitrahmen
 * @param {string} timeframe - Target timeframe
 */
function loadPrognosen(timeframe) {
    loadTimeframe(timeframe, 'prognosen');
}

/**
 * Navigation für SOLL-IST Vergleichsanalyse
 * @param {string} direction - Navigation direction  
 * @param {string} timeframe - Current timeframe
 */
function navigateVergleichsanalyse(direction, timeframe) {
    navigateTimeline(direction, timeframe, 'vergleichsanalyse');
}

/**
 * Load Vergleichsanalyse für spezifischen Zeitrahmen
 * @param {string} timeframe - Target timeframe
 */
function loadVergleichsanalyse(timeframe) {
    loadTimeframe(timeframe, 'vergleichsanalyse');
}

// =============================================================================
// TIMELINE UI COMPONENTS
// =============================================================================

/**
 * Generate timeline navigation HTML
 * @param {string} currentTimeframe - Currently selected timeframe
 * @param {Object} navigationPeriods - Navigation periods data
 * @param {string} pageType - Page type for navigation functions
 * @returns {string} HTML string for timeline navigation
 */
function generateTimelineNavigationHTML(currentTimeframe, navigationPeriods, pageType = 'prognosen') {
    try {
        const config = TIMELINE_CONFIG[currentTimeframe];
        const navFunction = pageType === 'vergleichsanalyse' ? 'navigateVergleichsanalyse' : 'navigatePrognosen';
        
        return `
            <div class="timeline-navigation" style="display: flex; justify-content: space-between; align-items: center; margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #007bff;">
                <button onclick="${navFunction}('previous', '${currentTimeframe}')" 
                        class="timeline-nav-btn timeline-nav-previous"
                        style="background: #6c757d; color: white; border: none; padding: 8px 16px; border-radius: 5px; cursor: pointer; font-size: 14px; transition: all 0.3s ease;"
                        onmouseover="this.style.background='#5a6268'"
                        onmouseout="this.style.background='#6c757d'">
                    ⬅️ Zurück (${navigationPeriods.previous})
                </button>
                
                <div style="text-align: center;">
                    <strong>${navigationPeriods.nav_info}</strong><br>
                    <span style="color: #007bff; font-size: 16px; font-weight: bold;">${navigationPeriods.current}</span>
                    ${navigationPeriods.nav_timestamp ? '<div style="margin-top: 5px;"><small style="color: #007bff;">✅ Navigation erfolgreich</small></div>' : ''}
                </div>
                
                <button onclick="${navFunction}('next', '${currentTimeframe}')" 
                        class="timeline-nav-btn timeline-nav-next"
                        style="background: #007bff; color: white; border: none; padding: 8px 16px; border-radius: 5px; cursor: pointer; font-size: 14px; transition: all 0.3s ease;"
                        onmouseover="this.style.background='#0056b3'"
                        onmouseout="this.style.background='#007bff'">
                    Vor (${navigationPeriods.next}) ➡️
                </button>
            </div>
        `;
    } catch (error) {
        console.error('❌ Error generating timeline navigation HTML:', error);
        return '<div class="alert alert-danger">⚠️ Timeline Navigation konnte nicht geladen werden</div>';
    }
}

/**
 * Generate timeframe selector HTML
 * @param {string} currentTimeframe - Currently selected timeframe
 * @param {string} pageType - Page type for load functions
 * @returns {string} HTML string for timeframe selector
 */
function generateTimeframeSelectorHTML(currentTimeframe, pageType = 'prognosen') {
    try {
        const loadFunction = pageType === 'vergleichsanalyse' ? 'loadVergleichsanalyse' : 'loadPrognosen';
        let buttonsHTML = '';
        
        Object.entries(TIMELINE_CONFIG).forEach(([timeframe, config]) => {
            const isActive = timeframe === currentTimeframe;
            const buttonClass = isActive ? 'btn-primary' : 'btn-outline-primary';
            
            buttonsHTML += `
                <button class="btn ${buttonClass} timeframe-selector-btn" 
                        onclick="${loadFunction}('${timeframe}')"
                        data-timeframe="${timeframe}"
                        style="margin: 0 5px; transition: all 0.3s ease;"
                        ${isActive ? 'disabled' : ''}>
                    ${config.icon} ${config.display_name}
                </button>
            `;
        });
        
        return `
            <div class="timeframe-selector" style="margin: 20px 0;">
                <h3>🔧 Zeitintervall auswählen</h3>
                <div class="btn-group" style="display: flex; flex-wrap: wrap; gap: 5px;">
                    ${buttonsHTML}
                </div>
            </div>
        `;
    } catch (error) {
        console.error('❌ Error generating timeframe selector HTML:', error);
        return '<div class="alert alert-danger">⚠️ Zeitintervall-Auswahl konnte nicht geladen werden</div>';
    }
}

// =============================================================================
// INITIALIZATION AND EVENT LISTENERS
// =============================================================================

/**
 * Initialize timeline navigation when DOM is ready
 */
function initializeTimelineNavigation() {
    try {
        console.log('🚀 Initializing Timeline Navigation v1.0.0');
        
        // Hide any loading indicators from previous navigation
        hideNavigationLoading();
        
        // Log current state
        const currentState = timelineState.getCurrentState();
        console.log('📊 Current Timeline State:', currentState);
        
        // Add keyboard navigation support
        addKeyboardNavigationSupport();
        
        // Add responsive behavior
        addResponsiveBehavior();
        
        console.log('✅ Timeline Navigation initialized successfully');
        
    } catch (error) {
        console.error('❌ Error initializing timeline navigation:', error);
    }
}

/**
 * Add keyboard navigation support
 */
function addKeyboardNavigationSupport() {
    try {
        document.addEventListener('keydown', function(event) {
            // Only handle if no input is focused
            if (document.activeElement.tagName === 'INPUT' || document.activeElement.tagName === 'TEXTAREA') {
                return;
            }
            
            const currentState = timelineState.getCurrentState();
            const pageType = window.location.pathname.includes('vergleichsanalyse') ? 'vergleichsanalyse' : 'prognosen';
            
            switch (event.key) {
                case 'ArrowLeft':
                    event.preventDefault();
                    navigateTimeline('previous', currentState.timeframe, pageType);
                    break;
                case 'ArrowRight':
                    event.preventDefault();
                    navigateTimeline('next', currentState.timeframe, pageType);
                    break;
                case '1':
                    event.preventDefault();
                    loadTimeframe('1W', pageType);
                    break;
                case '2':
                    event.preventDefault();
                    loadTimeframe('1M', pageType);
                    break;
                case '3':
                    event.preventDefault();
                    loadTimeframe('3M', pageType);
                    break;
                case '4':
                    event.preventDefault();
                    loadTimeframe('1Y', pageType);
                    break;
            }
        });
        
        console.log('⌨️ Keyboard navigation support added');
    } catch (error) {
        console.warn('⚠️ Error adding keyboard navigation support:', error);
    }
}

/**
 * Add responsive behavior for mobile devices
 */
function addResponsiveBehavior() {
    try {
        // Add touch swipe support for mobile
        let touchStartX = 0;
        let touchEndX = 0;
        
        document.addEventListener('touchstart', function(event) {
            touchStartX = event.changedTouches[0].screenX;
        });
        
        document.addEventListener('touchend', function(event) {
            touchEndX = event.changedTouches[0].screenX;
            handleSwipe();
        });
        
        function handleSwipe() {
            const swipeThreshold = 50;
            const diff = touchStartX - touchEndX;
            
            if (Math.abs(diff) > swipeThreshold) {
                const currentState = timelineState.getCurrentState();
                const pageType = window.location.pathname.includes('vergleichsanalyse') ? 'vergleichsanalyse' : 'prognosen';
                
                if (diff > 0) {
                    // Swipe left - go to next
                    navigateTimeline('next', currentState.timeframe, pageType);
                } else {
                    // Swipe right - go to previous
                    navigateTimeline('previous', currentState.timeframe, pageType);
                }
            }
        }
        
        console.log('📱 Mobile swipe navigation support added');
    } catch (error) {
        console.warn('⚠️ Error adding responsive behavior:', error);
    }
}

// =============================================================================
// AUTO-INITIALIZATION
// =============================================================================

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeTimelineNavigation);
} else {
    initializeTimelineNavigation();
}

// Export functions for global access (if needed)
if (typeof window !== 'undefined') {
    window.TimelineNavigation = {
        navigateTimeline,
        loadTimeframe,
        navigatePrognosen,
        loadPrognosen,
        navigateVergleichsanalyse,
        loadVergleichsanalyse,
        generateTimelineNavigationHTML,
        generateTimeframeSelectorHTML,
        timelineState,
        TIMELINE_CONFIG
    };
}

console.log('🌟 Frontend Timeline Navigation v1.0.0 loaded successfully');
console.log('📊 Available timeframes:', Object.keys(TIMELINE_CONFIG));
console.log('⌨️ Keyboard shortcuts: ← → (navigation), 1-4 (timeframes)');
console.log('📱 Mobile: Swipe left/right for navigation');