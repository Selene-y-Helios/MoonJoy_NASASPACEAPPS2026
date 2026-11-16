# LUNA SHIFT — Publicar y ejecutar desde GitHub

Esta carpeta es la versión preparada para el repositorio compartido `Selene-y-Helios/Lunar-Landing`, dentro de `LUNA-SHIFTAAAA/`.

## Diferencia importante entre GitHub y una página web

GitHub comparte el código y los datos. **No ejecuta por sí solo el backend de FastAPI** ni ofrece una aplicación online completamente operativa. Quien clone el repositorio podrá ejecutarla en su equipo. Para acceso web sin instalación aún haría falta un servidor de aplicaciones.

## Subir con GitHub Desktop (Windows)

1. Conserva intacta tu instalación funcional original. Abre **GitHub Desktop** y sincroniza el repositorio `Selene-y-Helios/Lunar-Landing` con `Fetch origin` y `Pull origin` cuando corresponda.
2. Desde `Current branch`, selecciona `New branch`: `feature/luna-shift-de440-complete`. No edites `main` directamente.
3. Abre el repositorio local desde GitHub Desktop (`Repository > Show in Explorer`). Confirma que dentro existe la carpeta `LUNA-SHIFTAAAA`.
4. **Antes de copiar y confirmar los datos**, abre una terminal en el repositorio y ejecuta `git lfs install`. Comprueba `git lfs version`. GitHub Desktop incluye Git LFS, pero hay que activarlo en la línea de comandos.
5. Extrae `LUNA_SHIFT_GITHUB_CODIGO_DE440.zip` en una carpeta temporal y copia **el contenido** de su carpeta `LUNA-SHIFTAAAA` a la carpeta `LUNA-SHIFTAAAA` de tu clon local. Elige reemplazar archivos existentes. No copies una segunda carpeta anidada. **Antes de continuar, copia también los siete datos NASA de la versión local original**, o extrae los dos ZIP de datos preparados sobre la carpeta raíz del repositorio, respetando `LUNA-SHIFTAAAA/data/dem` y `LUNA-SHIFTAAAA/data/kernels`.
6. En la terminal, estando en `LUNA-SHIFTAAAA`, ejecuta `git check-attr filter -- data/dem/LDEM_80S_80MPP_ADJ.TIF`. Debe mostrar `filter: lfs`. También ejecuta `git check-attr filter -- data/kernels/de440s.bsp`; debe mostrar `filter: lfs`.
7. Ejecuta `python tools/verify_github_package.py` (o `py -3 tools\verify_github_package.py`). Debe indicar `PASS`.
8. Regresa a GitHub Desktop. Revisa `Changes`: deben aparecer `.gitattributes`, el README, los módulos orbitales y los archivos NASA grandes. **No debe aparecer `.venv`, `node_modules`, `dist` ni archivos de contraseñas.**
9. Escribe el mensaje `Add complete LUNA SHIFT DE440 app and NASA datasets via LFS`, haz clic en `Commit to feature/luna-shift-de440-complete` y después en `Publish branch`/`Push origin`. Confirma que Git LFS terminó de cargar los archivos grandes.
10. Crea un Pull Request hacia `main` y pide revisión. No pulses Merge hasta confirmar que el `git lfs pull` de una clonación limpia recupera los archivos y las pruebas funcionan.

El paquete `LUNA_SHIFT_GITHUB_CODIGO_DE440.zip` NO contiene los siete datos NASA grandes; están en el proyecto completo recibido y los ZIP de datos separados. No hagas Commit hasta completar los siete archivos científicos.

Si GitHub Desktop no muestra los TIFF/BSP/BPC, comprueba que `.gitignore` no los excluya y que `.gitattributes` exista antes de `git add`. No subas el ZIP original como archivo al repositorio.

**Aviso de Git LFS:** el paquete conserva los datos científicos originales. Los archivos `.TIF`, `.tif`, `.bsp` y `.bpc` se suben con Git LFS, que tiene cuotas de almacenamiento y descarga que se cargan a la organización dueña del repositorio. Comprueba la política de tu equipo antes de publicar.

## Descargar y ejecutar después desde GitHub

1. Instala Git/GitHub Desktop con Git LFS, Python 3.12/3.13 y Node.js 22.
2. Clona el repositorio con GitHub Desktop. En una terminal dentro de la carpeta del proyecto ejecuta `git lfs pull`.
3. Verifica los datos científicos con `py -3 tools\verify_github_package.py`.
4. En Windows haz doble clic en `START_ALL.bat`. Se instalarán las dependencias faltantes y aparecerán dos terminales.
5. Abre `http://127.0.0.1:5173/` (o el puerto que muestre Vite).
6. Comprueba `http://127.0.0.1:8000/api/health` y `http://127.0.0.1:8000/api/orbits?date=2026-11-14`.
7. Para validar el código, ejecuta `python -m pytest -q` (requiere instalar `pytest`) y `npm run build` desde `web`.

Si no aparece la base de misiones o los datos científicos, revisa el estado del backend y el resultado del verificador. El modelo científico es preliminar y **no certifica seguridad de aterrizaje ni comunicación RF**.

**Importante para repositorios públicos:** la organización debe autorizar la publicación del código, las contribuciones de terceros y las texturas; comprobar atribuciones y licencias de los recursos. Poner el repositorio en público no es lo mismo que desplegar una página web.
