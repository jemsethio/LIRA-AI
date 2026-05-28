#!/usr/bin/env python3
"""
GloSEM Download Script — LIRA-AI
==================================
Downloads GloSEM v1.2 global soil erosion raster (open access, CC BY 4.0)
Reference: Borrelli et al. (2021) Nature Communications
Data DOI:  https://doi.org/10.5281/zenodo.6539253

The full global file is ~2GB. This script downloads just the Africa subset
if gdal/gdal_translate is available, otherwise downloads the full file.

Usage:
    cd backend
    python scripts/download_glsem.py

Output: data/glsem/Global_SoilErosion_3s.tif (~200MB Africa subset)
"""

import sys, urllib.request, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "glsem"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE = OUT_DIR / "Global_SoilErosion_3s.tif"

ZENODO_URL = "https://zenodo.org/record/6539253/files/Global_SoilErosion_3s.tif"
ZENODO_DOI = "https://doi.org/10.5281/zenodo.6539253"

# Africa bounding box for gdal_translate crop
AFRICA_BBOX = "-20 -40 55 40"   # xmin ymin xmax ymax (WGS84)
# Ethiopia + surrounding for Omo-Ghibe
ETH_BBOX    = "30 0 48 15"


def download_with_progress(url: str, dest: Path):
    print(f"Downloading from: {url}")
    print(f"Destination:      {dest}")
    print("This may take several minutes for the global file (~2GB)...")

    def _progress(block_num, block_size, total_size):
        pct = min(100, block_num * block_size / total_size * 100) if total_size > 0 else 0
        mb  = block_num * block_size / 1e6
        print(f"\r  {pct:.1f}%  {mb:.0f} MB downloaded", end="", flush=True)

    urllib.request.urlretrieve(url, str(dest), reporthook=_progress)
    print()


def try_gdal_crop():
    """Try to use gdal_translate to download only the Africa/Ethiopia subset."""
    import subprocess
    # Try /vsicurl/ approach (reads from remote, writes local subset)
    vsicurl = f"/vsicurl/{ZENODO_URL}"
    cmd = [
        "gdal_translate", "-projwin",
        "30", "15", "48", "0",   # xmin ymax xmax ymin (Ethiopia)
        "-co", "COMPRESS=LZW",
        vsicurl, str(OUT_FILE)
    ]
    print("Trying gdal_translate (Ethiopia subset ~50MB)...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode == 0 and OUT_FILE.exists():
        print(f"✓ Ethiopia subset downloaded: {OUT_FILE.stat().st_size/1e6:.0f}MB")
        return True
    print(f"gdal_translate failed: {result.stderr[:100]}")
    return False


def main():
    print("="*60)
    print("GloSEM v1.2 Download — LIRA-AI Soil Erosion Data")
    print(f"Citation: Borrelli et al. (2021) Nat. Commun.")
    print(f"DOI: {ZENODO_DOI}")
    print("License: CC BY 4.0 (open access)")
    print("="*60)

    if OUT_FILE.exists() and OUT_FILE.stat().st_size > 1e6:
        print(f"\n✓ GloSEM file already exists: {OUT_FILE}")
        print(f"  Size: {OUT_FILE.stat().st_size/1e6:.0f}MB")
        return

    # Try GDAL crop first (much smaller file)
    try:
        if try_gdal_crop():
            return
    except (FileNotFoundError, Exception) as e:
        print(f"  GDAL not available or failed: {e}")

    # Try rasterio vsicurl crop
    try:
        import rasterio
        from rasterio.windows import from_bounds
        vsicurl = f"/vsicurl/{ZENODO_URL}"
        print("Trying rasterio /vsicurl/ crop (Ethiopia 30-48°E, 0-15°N)...")
        with rasterio.open(vsicurl) as src:
            win = from_bounds(30, 0, 48, 15, src.transform)
            data = src.read(1, window=win)
            profile = src.profile.copy()
            profile.update({
                "width": data.shape[1],
                "height": data.shape[0],
                "transform": rasterio.windows.transform(win, src.transform),
                "compress": "lzw",
            })
            with rasterio.open(str(OUT_FILE), "w", **profile) as dst:
                dst.write(data, 1)
        print(f"✓ Ethiopia GloSEM saved: {OUT_FILE.stat().st_size/1e6:.0f}MB")
        return
    except Exception as e:
        print(f"  rasterio crop failed: {e}")

    # Last resort: download full file
    print("\nDownloading full global GloSEM file (~2GB)...")
    print("Tip: Use a stable network connection. Press Ctrl+C to cancel.")
    try:
        download_with_progress(ZENODO_URL, OUT_FILE)
        print(f"✓ Downloaded: {OUT_FILE.stat().st_size/1e6:.0f}MB")
    except KeyboardInterrupt:
        print("\nCancelled.")
        if OUT_FILE.exists(): OUT_FILE.unlink()
    except Exception as e:
        print(f"Download failed: {e}")
        print(f"\nManual download:")
        print(f"  wget '{ZENODO_URL}' -O '{OUT_FILE}'")
        print(f"  OR visit: {ZENODO_DOI}")


if __name__ == "__main__":
    main()
