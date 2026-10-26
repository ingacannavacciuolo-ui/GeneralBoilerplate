/**
 * Modulo di gestione visiva per le Card Allerte Server (Puro Renderer Grafico).
 * Non gestisce connessioni di rete: riceve i dati direttamente da AppSocketManager.
 */
const AlertServerCard = {
    /**
     * Mappatura dei contenitori DOM in base alla Severity dell'allerta.
     */
    containers: {
        CRITICAL: "container-critical-alerts", // Posizione Top Left
        WARNING:  "container-warning-alerts",  // Posizione Bottom Right
        INFO:     "container-info-alerts"      // Posizione Bottom Right
    },

    /**
     * Inizializzazione del componente visivo al caricamento della pagina.
     * La connessione socket è interamente delegata ad AppSocketManager.
     */
    init() {
        // Modulo puramente grafico: nessun ascoltatore di rete da inizializzare qui
    },

    /**
     * Renderizza una nuova card di allerta o ne aggiorna/rimuove una esistente.
     * 
     * @param {Object} data - Oggetto contenente i dati dell'allerta (notify_key, severity, message, is_active, permanent)
     */
    renderAlert(data) {
        if (!data || !data.notify_key) return;

        const cardId = `alert-${data.notify_key}`;

        // Management Quietanza: rimuove la card dal DOM se il backend la segnala come non più attiva
        if (data.is_active === false) {
            const existingCard = document.getElementById(cardId);
            if (existingCard) existingCard.remove();
            return;
        }

        const severity = (data.severity || NOTIFY_SEVERITY.INFO).toUpperCase();
        const cssClass = severity.toLowerCase();
        const containerId = this.containers[severity] || this.containers.INFO;
        const targetContainer = document.getElementById(containerId);

        if (!targetContainer) return;

        // Struttura HTML interna della card (coordinata con le classi CSS)
        const cardHTML = `
            <div class="alert-icon"></div>
            <div class="alert-content">
                <span class="alert-prefix"></span>
                <span class="alert-message">${data.message || ''}</span>
            </div>
            ${!data.permanent ? `<button class="alert-close-btn" onclick="document.getElementById('${cardId}').remove()">✕</button>` : ''}
        `;

        let card = document.getElementById(cardId);

        // Se la card esiste già, ne aggiorna stile e contenuto; altrimenti la crea e la appende
        if (card) {
            card.className = `alert-card-tech ${cssClass}`;
            card.innerHTML = cardHTML;
            if (card.parentElement.id !== containerId) {
                targetContainer.appendChild(card);
            }
        } else {
            card = document.createElement("div");
            card.id = cardId;
            card.className = `alert-card-tech ${cssClass}`;
            card.innerHTML = cardHTML;
            targetContainer.appendChild(card);
        }
    }
};

/**
 * Inizializzazione automatica del modulo visivo al termine del caricamento del DOM
 */
document.addEventListener('DOMContentLoaded', () => {
    AlertServerCard.init();
});