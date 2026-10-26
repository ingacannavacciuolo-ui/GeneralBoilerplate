/**
 * Manager centralizzato Socket.IO - Gestione del canale di comunicazione e smistamento messaggi
 */
const AppSocketManager = {
    socket: null,

    /**
     * Inizializza la connessione WebSocket autonoma verso il namespace WEB.
     * Garantisce l'esistenza di un'unica istanza di connessione Socket.IO per l'intera pagina.
     */
    init() {
        if (this.socket) return;

        if (typeof io === 'undefined' || typeof SOCKET_NAMESPACES === 'undefined') {
            console.error('[AppSocketManager] Socket.IO o SOCKET_NAMESPACES non trovati.');
            return;
        }

        // Apre l'unica connessione WebSocket condivisa verso il server
        this.socket = io(SOCKET_NAMESPACES.WEB, {
            transports: ['websocket', 'polling'],
            reconnection: true,
            reconnectionDelay: 2000
        });

        this.initListeners();
    },

    /**
     * Configura tutti gli ascoltatori (listener) per gli eventi provenienti dal backend.
     * Intercetta i pacchetti di rete in ingresso e li inoltra al router di smistamento.
     */
    initListeners() {
        // Evento di avvio e stabilizzazione della connessione WebSocket
        this.socket.on('connect', () => {
            console.log(`[AppSocketManager] Connesso al namespace: ${SOCKET_NAMESPACES.WEB}`);
            this.socket.emit(SOCKET_EVENTS.GET_ACTIVE_ALERTS);
        });

        // Intercetta l'evento di aggiornamento stato operativo inviato dal backend (web_receiver_socket.py)
        this.socket.on(SOCKET_EVENTS.SERVICE_STATUS_UPDATE, (data) => this.routeMessage(data));

        // 1. Intercetta la lista completa di allerte attive inviata dal DB (al refresh / login)
        this.socket.on(SOCKET_EVENTS.ACTIVE_ALERTS_LIST, (alerts) => {
            console.log('[AppSocketManager] Ricevute allerte attive dal DB:', alerts);
            if (Array.isArray(alerts)) {
                alerts.forEach(alertData => {
                    alertData.msg_type = alertData.msg_type || MSG_SERVICE_SOCKET_TYPE.MSG_SERVICE_SEVERITY;
                    this.routeMessage(alertData);
                });
            }
        });     

        // Ascolta il CANALE UNICO per tutte le allerte di severity in tempo reale
        this.socket.on(MSG_SERVICE_SOCKET_TYPE.MSG_SERVICE_SEVERITY, (data) => {
            this.routeMessage(data);
        });


        // Ascolta il CANALE UNICO per i toast utente in tempo reale
        this.socket.on(MSG_SERVICE_SOCKET_TYPE.MSG_USER_TOAST, (data) => {
            this.routeMessage(data);
        });

       
      

        // Intercetta la disconnessione della rete WebSocket e notifica i componenti visuali
        this.socket.on('disconnect', () => {
            console.warn('[AppSocketManager] Disconnesso dal server.');
            if (typeof ServerStatusCard !== 'undefined' && typeof ServerStatusCard.setDisconnected === 'function') {
                ServerStatusCard.setDisconnected();
            }
        });
    },

    /**
     * Smistatore centrale (Router): analizza la proprietà `msg_type` presente nel payload JSON 
     * e decide a quale componente frontend (es. ServerStatusCard) consegnare i dati.
     * 
     * @param {Object} data - Il payload inviato dal server backend
     */
    routeMessage(data) {
       if (!data || !data.msg_type) return;

        // Recupera il tipo di messaggio (con fallback per lo stato di servizio)
        const msgType = data.msg_type || (data.status ? MSG_SERVICE_SOCKET_TYPE.MSG_SERVICE_STATUS : null);

        switch (msgType) {
            case MSG_SERVICE_SOCKET_TYPE.MSG_SERVICE_STATUS:
                // Consegna il pacchetto dati al modulo grafico ServerStatusCard
                if (typeof ServerStatusCard !== 'undefined' && typeof ServerStatusCard.handleStatusUpdate === 'function') {
                    ServerStatusCard.handleStatusUpdate(data);
                }
                break;

            default:
                // Per ora ignora gli altri msg_type non gestiti
                break;
            
            
            case MSG_SERVICE_SOCKET_TYPE.MSG_SERVICE_SEVERITY:
                // Identifica la pagina attiva tramite l'URL
                const path = window.location.pathname;
                const isLogin = (AlertServerCard !== undefined) && (path === '/' || path === '/login' || document.body.dataset.page === 'login'); 
                // ^ Adatta i path '/main_page' o '/home' in base alle tue rotte Flask reali

                if (isLogin) {
                     // Siamo sulla Login o in altre pagine: renderizza la card AlertServerCard
                    if (typeof AlertServerCard !== 'undefined' && typeof AlertServerCard.renderAlert === 'function') {
                        AlertServerCard.renderAlert(data);
                    }                  
                } else {
                     // Siamo sulla main_page: aggiorna le icone della Top Bar
                    if (typeof AlertTopBarIcon !== 'undefined' && typeof AlertTopBarIcon.updateIconState === 'function') {
                        AlertTopBarIcon.updateIconState(data);
                    }
                }
                break;

            case MSG_SERVICE_SOCKET_TYPE.MSG_USER_TOAST:
               // Invoca direttamente la funzione mostraToast di main_page.js
                if (typeof mostraToast === 'function') {
                    mostraToast(data.message, data.notify_key);
                }
                break;
        }
    }
};

/**
 * Inizializzazione automatica del manager centralizzato al termine del caricamento del DOM
 */
document.addEventListener('DOMContentLoaded', () => {
    AppSocketManager.init();
});