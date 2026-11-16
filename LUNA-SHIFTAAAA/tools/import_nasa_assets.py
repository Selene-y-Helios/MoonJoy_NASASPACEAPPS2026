"""Copy the exact NASA DEM and SPICE files from the supplied lunar landing ZIP.

This script does not download, alter, or reproject the source data.
"""
from pathlib import Path
import shutil
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    'data/dem/LDEM_80S_80MPP_ADJ.TIF',
    'data/dem/Site04_final_adj_5mpp_surf.tif',
    'data/kernels/de440s.bsp',
    'data/kernels/moon_de440_250416.tf',
    'data/kernels/moon_pa_de440_200625.bpc',
    'data/kernels/naif0012.tls',
    'data/kernels/pck00011.tpc',
]


def import_assets(archive: Path) -> None:
    if not archive.is_file():
        raise FileNotFoundError(f'Cannot find source ZIP: {archive}')
    with zipfile.ZipFile(archive) as source:
        names = set(source.namelist())
        missing = [item for item in FILES if f'lunar landing/{item}' not in names]
        if missing:
            raise ValueError('Source ZIP is missing required files: ' + ', '.join(missing))
        for item in FILES:
            entry = source.getinfo(f'lunar landing/{item}')
            destination = ROOT / item
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                if destination.stat().st_size == entry.file_size:
                    print(f'Already present: {item}')
                    continue
                raise FileExistsError(f'Existing NASA file has a different size; refusing to overwrite: {destination}')
            with source.open(entry) as reader, destination.open('wb') as writer:
                shutil.copyfileobj(reader, writer, length=1024 * 1024)
            print(f'Imported: {item} ({entry.file_size:,} bytes)')
    print('NASA data import complete. Start the backend and check /api/health.')


if __name__ == '__main__':
    archive = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / 'lunar landing.zip'
    try:
        import_assets(archive)
    except (FileNotFoundError, FileExistsError, ValueError, zipfile.BadZipFile) as error:
        raise SystemExit(str(error)) from error
