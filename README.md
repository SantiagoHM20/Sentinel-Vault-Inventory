# Sentinel-Vault Inventory

Aplicacion monolitica en Python/Flask para demostrar la diferencia en superficie de ataque entre dos patrones de inyeccion de secretos en Azure AKS:

- Patron A: secreto en variable de entorno (DB_PASSWORD)
- Patron B: lectura directa en memoria desde Azure Key Vault con identidad de workload (DefaultAzureCredential + SecretClient)

## 1. Estructura del proyecto

- app.py: backend Flask + logica de lectura de secretos
- templates/index.html: dashboard Bootstrap 5
- requirements.txt: dependencias Python
- Dockerfile: imagen de contenedor (python:3.9-slim, puerto 8080)
- deployment.yaml: manifiesto combinado original (se mantiene para pruebas rapidas)
- k8s/manifest-patron-a.yml: manifiesto dedicado al Patron A (entorno)
- k8s/manifest-patron-b.yml: manifiesto dedicado al Patron B (vault/CSI)
- .github/workflows/pipeline-patron-a.yml: pipeline para desplegar Patron A
- .github/workflows/pipeline-patron-b.yml: pipeline para desplegar Patron B

## 2. Requisitos

- Python 3.9+
- Docker Desktop
- (Opcional para Patron B real) Azure Key Vault y Azure Workload Identity en AKS

## 3. Ejecutar local (sin Docker)

### 3.1 Crear entorno virtual e instalar dependencias (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3.2 Ejecutar Patron A (Entorno)

```powershell
$env:SECRET_SOURCE="env"
$env:DB_PASSWORD="demo-local-123"
python app.py
```

Abrir en navegador:

http://localhost:8080

### 3.3 Ejecutar Patron B (Vault directo)

```powershell
$env:SECRET_SOURCE="vault"
$env:KEY_VAULT_URL="https://TU-KEYVAULT.vault.azure.net/"
$env:KEY_VAULT_SECRET_NAME="db-password"
python app.py
```

Nota: si no hay identidad/permisos configurados, el dashboard mostrara el error controlado en pantalla.

## 4. Ejecutar con Docker

### 4.1 Build

```powershell
docker build -t sentinel-vault-inventory:latest .
```

### 4.2 Run Patron A (Entorno)

```powershell
docker run --rm -p 8080:8080 -e SECRET_SOURCE=env -e DB_PASSWORD=demo123 sentinel-vault-inventory:latest
```

### 4.3 Run Patron B (Vault directo)

```powershell
docker run --rm -p 8080:8080 -e SECRET_SOURCE=vault -e KEY_VAULT_URL=https://TU-KEYVAULT.vault.azure.net/ -e KEY_VAULT_SECRET_NAME=db-password sentinel-vault-inventory:latest
```

## 5. Variables de entorno

- SECRET_SOURCE:
  - env: usa get_secret_from_env()
  - vault o csi: usa get_secret_from_vault()
- DB_PASSWORD: secreto para Patron A
- KEY_VAULT_URL: URL del Key Vault para Patron B
- KEY_VAULT_SECRET_NAME: nombre del secreto en Key Vault (default: db-password)
- PORT: puerto de Flask (default: 8080)

## 6. Flujo de demo para video (Metrica M2)

1. Inicia en Patron A con SECRET_SOURCE=env y DB_PASSWORD cargado.
2. En la UI revisa:
   - Fuente: Entorno
   - Conexion Segura
   - Debug Info (Metrica M2): DB_PASSWORD existe / vacia / longitud detectada
3. Ejecuta inspeccion de runtime para mostrar que el secreto vive como variable de entorno.
4. Cambia a Patron B con SECRET_SOURCE=vault.
5. En la UI revisa:
   - Fuente: Vault Directo/CSI
   - Debug Info mostrando que DB_PASSWORD puede no existir en entorno
6. Repite inspeccion para comparar superficie de ataque.

## 7. Comandos utiles de inspeccion

### 7.1 Kubernetes - inspeccionar variables de entorno

```powershell
kubectl get pods
kubectl exec -it <POD_NAME> -- printenv | findstr DB_PASSWORD
```

### 7.2 TruffleHog (ejemplo conceptual)

```powershell
trufflehog filesystem .
```

Ajusta el comando segun tu version de TruffleHog y escenario de demo.

## 8. Despliegue AKS (manifest de ejemplo)

El archivo deployment.yaml ya incluye:

