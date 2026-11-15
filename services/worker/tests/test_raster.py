import tempfile, os
import numpy as np
import rasterio
from rasterio.transform import from_origin
from worker.processing import inspect_raster

def test_inspect_raster():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "t.tif")
        data = np.arange(12, dtype="float32").reshape(3,4)
        transform = from_origin(0, 0, 1, 1)
        with rasterio.open(path, "w", driver="GTiff", height=3, width=4, count=1, dtype="float32", crs="EPSG:4326", transform=transform, nodata=-999) as dst:
            dst.write(data, 1)
        m = inspect_raster(path)
        assert m.width == 4
        assert m.height == 3
        assert m.bands == 1
        assert m.crs == "EPSG:4326"
        assert m.nodata == -999
