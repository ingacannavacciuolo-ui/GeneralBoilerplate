/* ==========================================================================
   MAIN_PAGE.JS - Gestione Top Bar, Allerte (AlertTopBarIcon) e Interfaccia
   ========================================================================== */

// --------------------------------------------------------------------------
// OGGETTO GLOBALE: AlertTopBarIcon
// Invocato direttamente da app_socket_manager.js tramite:
// AlertTopBarIcon.updateIconState(data);
// --------------------------------------------------------------------------
window.AlertTopBarIcon = {
    // Traccia le allerte correnti suddivise per severità
    alertsData: {
        critical: [],
        warning: [],
        info: []
    },

    /**
     * Metodo principale richiamato da app_socket_manager.js per ogni alert dal DB
     * @param {Object} alertData - Oggetto contenente i dettagli dell'alert
     */
    updateIconState: function(alertData) {
        if (!alertData) return;

        // Normalizza la severità (es. 'critical', 'warning', 'info')
        const severity = (alertData.severity || alertData.level || alertData.msg_type || 'info').toLowerCase();

        if (this.alertsData.hasOwnProperty(severity)) {
            // Controlla se l'alert è già presente per evitare duplicati (se ha un id univoco)
            const exists = alertData.id && this.alertsData[severity].some(a => a.id === alertData.id);
            if (!exists) {
                this.alertsData[severity].push(alertData);
            }

            // Renderizza l'alert nel rispettivo container dropdown
            this.renderAlertCard(severity, alertData);

            // Aggiorna lo stato dell'icona (ON/OFF) e il contatore
            this.refreshIconUI(severity);
        }
    },

    /**
     * Rimuove o risolve un alert specifico
     * @param {string} severity - 'critical' | 'warning' | 'info'
     * @param {string|number} alertId - ID dell'alert da rimuovere
     */
    removeAlert: function(severity, alertId) {
        if (this.alertsData[severity]) {
            this.alertsData[severity] = this.alertsData[severity].filter(a => a.id !== alertId);
            
            // Rimuove la card dal DOM
            const cardEl = document.getElementById(`alert-card-${alertId}`);
            if (cardEl) {
                cardEl.remove();
            }

            // Aggiorna lo stato visivo visibilità badge
            this.refreshIconUI(severity);
        }
    },

    /**
     * Resetta tutti gli alert di una determinata categoria
     * @param {string} severity 
     */
    clearAll: function(severity) {
        if (this.alertsData[severity]) {
            this.alertsData[severity] = [];
            const container = document.getElementById(`container-${severity}-alerts`);
            if (container) {
                container.innerHTML = '';
            }
            this.refreshIconUI(severity);
        }
    },

    /**
     * Aggiorna contatore visivo e classe .off/accensione per la tipologia indicata
     * @param {string} severity 
     */
    refreshIconUI: function(severity) {
        const wrapper = document.getElementById(`wrapper-${severity}`);
        const countSpan = document.getElementById(`count-${severity}`);

        if (!wrapper || !countSpan) return;

        const count = this.alertsData[severity].length;
        
        // Aggiorna la cifra visibile
        countSpan.innerText = count;

        if (count > 0) {
            // Se c'è almeno 1 alert accende l'icona rimuovendo .off (attiva colori neon e glow)
            wrapper.classList.remove('off');
        } else {
            // Se 0 alert ripristina lo stato spento (.off) grigio opaco
            wrapper.classList.add('off');
        }
    },

    /**
     * Renderizza dinamicamente una card all'interno del dropdown corrispondente
     * @param {string} severity 
     * @param {Object} alertData 
     */
    renderAlertCard: function(severity, alertData) {
        const container = document.getElementById(`container-${severity}-alerts`);
            if (!container) return;

            const card = document.createElement('div');
            // Usa le classi ufficiali ereditate da alert_server_card.css
            card.className = `alert-card-tech ${severity}`;
            if (alertData.id) card.id = `alert-card-${alertData.id}`;

            const message = alertData.message || alertData.text || 'Nessun dettaglio specificato';

            // Generazione HTML permanente (SENZA tasto chiusura)
            card.innerHTML = `
                <div class="alert-icon"></div>
                <div class="alert-content">
                    <span class="alert-prefix"></span>
                    <span class="alert-message">${message}</span>
                </div>
            `;

            // Inserisce in cima alla lista nel dropdown
            container.insertBefore(card, container.firstChild);
    }
};

// --------------------------------------------------------------------------
// INIZIALIZZAZIONE AL CARICAMENTO DELLA PAGINA
// --------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
    // Inizializza tutte e tre le icone nello stato di default (.off)
    ['critical', 'warning', 'info'].forEach(severity => {
        AlertTopBarIcon.refreshIconUI(severity);
    });

    console.log('[MainPage] Inizializzata gestione AlertTopBarIcon in stato .off di default.');
});

// ==========================================================================
// 3. FUNZIONE GLOBALE PER MOSTRARE NOTIFICHE TOAST
// ==========================================================================
function mostraToast(messaggio, tipo = 'success') {
    let container = document.getElementById('toast-container');
    
    // Se per qualsiasi motivo il contenitore non esiste ancora, lo crea al volo nel body
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        document.body.appendChild(container);
    }

    // Crea l'elemento toast
    const toast = document.createElement('div');
    toast.className = `toast ${tipo}`;

    // Span dedicato al messaggio
    const msgSpan = document.createElement('span');
    msgSpan.className = 'toast-message';
    msgSpan.innerText = messaggio;
    toast.appendChild(msgSpan);

    container.appendChild(toast);

    // Rimuove automaticamente il toast dopo 5 secondi
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => {
            toast.remove();
        }, 500);
    }, 4000);
}