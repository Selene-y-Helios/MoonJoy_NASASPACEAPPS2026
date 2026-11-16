"""Synthetic DEM tests check geometry/software behavior, not lunar scientific accuracy."""
import math
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from pyproj import CRS, Transformer
from fastapi.testclient import TestClient
from backend import dynamic_site as ds
from backend.api import app


@pytest.fixture
def synthetic_dem(tmp_path, monkeypatch):
    directory = tmp_path / "dem"
    directory.mkdir()
    projection = CRS.from_proj4(
        "+proj=stere +lat_0=-90 +lat_ts=-90 +lon_0=0 "
        "+R=1737400 +x_0=0 +y_0=0 +units=m +type=crs"
    )
    with rasterio.open(directory / "LDEM_80S_80MPP_ADJ.tiff", "w", driver="GTiff",
                       height=300, width=300, count=1, dtype="float32",
                       crs=projection.to_wkt(), transform=from_origin(-12000, 12000, 80, 80),
                       nodata=-9999) as file:
        data = np.zeros((300,300), dtype="float32")
        data[100:104, 151:155] = 400
        file.write(data,1)
    with rasterio.open(directory / "Site04_final_adj_5mpp_surf.tif", "w", driver="GTiff",
                       height=160, width=160, count=1, dtype="float32",
                       crs=projection.to_wkt(), transform=from_origin(-400, 400, 5, 5),
                       nodata=-9999) as file:
        file.write(np.zeros((160,160),dtype="float32"),1)
    monkeypatch.setattr(ds,"DEM_DIR",directory)
    monkeypatch.setattr(ds,"CACHE_DIR",tmp_path / "cache")
    monkeypatch.setattr(ds,"MAX_SEARCH_KM",8.0)
    monkeypatch.setattr(ds,"AZIMUTH_STEP_DEG",15.0)
    ds.map_png.cache_clear()
    return directory


def test_local_and_regional_sites_and_mesh(synthetic_dem):
    near = ds.resolve_site(-89.995, 20, 1.5)
    far = ds.resolve_site(-89.85, 20, 1.5)
    assert "Site04" in near["elevation_dem"]
    assert "LDEM" in far["elevation_dem"]
    assert far["longitude_deg_east"] == 20
    for site in (near,far):
        horizon,path=ds.get_or_compute_horizon(site)
        assert len(horizon["samples"]) == 24
        assert any(p["horizon_elevation_deg"] is not None for p in horizon["samples"])
        assert path.is_file()
        mesh=ds.build_terrain_mesh(site,width_m=400,max_resolution=40)
        assert mesh["metadata"]["valid_vertices"]>0
        assert len(mesh["indices"])>0


def test_map_click_geodetic_round_trip(synthetic_dem):
    point = ds.resolve_site(-89.96,85,1.5)
    clicked = ds.latlon_from_regional_xy(point["map_x_m"],point["map_y_m"],1.5)
    assert abs(clicked["latitude_deg"]-point["latitude_deg"])<1e-5
    assert abs(clicked["longitude_deg_east"]-point["longitude_deg_east"])<1e-5
    assert ds.map_png()[:8]==b"\x89PNG\r\n\x1a\n"


def test_reject_outside_coverage(synthetic_dem):
    with pytest.raises(ValueError, match="south polar"):
        ds.resolve_site(-75,0)
    with pytest.raises(ValueError, match="no valid regional"):
        ds.resolve_site(-88, 10)


def test_api_routes(synthetic_dem):
    client=TestClient(app)
    assert client.get("/api/health").status_code==200
    assert client.get("/api/map/metadata").status_code==200
    assert client.get("/api/map/preview").headers["content-type"]=="image/png"
    params={"latitude_deg":-89.9,"longitude_deg_east":15}
    site=client.get("/api/site",params=params)
    assert site.status_code==200,site.text
    horizon=client.get("/api/horizon",params=params)
    assert horizon.status_code==200,horizon.text
    terrain=client.get("/api/terrain",params=params)
    assert terrain.status_code==200,terrain.text
    assert client.get("/api/site",params={"latitude_deg":-75,"longitude_deg_east":15}).status_code==422
    assert client.get("/api/reference/test-south-pole").json()["can_merge_with_shackleton"] is False
