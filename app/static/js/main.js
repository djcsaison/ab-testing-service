/**
 * Main entry point for the A/B Testing dashboard
 */
document.addEventListener('DOMContentLoaded', () => {
    // Initialize the experiments manager
    const experimentsManager = new ExperimentsManager(api);
    
    // Add Bootstrap icons via CDN
    const iconLink = document.createElement('link');
    iconLink.rel = 'stylesheet';
    iconLink.href = 'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.8.1/font/bootstrap-icons.css';
    document.head.appendChild(iconLink);
    
    // Log initialization
    console.log('A/B Testing dashboard initialized');
});