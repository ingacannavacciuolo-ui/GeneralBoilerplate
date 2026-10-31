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

            //this.socket.onAny((eventName, ...args) => {
            //    console.log(`[ANY SOCKET EVENT] Evento ricevuto: "${eventName}"`, args);
            //});

            // Legge il token dal meta tag HTML invece che dai cookie
            const metaToken = document.querySelector('meta[name="user-session-token"]')?.content;

            if (metaToken) {
                // Se il token è presente viene registrato nella sessione, tramile la chiamata
                // socket ad REGISTER_SESSION che si trova in web_receiver_socket.
                // La registrazione è fondamentale per inviare TOAST personalizzati per utente    
                console.log('[AppSocketManager] Token trovato. Registrazione sessione...');
                this.socket.emit(SOCKET_EVENTS.REGISTER_SESSION, { session_token: metaToken });
            } else {
                console.log('[AppSocketManager] Nessun token trovato nella pagina.');
            }
            // Emette l'evento GET_ACTIVE_ALERTS per chiedere al DB tutte le allerte attualmente attive
            // e mandarel all'utente connesso. La chiamata sta in web_receiver_socket
            this.socket.emit(SOCKET_EVENTS.GET_ACTIVE_ALERTS);
        });

        // 1. SOCKET_EVENTS.STATUS_UPDATE: Intercetta l'evento di aggiornamento stato operativo inviato dal backend (web_receiver_socket.py)
        //    Invocato da web_receiver_socket quando riceve notifica da parte di client_service_socket per inviare
        //    lo stato del server (CONNESSO O DISCONESSO)   
        this.socket.on(SOCKET_EVENTS.STATUS_UPDATE, (data) => this.routeMessage(data));


        // 2. SOCKET_EVENTS.ACTIVE_ALERTS_LIST: Intercetta la lista completa di allerte attive inviata dal DB (al refresh / login)
        //    Usato in fase di apertura della pagina da web_receiver_socket, per notificare 
        //    all'utente i messaggi di alert o di info attivi
        this.socket.on(SOCKET_EVENTS.ACTIVE_ALERTS_LIST, (alerts) => {
            console.log('[AppSocketManager] Ricevute allerte attive dal DB:', alerts);
            if (Array.isArray(alerts)) {
                alerts.forEach(alertData => {
                    alertData.msg_type = alertData.msg_type || MSG_SERVICE_SOCKET_TYPE.MSG_SERVICE_SEVERITY;
                    this.routeMessage(alertData);
                });
            }
        });     

        // 3.  SOCKET_EVENTS.SEVERITY_UPDATE: Ascolta il CANALE UNICO per tutte le allerte di severity in tempo reale
        //     Invocato da web_receiver_socket quando riceve notifica di alert da parte di system_monitor_worker.
        //     La connessione a web_receiver_socket, arriva tramite client_service_socket. 
        //     Le notifiche invocate sono CRITICA, WARNING ed INFO che si attivano nel database.
        this.socket.on(SOCKET_EVENTS.SEVERITY_UPDATE, (data) => {
            this.routeMessage(data);
        });


        // 4. SOCKET_EVENTS.USER_TOAST_UPDATE: Ascolta il CANALE UNICO per i toast utente in tempo reale
        this.socket.on(SOCKET_EVENTS.USER_TOAST_UPDATE, (data) => {
            //console.log("===> [DEBUG SOCKET] TOAST ARRIVATO AL CLIENT! <===", data);
            this.routeMessage(data);
        });

       
      

        // 5. Intercetta la disconnessione della rete WebSocket e notifica i componenti visuali
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
       if (!data) return;

        // Recupera il tipo di messaggio (con fallback per lo stato di servizio)
        const msgType = data.msg_type || (data.status ? MSG_SERVICE_SOCKET_TYPE.MSG_SERVICE_STATUS : null);
        if (!msgType) return;

        switch (msgType) {
            case MSG_SERVICE_SOCKET_TYPE.MSG_SERVICE_STATUS:
                // Consegna il pacchetto dati al modulo grafico ServerStatusCard
                if (typeof ServerStatusCard !== 'undefined' && typeof ServerStatusCard.handleStatusUpdate === 'function') {
                    ServerStatusCard.handleStatusUpdate(data);
                }
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
                    mostraToast(window.lang(data.message), data.notify_key);
                }
                break;

            default:
                // Per ora ignora gli altri msg_type non gestiti
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