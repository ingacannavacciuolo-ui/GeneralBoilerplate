# library/api/web/dependencies.py

import asyncio
from tkinter import NO
from typing import Dict, Any, Callable
from fastapi import Request, HTTPException, status, Depends
from fastapi.responses import RedirectResponse
from app.api.socket.web_receiver_socket import GeneralBoilerplateWebReceiverSocket
from app.services import AuthService
# Importiamo il receiver per poter accedere a get_sid_by_token
from app.api.socket import GeneralBoilerplateServiceClientSocket
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
                             user_sid,
                             socket_events,
                             application_name,
                             msg_type,
                             notify_error,
                             message_key):
    if sio_server:
        await sio_server.emit(
            socket_events,
            {
                "sender": application_name,
                "msg_type": msg_type,
                "notify_key": notify_error,                    
                "message": message_key
            },
            namespace=target_namespace,
            to=user_sid
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
    # Recuperiamo il SID della connessione Socket legato a questo token
    user_sid = GeneralBoilerplateWebReceiverSocket.get_sid_by_token(token)
    # CASO 1: Token di sessione assente
    if not token:
        await _send_notification(sio_server, 
                                  target_namespace, 
                                  user_sid,
                                  SOCKET_EVENTS.USER_TOAST_UPDATE,
                                  APPLICATION_NAME_SERVICE,
                                  MSG_SERVICE_SOCKET_TYPE.MSG_USER_TOAST,
                                  "error",
                                  LANG_KEY.ALERT_MISSING_TOKEN)  
        return None 
   

   # CASO 2: Token inviato ma sessione scaduta sul DB
    session_info = auth_service.validate_session(token)
    if not session_info:        
        await _send_notification(sio_server, 
                                  target_namespace, 
                                  user_sid,
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
            # Estraiamo il valore reale della costante
            error_value = getattr(NOTIFY_ERROR.INSUFFICIENT_PERMISSIONS, "value", NOTIFY_ERROR.INSUFFICIENT_PERMISSIONS)
            
            # Se la richiesta ha un Referer dello stesso dominio, inviamo un Toast via Socket se possibile
            token = request.cookies.get("session_token")
            user_sid = GeneralBoilerplateWebReceiverSocket.get_sid_by_token(token) if token else None
            sio_server = getattr(request.app.state, "sio", None)
            target_namespace = getattr(SOCKET_NAMESPACES.WEB, "value", SOCKET_NAMESPACES.WEB)
            
            if sio_server and user_sid:
                await _send_notification(sio_server, 
                                  target_namespace, 
                                  user_sid,
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
                redirect_url = f"{first_page_url}"#?reason={error_value}"

            return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)

        return user

    return permission_checker

