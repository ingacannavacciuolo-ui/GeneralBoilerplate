/**
 * Modulo di gestione visiva e socket per la card di stato del Server
 */
const ServerStatusCard = {
    cardEl: null,
    textEl: null,
    connected: false,
    socket: null,

    init() {
        this.cardEl = document.getElementById('server-status-card');
        this.textEl = document.getElementById('server-status-text');
        //this.setDisconnected(); // Stato iniziale obbligatorio
    },

    // Riceve i dati inoltrati da AppSocketManager
    handleStatusUpdate(data) {
        console.log('[ServerStatusCard] Ricevuto aggiornamento stato via AppSocketManager:', data);

        const onlineValue = (typeof SERVICE_STATUS_STATES !== 'undefined' && SERVICE_STATUS_STATES.ONLINE) 
            ? SERVICE_STATUS_STATES.ONLINE 
            : 'ONLINE';

        if (data && data.status === onlineValue) {
            this.setConnected(SERVICE_STATUS_STATES_VIEW.CONNECT);
        } else {
            this.setDisconnected(SERVICE_STATUS_STATES_VIEW.DISCONNECT);
        }
    },

    setConnected(customText = SERVICE_STATUS_STATES_VIEW.CONNECT) {
        if (!this.cardEl || !this.textEl) return;
        
        this.connected = true;
        this.cardEl.classList.remove('status-disconnected');
        this.cardEl.classList.add('status-connected');        
        const statusText = window.lang(LANG_KEY.STATUS_CONNECTED, customText);
        this.textEl.textContent = statusText.toUpperCase();
    },

    setDisconnected(customText = SERVICE_STATUS_STATES_VIEW.DISCONNECT) {
        if (!this.cardEl || !this.textEl) return;

        this.connected = false;
        this.cardEl.classList.remove('status-connected');
        this.cardEl.classList.add('status-disconnected');
        const statusText = window.lang(LANG_KEY.STATUS_DISCONNECTED, customText);
        this.textEl.textContent = statusText.toUpperCase();
    },

    isOnline() {
        return this.connected;
    }
};

document.addEventListener('DOMContentLoaded', () => {
    ServerStatusCard.init();
});