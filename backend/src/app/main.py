import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


from app.data_access import DataAccess
from app.config import get_cors_origins
from app.controller.auth_router import router as auth_router
from app.controller.agent_router import router as agent_router
from app.controller.terminal_router import router as session_router
from app.controller.computer_router import router as computer_router
from app.controller.files_router import router as files_router
from app.controller.user_router import router as user_router
from app.controller.tool_approval_router import router as tool_approval_router
from app.controller.tool_client_router import router as tool_client_router

from app.modules.terminal.terminal_service import terminal_session_service
from app.modules.computer.computer_service import computer_session_service



@asynccontextmanager
async def lifespan(app: FastAPI):
    terminal_session_service.start()
    computer_session_service.start()
    try:
        yield
    finally:
        terminal_session_service.shutdown()
        computer_session_service.shutdown()


app = FastAPI(
    title="BBAgent",
    lifespan=lifespan,
    swagger_ui_parameters={
        "supportedSubmitMethods": []
    }
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

data_base = os.getenv("DATABASE_PATH")
# configura la base de datos una vez al arrancar
DataAccess.configure(data_base)

app.include_router(auth_router)
app.include_router(agent_router)
app.include_router(session_router)
app.include_router(computer_router)
app.include_router(files_router)
app.include_router(user_router)
app.include_router(tool_approval_router)
app.include_router(tool_client_router)

