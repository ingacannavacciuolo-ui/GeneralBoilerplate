/**
 * Helper globale per la localizzazione (i18n) lato client
 */
window.lang = function(key, defaultValue = "it") {
    if (window.langRANSLATIONS && window.langRANSLATIONS[key]) {
        return window.langRANSLATIONS[key];
    }
    return defaultValue || key;
};