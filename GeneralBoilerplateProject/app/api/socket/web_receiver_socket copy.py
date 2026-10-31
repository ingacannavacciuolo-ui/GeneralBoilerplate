import time
import socketio
from typing import Dict, Any, Optional
from app.core.logger import logger
from app.core.constants import (
    MSG_SERVICE_SOCKET_TYPE,
    SERVICE_STATUS_STATES,
    SOCKET_NAMESPACES,
    SOCKET_EVENTS,
    NOTIFY_KEY,    
    NOTIFY_SEVERITY,
    LANG_KEY,
    APPLICATION_NAME_SERVICE
)
from app.repository import AppNotificationWorkerRepo



# 1. Server Socket.IO asincrono (compatibile ASGI)
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*"
)

# App ASGI esportata per il montaggio su FastAPI
sio_app = socketio.ASGIApp(sio)


# Stato globale in memoria per monitorare lo stato del Service
class ServiceStatusState:
    last_heartbeat: float = 0
    status: str = SERVICE_STATUS_STATES.OFFLINE

status_state = ServiceStatusState()

# Mappa globale in memoria: session_token -> sid del browser
user_sockets: Dict[str, str] = {}


class GeneralBoilerplateWebReceiverSocket(socketio.AsyncNamespace):
    """
    Namespace Socket.IO dedicato alla ricezione delle notifiche, 
    heartbeat e cambi di stato provenienti da GeneralBoilerplateService.
    """
    def __init__(self, db_manager, lang: str = "it", fallback_lang: str = "en",):
        self.dbmanager = db_manager
        self.namespace = SOCKET_NAMESPACES.WEB
        self.service_sid = None  # Memorizza il SID di GeneralBoilerplateService
        self.lang = lang
        self.fallback_lang =fallback_lang
        super().__init__(self.namespace)

    @staticmethod
    def get_sid_by_token(token: str) -> Optional[str]:
        """Restituisce il SID del browser associato a un determinato session_token."""
        return user_sockets.get(token)

    async def on_connect(self, sid, environ):
        logger.info(f"[WEB SOCKET RECEIVER] Nuova connessione client [sid: {sid}]")
        
        # Verifichiamo se l'ultimo heartbeat è recente (es. ultimi 45 secondi)
        now = time.time()
        is_alive = (
            status_state.last_heartbeat > 0 
            and (now - status_state.last_heartbeat) < 45 
            and status_state.status == SERVICE_STATUS_STATES.ONLINE
        )
        
        current_status = SERVICE_STATUS_STATES.ONLINE if is_alive else SERVICE_STATUS_STATES.OFFLINE

        # Risponde SOLO al browser appena connesso con lo stato reale freschissimo
        await self.emit(
            SOCKET_EVENTS.STATUS_UPDATE,
            {
                "status": current_status,
                "message": LANG_KEY.SERVICE_STATUS_CURRENT_MSG
            },
            to=sid
        )

    async def on_register_session(self, sid, data: Dict[str, Any]):
        """Evento invocato dal frontend JS dopo il login per associare il session_token al sid."""
        if isinstance(data, dict):
            token = data.get("session_token")
            if token:
                user_sockets[token] = sid
                logger.info(f"[WEB SOCKET RECEIVER] Sessione associata con successo: [sid: {sid}]")


    async def on_message(self, sid, data: Dict[str, Any]):
        if not isinstance(data, dict):
            return
        
        # Registra il SID solo se il mittente è il servizio backend
        if data.get("sender") != APPLICATION_NAME_SERVICE:
            return

        self.service_sid = sid
        msg_type = data.get("msg_type")
       

        # Se si tratta dello stato del servizio, lo gestiamo tramite il tipo
        if msg_type == MSG_SERVICE_SOCKET_TYPE.MSG_SERVICE_STATUS:
            await self._handle_service_status(data)
        # Se si tratta dello stato di severity, lo gestiamo tramite il tipo
        elif msg_type == MSG_SERVICE_SOCKET_TYPE.MSG_SERVICE_SEVERITY:
            await self._handle_service_severity(data)
        elif msg_type == MSG_SERVICE_SOCKET_TYPE.MSG_USER_TOAST:
            await self._handle_user_toast(data)

    async def on_disconnect(self, sid):
        # Rimozione dell'associazione session_token -> sid
        tokens_to_remove = [k for k, v in user_sockets.items() if v == sid]
        for k in tokens_to_remove:
            del user_sockets[k]

        # SOLTANTO se a disconnettersi è il vero Service impostiamo OFFLINE e notifichiamo a tutti!
        if sid == self.service_sid:
            logger.warning(f"[WEB SOCKET RECEIVER] GeneralBoilerplateService disconnesso [sid: {sid}]")
            self.service_sid = None
            status_state.status = SERVICE_STATUS_STATES.OFFLINE

            await self.emit(
                SOCKET_EVENTS.STATUS_UPDATE,
                {
                    "msg_type": MSG_SERVICE_SOCKET_TYPE.MSG_SERVICE_STATUS,
                    "status": SERVICE_STATUS_STATES.OFFLINE,
                    "message": LANG_KEY.SERVICE_OFFLINE,
                    "timestamp": time.time(),
                }
            )
        else:
            # Se è la disconnessione di un browser (F5/Refresh), ignoriamo silenziosamente
            logger.info(f"[WEB SOCKET RECEIVER] Browser disconnesso [sid: {sid}] (nessun impatto sullo stato)")

   
    # Recupera tutti gli alert attivi per mandarli al browser
    async def on_get_active_alerts(self, sid):
        """
        Invocato quando un browser (incluso F5/refresh) richiede la lista 
        delle allerte attualmente attive nel DB.
        """
        logger.info(f"[WEB SOCKET RECEIVER] Richiesta allerte attive dal client [sid: {sid}]")
        try:
            with self.dbmanager.get_session() as session:
                # Usa il repository per recuperare le allerte con is_active = True
                repo = AppNotificationWorkerRepo(session)
                active_events = repo.get_active_notifications()  # o repo.get_all_active_notifications()

                alerts_data = []
                for event in active_events:
                    localized_msg = event.get_description(lang=self.lang, fallback_lang=self.fallback_lang)
                    alerts_data.append({
                        "sender": APPLICATION_NAME_SERVICE,
                        "msg_type": MSG_SERVICE_SOCKET_TYPE.MSG_SERVICE_SEVERITY,                        
                        "notify_key": event.notify_key,
                        "notify_type": event.notify_type,
                        "message":localized_msg,
                        "permanent": event.permanent,
                        "severity": event.severity,
                        "is_active": True,
                        "timestamp": time.time()
                    })

                # Invia la lista ESCLUSIVAMENTE al client richiedente (sid)
                await self.emit(SOCKET_EVENTS.ACTIVE_ALERTS_LIST, alerts_data, to=sid)
                logger.info(f"[WEB SOCKET RECEIVER] Inviate {len(alerts_data)} allerte attive al client [sid: {sid}]")

        except Exception as e:
            logger.error(f"[WEB SOCKET RECEIVER] Errore durante il recupero delle allerte attive per sid {sid}: {e}", exc_info=True)
   
   
    # --- HANDLER DEDICATI PER TIPOLOGIA MESSAGGIO ---  

    async def _handle_service_status(self, data: Dict[str, Any]):
        """Gestisce Heartbeat e stato operativo di GeneralBoilerplateService."""
        status_state.last_heartbeat = time.time()
        status_state.status = data.get("status", SERVICE_STATUS_STATES.OFFLINE)

        logger.info(f"[STATUS HANDLER] Service status: {status_state.status} | Msg: {data.get('message')}")
        # EMIT verso il client Web         
        await self.emit(SOCKET_EVENTS.STATUS_UPDATE, data)


    async def _handle_service_severity(self, data: Dict[str, Any]):
        """Gestisce l'invio unico di tutti gli avvisi di severity."""
        severity = str(data.get("severity", "INFO")).upper()
        notify_key = data.get("notify_key", NOTIFY_KEY.UNKNOWN_KEY)
        message = data.get("message", LANG_KEY.NO_DETAILS_PROVIDED)

        logger.info(f"[{severity} ALERT] Key: {notify_key} | Msg: {message}")

        # Emette sul singolo canale Socket unico per la severity
        await self.emit(SOCKET_EVENTS.SEVERITY_UPDATE, data)


    async def _handle_user_toast(self, data: Dict[str, Any]):
        """Gestisce l'invio di notifiche toast verso il browser."""
        notify_key = data.get("notify_key", NOTIFY_KEY.UNKNOWN_KEY)
        message = data.get("message", LANG_KEY.NO_DETAILS_PROVIDED)

        logger.info(f"[USER TOAST] Key: {notify_key} | Msg: {message}")

        # Emette sul singolo canale Socket unico per i toast
        await self.emit(SOCKET_EVENTS.USER_TOAST_UPDATE, data)



def init_socket_receiver(
        db_manager,
        lang: str = "it",
        fallback_lang: str = "en",
    ) -> GeneralBoilerplateWebReceiverSocket:
    """Inizializza e registra l'istanza del receiver Socket.IO."""
    receiver = GeneralBoilerplateWebReceiverSocket(db_manager, lang, fallback_lang)
    sio.register_namespace(receiver)
    return receiver