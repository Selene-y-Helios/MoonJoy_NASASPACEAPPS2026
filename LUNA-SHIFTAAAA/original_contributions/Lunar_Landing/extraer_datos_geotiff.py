import rasterio

with rasterio.open("Site04_final_adj_5mpp_surf.tif") as dem:
    elevacion = dem.read(1, masked=True)
    transformacion = dem.transform
    crs = dem.crs

print("Dimensiones:", elevacion.shape)
print("Proyección:", crs)