"""Shim de arranque para Reflex.

Reflex busca por defecto un módulo llamado `<app_name>.<app_name>` que exporte `app`.
Este archivo reexporta la instancia `app` definida en `.app`.
"""

from .app import app  # noqa: F401
