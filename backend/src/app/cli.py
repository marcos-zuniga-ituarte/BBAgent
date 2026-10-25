import argparse
import os
import sys
from getpass import getpass

from dotenv import load_dotenv

from app.data_access import AuthService, DataAccess


def _configure_database() -> None:
    load_dotenv()
    database = os.getenv("DATABASE_PATH")

    if not database:
        print(
            "Error: la variable de entorno DATABASE_PATH no está definida.",
            file=sys.stderr,
        )
        raise SystemExit(2)

    DataAccess.configure(database)


def _prompt_non_empty(label: str) -> str:
    while True:
        value = input(f"{label}: ").strip()
        if value:
            return value
        print(f"{label} no puede estar vacío.")


def _prompt_password(label: str = "Password") -> str:
    while True:
        value = getpass(f"{label}: ")
        if value:
            return value
        print(f"{label} no puede estar vacío.")


def _prompt_new_password_with_confirmation() -> str:
    while True:
        password = _prompt_password("Password")
        password_confirm = _prompt_password("Repite el password")

        if password != password_confirm:
            print("Los passwords no coinciden. Inténtalo de nuevo.")
            continue

        return password


def create_user(_: argparse.Namespace) -> int:
    print("Crear usuario")
    login = _prompt_non_empty("Login")
    password = _prompt_new_password_with_confirmation()

    try:
        user = AuthService.register_user(
            login=login,
            password=password,
        )
        print(f"Usuario creado correctamente. id={user.id} login={login}")
        return 0

    except ValueError as exc:
        print(f"Error creando usuario: {exc}", file=sys.stderr)
        return 1


def delete_user(_: argparse.Namespace) -> int:
    print("Eliminar usuario")
    login = _prompt_non_empty("Login")
    password = _prompt_password("Password actual")

    confirmation = input(
        f'Escribe "ELIMINAR" para confirmar el borrado del usuario "{login}": '
    ).strip()

    if confirmation != "ELIMINAR":
        print("Operación cancelada.")
        return 1

    if not hasattr(AuthService, "delete_user"):
        print(
            "Error: AuthService.delete_user(login, password) no está implementado todavía.",
            file=sys.stderr,
        )
        return 2

    try:
        AuthService.delete_user(
            login=login,
            password=password,
        )
        print(f"Usuario eliminado correctamente. login={login}")
        return 0

    except ValueError as exc:
        print(f"Error eliminando usuario: {exc}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli",
        description="CLI local de administración de usuarios",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser(
        "create-user",
        help="Crear un usuario de forma interactiva",
    )
    create_parser.set_defaults(func=create_user)

    delete_parser = subparsers.add_parser(
        "delete-user",
        help="Eliminar un usuario de forma interactiva",
    )
    delete_parser.set_defaults(func=delete_user)

    return parser


def main() -> int:
    _configure_database()
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())