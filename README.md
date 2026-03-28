# Sentinel-Vault Inventory

Aplicacion monolitica Flask para demostrar la diferencia de superficie de ataque entre dos patrones de consumo de secretos en AKS.

- Patron A: secreto en variable de entorno (`DB_PASSWORD`)
- Patron B: secreto consumido en runtime desde Key Vault (Workload Identity)

## 1. Estado actual del proyecto

Archivos principales:

- `app.py`: backend Flask y logica de resolucion del secreto
- `templates/index.html`: dashboard y panel de Debug Info
- `Dockerfile`: build local para pruebas
- `k8s/manifest-patron-a.yml`: Deployment `sentinel-vault-inventory-a`, Service `sentinel-vault-inventory-svc-a`
- `k8s/manifest-patron-b.yml`: Deployment `sentinel-vault-inventory-b`, Service `sentinel-vault-inventory-svc-b`
- `.github/workflows/pipeline-patron-a.yml`: build/push patron A + creacion de secret K8s + deploy A
- `.github/workflows/pipeline-patron-b.yml`: build/push patron B + deploy B

## 2. Recursos externos requeridos

1. AKS en ejecucion
2. ACR `acrcloudsec`
3. Key Vault `kv-cloud-sec-demo` con secreto `db-password`
4. Managed Identity con permisos de lectura a secretos para Patron B
5. Workload Identity configurado para el ServiceAccount del Patron B
6. GitHub Secrets para pipelines:
   - `AZURE_CREDENTIALS` (JSON de service principal)
   - `AKS_RESOURCE_GROUP`
   - `AKS_CLUSTER_NAME`

## 3. Papel de manifiestos y pipelines en la demo

- Los manifiestos (`k8s/*.yml`) son la forma mas clara de mostrar en video el cambio A -> B en vivo.
- Los pipelines (`.github/workflows/*.yml`) sirven como evidencia de CI/CD automatizado.

Recomendacion de grabacion:

1. Mostrar primero Patron A aplicado en cluster.
2. Mostrar luego Patron B aplicado en cluster.
3. Mostrar que la app funciona en ambos, pero cambia la exposicion observada.

## 4. Preflight antes de grabar

Ejecutar en PowerShell:

   kubectl config current-context
   kubectl get nodes
   kubectl get deploy,svc,pods

Crear/actualizar secreto para Patron A (si no existe):

   kubectl create secret generic db-password-secret --from-literal=DB_PASSWORD="DemoEnv-2026" --dry-run=client -o yaml | kubectl apply -f -

## 5. Demo en vivo con manifiestos (recomendado)

### 5.1 Escena A (entorno)

Desplegar Patron A:

   kubectl apply -f k8s/manifest-patron-a.yml
   kubectl rollout status deploy/sentinel-vault-inventory-a

Obtener pod A:

   $POD_A = kubectl get pods -l app=sentinel-vault-inventory-a -o jsonpath='{.items[0].metadata.name}'
   echo $POD_A

Evidencia M2 en pod A:

   kubectl exec -it $POD_A -- printenv | findstr DB_PASSWORD

Exponer app A localmente y abrir navegador en `http://localhost:8081`:

   kubectl port-forward svc/sentinel-vault-inventory-svc-a 8081:80

Esperado en UI:

1. Fuente: Entorno
2. Debug Info: DB_PASSWORD existe = Si

### 5.2 Escena B (vault)

En otra terminal, desplegar Patron B:

   kubectl apply -f k8s/manifest-patron-b.yml
   kubectl rollout status deploy/sentinel-vault-inventory-b

Obtener pod B:

   $POD_B = kubectl get pods -l app=sentinel-vault-inventory-b -o jsonpath='{.items[0].metadata.name}'
   echo $POD_B

Evidencia en pod B:

   kubectl exec -it $POD_B -- printenv | findstr DB_PASSWORD

Exponer app B localmente y abrir navegador en `http://localhost:8082`:

   kubectl port-forward svc/sentinel-vault-inventory-svc-b 8082:80

Esperado en UI:

1. Fuente: Vault Directo/CSI
2. Debug Info: DB_PASSWORD existe = No (o vacia)

## 6. Demo usando pipelines (alternativa)

### 6.1 Ejecutar pipeline A

En GitHub Actions, ejecutar `pipeline-patron-a`.

Ese pipeline actualmente:

1. Hace login en Azure
2. Hace login en ACR
3. Build y push de imagen `acrcloudsec.azurecr.io/sentinel-vault-inventory:patron-a`
4. Extrae secreto desde Key Vault y lo usa para crear `db-password-secret`
5. Aplica `k8s/manifest-patron-a.yml`

Nota importante: ese flujo de A incluye una evidencia de fuga en logs de CI por diseno de demo.

### 6.2 Ejecutar pipeline B

En GitHub Actions, ejecutar `pipeline-patron-b`.

Ese pipeline:

1. Hace login en Azure
2. Hace login en ACR
3. Build y push de imagen `acrcloudsec.azurecr.io/sentinel-vault-inventory:patron-b`
4. Configura contexto AKS
5. Aplica `k8s/manifest-patron-b.yml`

## 7. Validacion final (checklist)

1. `kubectl get deploy,svc,pods` muestra ambos despliegues en Running
2. Pod A expone `DB_PASSWORD` por `printenv`
3. Pod B no expone `DB_PASSWORD` por `printenv`
4. UI A responde en `localhost:8081`
5. UI B responde en `localhost:8082`

## 8. Troubleshooting rapido

Si `kubectl` falla en pipeline A:

- Agregar paso `azure/aks-set-context` como en pipeline B.

Si Patron B no puede leer secreto:

1. Verificar `azure.workload.identity/client-id` en `k8s/manifest-patron-b.yml`
2. Verificar permisos de Managed Identity sobre Key Vault
3. Verificar nombre del secreto `db-password` en Key Vault

Si no ves la app:

1. Verificar `kubectl port-forward` activo
2. Verificar nombre correcto del Service (`-svc-a` o `-svc-b`)
