import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bbox import NSPD_BBOX_WGS84, nspd_bbox_l72, nspd_bbox_rd  # noqa: E402


def test_bbox_constanten_en_volgorde():
    x0, y0, x1, y1 = NSPD_BBOX_WGS84
    assert x0 < x1 and y0 < y1
    # NSPD-kader: Vlissingen/Borsele (west/noord) tot haven Gent/Zelzate (oost/zuid)
    assert 3.4 < x0 < 3.5 and 3.8 < x1 < 3.95
    assert 51.0 < y0 < 51.1 and 51.4 < y1 < 51.55


def test_rd_en_l72_transformaties():
    rd = nspd_bbox_rd()
    assert all(isinstance(v, float) for v in rd)
    # RD van de NSPD-bbox moet binnen het NL-kanaal vallen (grof checkpunt:
    # Vlissingen ligt rond RD (35000, 420000))
    assert rd[0] < 50000 < rd[2] or rd[0] < 60000
    l72 = nspd_bbox_l72()
    assert all(isinstance(v, float) for v in l72)
    # Lambert72 van haven Gent ligt rond (105000, 193000)
    assert l72[0] < 105000 < l72[2]
    assert l72[1] < 193000 < l72[3]
