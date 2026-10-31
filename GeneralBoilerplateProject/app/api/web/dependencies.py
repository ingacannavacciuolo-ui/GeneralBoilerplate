# library/api/web/dependencies.py

import asyncio
from typing import Dict, Any, Callable
from fastapi import Request, status, Depends
from fastapi.responses import RedirectResponse
from app.services import AuthService
from app.core.constants import (
    LANG_KEY,
    NOTIFY_ERROR,
    SOCKET_NAMESPACES,
    SOCKET_EVENTS,
    SYSTEM_SETTING_KEY,
    GENERAL_BOILERPLATE_WEB_FIRST_PAGE_DEFAULT,
    APPLICATION_NAME_SERVICE,
    MSG_SERVICE_SOCKET_TYPE
)

def get_auth_service(request: Request) -> AuthService:
    """Istanzia AuthService utilizzando il DatabaseManager presente nello stato dell'app."""
    return AuthService(request.app.state.repo_container)

async def _send_notification(sio_server, 
                             target_namespace, 
                             room_token,
                             socket_events,
                             application_name,
                             msg_type,
                             notify_error,
                             message_key):
    """
    Invia una notifica Socket.IO puntando alla Room identificata dal room_token (session_token).
    """
    if sio_server and room_token:
        await sio_server.emit(
            socket_events,
            {
                "sender": application_name,
                "msg_type": msg_type,
                "notify_key": notify_error,                    
                "message": message_key
            },
            namespace=target_namespace,
            to=room_token  # <--- Emesso verso la Room dell'utente su Redis!
        )
        await asyncio.sleep(2.5)
    

async def get_current_user_session(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service)
) -> Dict[str, Any]:
    """
    Dipendenza FastAPI per proteggere le rotte web.
    Estrae il cookie 'session_token', ne esegue la validazione e il rinnovo 
    su app_users_sessions e restituisce i dettagli dell'utente con i permessi.
    """
    token = request.cookies.get("session_token")

    # Fallback per chiamate API con header Authorization: Bearer <token>
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

    # Recuperiamo l'istanza di socketio.AsyncServer già registrata in app.state.sio
    sio_server = getattr(request.app.state, "sio", None)
    target_namespace = getattr(SOCKET_NAMESPACES.WEB, "value", SOCKET_NAMESPACES.WEB)

    # CASO 1: Token di sessione assente
    if not token:
        # Senza token non c'è una room a cui inviare il toast
        return None 
   
    # CASO 2: Token inviato ma sessione scaduta/non valida sul DB
    session_info = auth_service.validate_session(token)
    if not session_info:        
        await _send_notification(sio_server, 
                                  target_namespace, 
                                  token,  # <--- Passiamo il token come identificatore di Room
                                  SOCKET_EVENTS.USER_TOAST_UPDATE,
                                  APPLICATION_NAME_SERVICE,
                                  MSG_SERVICE_SOCKET_TYPE.MSG_USER_TOAST,
                                  "error",
                                  LANG_KEY.ALERT_SESSION_EXPIRED) 
        return None  

    return session_info


def require_permission(permission_name: str) -> Callable:
    async def permission_checker(
        request: Request,
        user: Dict[str, Any] = Depends(get_current_user_session)
    ) -> Dict[str, Any]:
        # Se l'utente non è autenticato (es. sessione scaduta)
        if not user:
            return RedirectResponse(url="/?reason=" + NOTIFY_ERROR.SESSION_EXPIRED, status_code=status.HTTP_303_SEE_OTHER)

        user_permissions = user.get("permissions", [])
        
        if permission_name not in user_permissions:
            error_value = getattr(NOTIFY_ERROR.INSUFFICIENT_PERMISSIONS, "value", NOTIFY_ERROR.INSUFFICIENT_PERMISSIONS)
            
            token = request.cookies.get("session_token")
            sio_server = getattr(request.app.state, "sio", None)
            target_namespace = getattr(SOCKET_NAMESPACES.WEB, "value", SOCKET_NAMESPACES.WEB)
            
            # Se abbiamo un token e il server socket, inviamo il toast alla Room del token
            if sio_server and token:
                await _send_notification(sio_server, 
                                  target_namespace, 
                                  token,  # <--- Invia alla Room utente
                                  SOCKET_EVENTS.USER_TOAST_UPDATE,
                                  APPLICATION_NAME_SERVICE,
                                  MSG_SERVICE_SOCKET_TYPE.MSG_USER_TOAST,
                                  "warning",
                                  LANG_KEY.ALERT_INSUFFICIENT_PERMISSIONS)               

            referer = request.headers.get("Referer")
            if referer and request.base_url._url in referer:
                base_referer = referer.split("?")[0]
                redirect_url = f"{base_referer}?reason={error_value}"
            else:
                repo_container = request.app.state.repo_container
                first_page_url = repo_container.appsystemsettingsrepo.get_setting_value(
                    SYSTEM_SETTING_KEY.WEB_FIRST_PAGE, default_value=GENERAL_BOILERPLATE_WEB_FIRST_PAGE_DEFAULT
                )
                redirect_url = f"{first_page_url}"

            return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)

        return user

    return permission_checker