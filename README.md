# 🌕 MoonJoy

**Lunar Landing Site Navigator | NASA Space Apps Challenge 2026**

Interactive lunar exploration and research prototype with NASA imagery, LOLA lunar terrain, JPL SPICE/DE440 ephemerides, React, TypeScript, Three.js and FastAPI.

> **Research and educational demonstrator.** Not a certified landing-safety, radio-link or mission-planning tool. This is not an official NASA application.

## Español

### Funcionalidades

- **Educativo:** globo lunar 3D con texturas NASA, cinco alunizajes históricos, información educativa y visualización orbital.
- **Profesional:** mapa del polo sur lunar, puntos A/B comparables, terreno LOLA en primera persona, horizonte de 360°, geometría Sol/Tierra con JPL SPICE, gráficos de visibilidad y ventanas de comunicación geométrica.
- **Órbitas DE440:** posiciones y trayectorias geométricas calculadas con JPL SPICE cuando la API está disponible. Las distancias se reescalan para su visualización; algunos giros axiales son ilustrativos.

### Instalación en Windows

**Requisitos:** Git, Git LFS, Python 3.12 o 3.13 y Node.js 22.

Abre CMD y ejecuta:

```bat
git lfs install
git clone https://github.com/Selene-y-Helios/MoonJoy_NASASPACEAPPS2026.git
cd MoonJoy_NASASPACEAPPS2026
git lfs pull
cd LUNA-SHIFTAAAA
py -3 tools\verify_github_package.py
START_ALL.bat
```

Espera a que el verificador muestre **PASS**. El lanzador instala las dependencias necesarias y abre dos terminales, una para la API y otra para el sitio. Mantén ambas abiertas y visita **http://127.0.0.1:5173/**, o el puerto indicado por Vite.

**Importante:** los archivos científicos grandes están en **Git LFS**. No utilices «Download ZIP» si necesitas todos los archivos de terreno y kernels, ya que ese ZIP puede incluir punteros LFS en vez de los datos originales. Si faltan archivos, ejecuta `git lfs pull` desde la raíz del repositorio.

Documentación ampliada: [README_START_HERE.md](LUNA-SHIFTAAAA/README_START_HERE.md) y [README_GITHUB_ES.md](LUNA-SHIFTAAAA/README_GITHUB_ES.md).

## English

**Features:** NASA-textured 3D Moon, five historical lunar landings, educational mode, professional south-pole LOLA terrain and 360° horizon, A/B observer comparisons, JPL SPICE Sun/Earth visibility and DE440 orbital visualization.

**Windows:** Install Git and Git LFS, Python 3.12/3.13, and Node.js 22. Run the commands under *Instalación en Windows*. Verify the scientific assets report **PASS**, launch `START_ALL.bat`, then open the Vite URL.

## Project structure

```text
LUNA-SHIFTAAAA/
├── backend/             # FastAPI, scientific calculations, SPICE orbits
├── web/                 # React, TypeScript, Three.js, NASA textures
├── data/
│   ├── dem/             # NASA LOLA lunar DEMs (Git LFS)
│   ├── kernels/         # JPL SPICE data (large files via Git LFS)
│   └── education/       # Historical lunar landing database
├── tests/               # Python tests
├── tools/               # Asset integrity verifier
├── START_ALL.bat
└── README_START_HERE.md
```

**Scientific limitations:** visibility based on geometry does not establish RF link quality; terrain analysis does not certify safe landing conditions. Scene distances are rescaled for visibility.

**Credits and rights:** NASA/JPL datasets and imagery retain their own attribution and usage terms; project contributors retain applicable rights. A public repository does not itself grant a software license or imply NASA/JPL endorsement.
