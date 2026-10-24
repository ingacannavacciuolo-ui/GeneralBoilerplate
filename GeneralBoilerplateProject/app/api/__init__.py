from .socket import (
    sio_app,
    init_socket_receiver,
    GeneralBoilerplateServiceClientSocket,
)
from .web import (
    pages_router, 
    get_auth_service, 
    get_current_user_session,
    setup_template_globals,
)

__all__ = [
    "studies_rest_router",
    "studies_socket_router",
    "sio_app",
    "init_socket_receiver",
    "GeneralBoilerplateServiceClientSocket",
    "pages_router",
    "get_auth_service",
    "get_current_user_session",
    "setup_template_globals",
]