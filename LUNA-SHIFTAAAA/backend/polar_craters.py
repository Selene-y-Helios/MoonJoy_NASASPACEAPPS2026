"""Named lunar south-pole crater reference locations and local NASA LOLA DEM previews.

Coordinates approximate crater centers from JPL IPN Progress Report 42-176,
Table 1. Crater centers are geographic references, NOT validated landing sites.
Preview images are elevation-shaded LOLA raster samples, never optical LROC photos.
"""
from __future__ import annotations

import io
from functools import lru_cache

import numpy as np
import rasterio
from PIL import Image
from pyproj import CRS
from rasterio.enums import Resampling
from rasterio.windows import from_bounds

from .dynamic_site import _project_to, dem_paths

SOURCE = 'https://ipnpr.jpl.nasa.gov/progress_report/42-176/176C.pdf'
CRATERS = (
    {'id':'shackleton','name':'Shackleton','latitude_deg':-89.639,'longitude_deg_east':137.825,'diameter_km':19.0,'region':'Near the geographic south pole','description':'A deep polar crater. Some surrounding high terrain receives low-angle sunlight while the interior is often shadowed.'},
    {'id':'shoemaker','name':'Shoemaker','latitude_deg':-88.1,'longitude_deg_east':44.9,'diameter_km':50.9,'region':'South polar crater belt','description':'A large crater where terrain relief can obscure the Sun and the Earth. Its center is not an assessed landing site.'},
    {'id':'faustini','name':'Faustini','latitude_deg':-87.3,'longitude_deg_east':77.0,'diameter_km':39.0,'region':'Eastern polar highlands','description':'A polar crater with substantial shadowed terrain. Visibility must be checked at the exact observation site.'},
    {'id':'haworth','name':'Haworth','latitude_deg':-87.4,'longitude_deg_east':355.4,'diameter_km':51.4,'region':'Nearside polar sector','description':'Its high walls and dark floor illustrate why the local horizon matters when planning an operation.'},
    {'id':'de-gerlache','name':'de Gerlache','latitude_deg':-88.5,'longitude_deg_east':272.9,'diameter_km':32.4,'region':'Western sector near Shackleton','description':'A polar crater whose rims and neighboring ridges can produce different visibility windows only kilometers apart.'},
    {'id':'nobile','name':'Nobile','latitude_deg':-85.2,'longitude_deg_east':53.5,'diameter_km':73.0,'region':'Outer south polar region','description':'A broad crater near the 85°S band. Different points on its rim and floor require independent topographic analysis.'},
)


def catalog() -> dict:
    _, regional = dem_paths()
    with rasterio.open(regional) as src:
        crs = CRS.from_wkt(src.crs.to_wkt())
        features = []
        for item in CRATERS:
            x,y = _project_to(crs,item['latitude_deg'],item['longitude_deg_east'])
            features.append({**item,'map_x_m':round(float(x),1),'map_y_m':round(float(y),1),
                             'preview_url':f"/api/craters/{item['id']}/preview",
                             'preview_type':'NASA LOLA elevation visualization (not an optical photograph)',
                             'coordinate_source':SOURCE})
    return {'craters':features,'coordinate_source':SOURCE,
            'notice':'Approximate crater centers for map reference; do not interpret as safe or valid landing sites.'}


@lru_cache(maxsize=12)
def preview(crater_id: str, fingerprint: tuple) -> bytes:
    item = next((f for f in CRATERS if f['id']==crater_id),None)
    if item is None: raise KeyError(crater_id)
    _, regional = dem_paths()
    with rasterio.open(regional) as src:
        crs = CRS.from_wkt(src.crs.to_wkt())
        x,y = _project_to(crs,item['latitude_deg'],item['longitude_deg_east'])
        half=max(item['diameter_km']*750, 16000)  # crater and immediate surroundings
        window=from_bounds(x-half,y-half,x+half,y+half,transform=src.transform)
        grid=src.read(1,window=window,out_shape=(288,288),boundless=True,masked=True,
                      resampling=Resampling.bilinear)
    values=np.ma.filled(grid.astype('float64'),np.nan)
    valid=np.isfinite(values)
    if not valid.any():raise ValueError('No valid NASA LOLA pixels are available for this crater preview.')
    lo,hi=np.percentile(values[valid],[3,97]); normalized=np.clip((values-lo)/max(hi-lo,1),0,1)
    gray=np.nan_to_num(0.13+normalized*0.80,nan=0)
    rgba=np.zeros((288,288,4),dtype=np.uint8)
    rgba[:,:,:3]=(gray[:,:,None]*255).astype(np.uint8)
    rgba[:,:,3]=np.where(valid,255,0).astype(np.uint8)
    out=io.BytesIO();Image.fromarray(rgba,mode='RGBA').save(out,format='PNG')
    return out.getvalue()
