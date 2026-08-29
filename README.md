# Balotario de Aviación — versión web

Aplicación Streamlit preparada para Streamlit Community Cloud.

## Archivos que SÍ deben ir a GitHub

- `streamlit_app.py`
- `preguntas.csv`
- `requirements.txt`
- `supabase_schema.sql`
- `.gitignore`
- `README.md`

`secrets.example.toml` es solo una plantilla. No pongas claves reales en GitHub.

## 1. Crear el proyecto de Supabase

1. Crea un proyecto en Supabase.
2. Abre **SQL Editor**.
3. Copia y ejecuta el contenido de `supabase_schema.sql`.
4. Abre **Project Settings / API**.
5. Copia:
   - Project URL
   - `service_role` / secret key

La `service_role` es privada: nunca la subas a GitHub.

## 2. Crear secretos para Streamlit

En Streamlit Community Cloud > tu app > Settings > Secrets, pega:

```toml
SUPABASE_URL = "https://TU-PROYECTO.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "TU_SERVICE_ROLE_KEY"
PROFILE_PEPPER = "una-frase-larga-y-aleatoria-que-solo-tu-conozcas"
```

## 3. Subir a GitHub

Crea un repositorio y sube los archivos de esta carpeta.

## 4. Desplegar

1. Entra a https://share.streamlit.io
2. Inicia sesión con GitHub.
3. Create app.
4. Elige tu repositorio.
5. Branch: `main`
6. Main file path: `streamlit_app.py`
7. Advanced settings:
   - Python: 3.13 (o una versión compatible)
   - Secrets: pega los tres secretos indicados arriba.
8. Deploy.

## Uso por la estudiante

Al abrir el enlace:
1. Escribe siempre el mismo alias.
2. Escribe siempre el mismo PIN (mínimo 4 caracteres).
3. El progreso se recupera desde Supabase.

El alias y el PIN no se guardan literalmente. La app genera un identificador SHA-256 usando también `PROFILE_PEPPER`.

## Importante

- Si cambia alias o PIN, la app lo interpretará como un perfil distinto.
- No compartas `SUPABASE_SERVICE_ROLE_KEY`.
- El banco incluido contiene 538 preguntas extraídas de los nueve balotarios suministrados.
