import os
from flask import Flask, render_template

app = Flask(__name__)


def get_secret_from_env():
    """Pattern A: Read secret from environment variable."""
    secret_value = os.getenv("DB_PASSWORD")
    if secret_value is None:
        return None, "Entorno", "DB_PASSWORD no esta definida en el entorno"
    if secret_value == "":
        return None, "Entorno", "DB_PASSWORD existe pero esta vacia"
    return secret_value, "Entorno", None


def get_secret_from_vault():
    """Pattern B: Read secret directly from Azure Key Vault into memory."""
    try:
        from azure.identity import DefaultAzureCredential
        from azure.keyvault.secrets import SecretClient
    except ImportError:
        return None, "Vault Directo/CSI", "Dependencias de Azure no instaladas"

    vault_url = os.getenv("KEY_VAULT_URL", "").strip()
    secret_name = os.getenv("KEY_VAULT_SECRET_NAME", "db-password").strip()

    if not vault_url:
        return None, "Vault Directo/CSI", "KEY_VAULT_URL no esta configurada"

    try:
        credential = DefaultAzureCredential(exclude_interactive_browser_credential=True)
        client = SecretClient(vault_url=vault_url, credential=credential)
        secret_value = client.get_secret(secret_name).value

        if not secret_value:
            return None, "Vault Directo/CSI", "Secreto vacio en Key Vault"

        return secret_value, "Vault Directo/CSI", None
    except Exception as ex:
        return None, "Vault Directo/CSI", f"No se pudo leer secreto desde Key Vault: {ex}"


def resolve_secret(secret_source):
    """
    Selects which secret loading pattern to use for the demo.

    Demo note:
    - You can force Pattern A by returning get_secret_from_env().
    - You can force Pattern B by returning get_secret_from_vault().
    """

    # Pattern A (Environment variable)
    if secret_source == "env":
        return get_secret_from_env()

    # Pattern B (Direct Key Vault / CSI-backed identity)
    if secret_source in {"vault", "csi"}:
        return get_secret_from_vault()

    return None, "Desconocido", f"SECRET_SOURCE invalido: {secret_source}"


def mask_secret(secret_value):
    if not secret_value:
        return "No disponible"
    return f"******** (len={len(secret_value)})"


@app.route("/")
def inventory_dashboard():
    secret_source = os.getenv("SECRET_SOURCE", "env").strip().lower()
    secret_value, source_label, secret_error = resolve_secret(secret_source)

    env_value = os.getenv("DB_PASSWORD")
    env_exists = env_value is not None
    env_is_empty = env_exists and env_value == ""

    secure_connection = secret_value is not None and secret_error is None

    supplies = [
        {"item": "Antidoto NBQ", "stock": 42, "location": "Bunker Norte", "status": "OK"},
        {"item": "Raciones MRE", "stock": 350, "location": "Almacen Central", "status": "LOW"},
        {"item": "Kits Trauma", "stock": 88, "location": "Unidad Medica", "status": "OK"},
        {"item": "Filtros HEPA", "stock": 12, "location": "Sala de Aire", "status": "CRITICAL"},
    ]

    return render_template(
        "index.html",
        supplies=supplies,
        secret_source_label=source_label,
        secure_connection=secure_connection,
        secret_error=secret_error,
        masked_secret=mask_secret(secret_value),
        selected_mode=secret_source,
        env_exists=env_exists,
        env_is_empty=env_is_empty,
        env_length=len(env_value) if env_value else 0,
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    app.run(host="0.0.0.0", port=port, debug=False)
