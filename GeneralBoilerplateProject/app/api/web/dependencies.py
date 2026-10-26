# library/api/web/dependencies.py

from tkinter import NO
from typing import Dict, Any, Callable
from fastapi import Request, HTTPException, status, Depends
from fastapi.responses import RedirectResponse
from app.services import AuthService
from app.core.constants import (
    LANG_KEY,
    NOTIFY_ERROR,
    SOCKET_NAMESPACES,
    SYSTEM_SETTING_KEY,
    GENERAL_BOILERPLATE_WEB_FIRST_PAGE_DEFAULT,
    APPLICATION_NAME_SERVICE,
    MSG_SERVICE_SOCKET_TYPE
)

def get_auth_service(request: Request) -> AuthService:
    """Istanzia AuthService utilizzando il DatabaseManager presente nello stato dell'app."""
    return AuthService(request.app.state.repo_container)


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

   # CASO 1: Token di sessione assente
    if not token:
        if sio_server:
            await sio_server.emit(
                MSG_SERVICE_SOCKET_TYPE.MSG_USER_TOAST,
                {
                    "sender": APPLICATION_NAME_SERVICE,
                    "msg_type": MSG_SERVICE_SOCKET_TYPE.MSG_USER_TOAST,
                    "notify_key": "error",                    
                    "message": LANG_KEY.ALERT_MISSING_TOKEN
                },
                namespace=SOCKET_NAMESPACES.WEB
            )
        return None

   # CASO 2: Token inviato ma sessione scaduta sul DB
    session_info = auth_service.validate_session(token)
    if not session_info:
        if sio_server:
            await sio_server.emit(
                 MSG_SERVICE_SOCKET_TYPE.MSG_USER_TOAST,
                {
                    "sender": APPLICATION_NAME_SERVICE,
                    "msg_type": MSG_SERVICE_SOCKET_TYPE.MSG_USER_TOAST,
                    "notify_key": "error",                    
                    "message": LANG_KEY.ALERT_SESSION_EXPIRED
                },
                namespace=SOCKET_NAMESPACES.WEB
            )
        return None

    return session_info


def require_permission(permission_name: str) -> Callable:
    async def permission_checker(
        request: Request,
        user: Dict[str, Any] = Depends(get_current_user_session)
    ) -> Dict[str, Any]:
        user_permissions = user.get("permissions", [])
        
        if permission_name not in user_permissions:
            # Estraiamo il valore reale della costante
            error_value = getattr(NOTIFY_ERROR.INSUFFICIENT_PERMISSIONS, "value", NOTIFY_ERROR.INSUFFICIENT_PERMISSIONS)
            
            referer = request.headers.get("Referer")
            
            if referer and request.base_url._url in referer:
                base_referer = referer.split("?")[0]
                redirect_url = f"{base_referer}?reason={error_value}"
            else:
                repo_container = request.app.state.repo_container
                first_page_url = repo_container.appsystemsettingsrepo.get_setting_value(
                    SYSTEM_SETTING_KEY.WEB_FIRST_PAGE, default_value=GENERAL_BOILERPLATE_WEB_FIRST_PAGE_DEFAULT
                )
                redirect_url = f"{first_page_url}?reason={error_value}"

            return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)

        return user

    return permission_checker