- ServiceAccount con anotacion de Azure Workload Identity
- Label azure.workload.identity/use: "true"
- Montaje de Secrets Store CSI Driver en /mnt/secrets-store
- Variables para alternar Patron A/B

Aplicar:

```powershell
kubectl apply -f deployment.yaml
kubectl get deploy,pods,svc
```

## 8.1 Despliegue AKS recomendado para demo A/B separada

Patron A (entorno):

```powershell
kubectl apply -f k8s/manifest-patron-a.yml
kubectl rollout status deploy/sentinel-vault-inventory
```

Patron B (vault/CSI):

```powershell
kubectl apply -f k8s/manifest-patron-b.yml
kubectl rollout status deploy/sentinel-vault-inventory
```

Nota: estos manifiestos no cambian la forma de prueba; solo separan la evidencia por patron.

## 9. Personalizacion rapida de la demo

En app.py puedes:

- Forzar Patron A devolviendo get_secret_from_env() en resolve_secret()
- Forzar Patron B devolviendo get_secret_from_vault() en resolve_secret()

Esto permite comentar/descomentar durante el video para mostrar cambios en herramientas de escaneo.

## 10. Seguridad

- El dashboard no imprime el secreto en claro; solo muestra estado y longitud.
- Si Patron B falla (credenciales/permisos), se reporta error controlado sin exponer contenido sensible.
- Recomendado: ejecutar escaneo Snyk despues de cambios en codigo o dependencias.

## 11. Guia para grabar la demo 

### 11.1 Preparacion unica (antes de grabar)

1. Verificar contexto y namespace:

```powershell
kubectl config current-context
kubectl get nodes
```

2. Asegurar el secreto para Patron A (si no existe):

```powershell
kubectl create secret generic db-password-secret --from-literal=DB_PASSWORD="DemoEnv-2026" --dry-run=client -o yaml | kubectl apply -f -
```

3. Verificar prerequisitos de Patron B:
   - ServiceAccount con client-id correcto en k8s/manifest-patron-b.yml
   - SecretProviderClass sentinel-vault-spc ya creado en cluster
   - KEY_VAULT_URL y KEY_VAULT_SECRET_NAME correctos

### 11.2 Escena 1 - Patron A (entorno)

1. Despliegue del Patron A:

```powershell
kubectl apply -f k8s/manifest-patron-a.yml
kubectl rollout restart deploy/sentinel-vault-inventory
kubectl rollout status deploy/sentinel-vault-inventory
```

2. Obtener nombre del pod:

```powershell
$POD_A = kubectl get pods -l app=sentinel-vault-inventory -o jsonpath='{.items[0].metadata.name}'
echo $POD_A
```

3. Evidenciar superficie de ataque (M2):

```powershell
kubectl exec -it $POD_A -- printenv | findstr DB_PASSWORD
```

4. Abrir la app y mostrar en pantalla:
   - Fuente: Entorno
   - Conexion Segura
   - Debug Info: DB_PASSWORD existe = Si

### 11.3 Escena 2 - Patron B (vault/CSI)

1. Despliegue del Patron B:

```powershell
kubectl apply -f k8s/manifest-patron-b.yml
kubectl rollout restart deploy/sentinel-vault-inventory
kubectl rollout status deploy/sentinel-vault-inventory
```

2. Obtener nombre del pod:

```powershell
$POD_B = kubectl get pods -l app=sentinel-vault-inventory -o jsonpath='{.items[0].metadata.name}'
echo $POD_B
```

3. Evidenciar reduccion de exposicion:

```powershell
kubectl exec -it $POD_B -- printenv | findstr DB_PASSWORD
kubectl exec -it $POD_B -- ls -la /mnt/secrets-store
```

4. Abrir la app y mostrar en pantalla:
   - Fuente: Vault Directo/CSI
   - Conexion Segura
   - Debug Info: DB_PASSWORD existe = No (o vacia)

### 11.4 Escena 3 - Comparativa final en video

1. Resumir evidencia con split-screen o corte directo:
   - Patron A: secreto visible en entorno del contenedor
   - Patron B: secreto ya no aparece como variable de entorno
2. Mostrar que la app sigue funcionando en ambos casos, pero cambiar la superficie observable.

### 11.5 Pipelines dedicados (opcional en demo)

Disparar en GitHub Actions:

- .github/workflows/pipeline-patron-a.yml
- .github/workflows/pipeline-patron-b.yml

Secrets requeridos en GitHub:

- AZURE_CREDENTIALS
- AKS_RESOURCE_GROUP
- AKS_CLUSTER_NAME
