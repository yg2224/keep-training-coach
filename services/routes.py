import base64
import gzip
import json
import zlib

try:
    from Crypto.Cipher import AES as CryptoAES
except Exception:
    CryptoAES = None


MAX_ROUTE_POINTS = 240
FULL_ROUTE_MIN_POINTS = 10
AES_KEY = base64.b64decode("NTZmZTU5OzgyZzpkODczYw==")
AES_IV = base64.b64decode("MjM0Njg5MjQzMjkyMDMwMA==")


def _normalize_point(latitude, longitude):
    try:
        lat = float(latitude)
        lng = float(longitude)
    except (TypeError, ValueError):
        return None
    if not lat and not lng:
        return None
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        return None
    return {"lat": round(lat, 6), "lng": round(lng, 6)}


def downsample_route_points(points, max_points=MAX_ROUTE_POINTS):
    if max_points is None or max_points <= 0:
        return points
    if len(points) <= max_points:
        return points
    last_index = len(points) - 1
    selected = []
    for index in range(max_points):
        point_index = round(index * last_index / (max_points - 1))
        selected.append(points[point_index])
    return selected


def _decode_runmap_data(text, is_geo=False):
    if not text:
        return []

    raw_bytes = base64.b64decode(text)
    candidates = []
    if is_geo and CryptoAES is not None:
        try:
            cipher = CryptoAES.new(AES_KEY, CryptoAES.MODE_CBC, AES_IV)
            candidates.append(cipher.decrypt(raw_bytes))
        except ValueError:
            pass
    candidates.append(raw_bytes)

    for candidate in candidates:
        try:
            return json.loads(zlib.decompress(candidate, 16 + zlib.MAX_WBITS))
        except Exception:
            continue
    return []


def _points_from_items(items, latitude_key="latitude", longitude_key="longitude"):
    points = []
    for item in items or []:
        point = _normalize_point(item.get(latitude_key), item.get(longitude_key))
        if point and (not points or points[-1] != point):
            points.append(point)
    return points


def extract_route_points(payload, max_points=MAX_ROUTE_POINTS):
    points = _points_from_items(_decode_runmap_data(payload.get("geoPoints"), is_geo=True))

    if not points:
        points = []
    step_points = payload.get("stepPoints")
    if step_points and not points:
        try:
            decoded = gzip.decompress(base64.b64decode(step_points)).decode("utf-8")
            for item in json.loads(decoded):
                point = _normalize_point(item.get("latitude"), item.get("longitude"))
                if point and (not points or points[-1] != point):
                    points.append(point)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            points = []

    if not points:
        points = _points_from_items(payload.get("crossKmPoints"))

    return downsample_route_points(points, max_points=max_points)


def serialize_route_points(points):
    if not points:
        return ""
    return json.dumps(points, separators=(",", ":"))


def deserialize_route_points(value):
    if not value:
        return []
    try:
        items = json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    points = []
    for item in items:
        if not isinstance(item, dict):
            continue
        point = _normalize_point(item.get("lat"), item.get("lng"))
        if point and (not points or points[-1] != point):
            points.append(point)
    return points


def has_dense_route(value, min_points=FULL_ROUTE_MIN_POINTS):
    return len(deserialize_route_points(value)) >= min_points


def build_route_preview(points, width=720, height=280, padding=18):
    if len(points) < 2:
        return None

    lng_values = [point["lng"] for point in points]
    lat_values = [point["lat"] for point in points]
    min_lng, max_lng = min(lng_values), max(lng_values)
    min_lat, max_lat = min(lat_values), max(lat_values)

    span_lng = max(max_lng - min_lng, 0.000001)
    span_lat = max(max_lat - min_lat, 0.000001)
    usable_width = width - padding * 2
    usable_height = height - padding * 2
    scale = min(usable_width / span_lng, usable_height / span_lat)
    offset_x = padding + (usable_width - span_lng * scale) / 2
    offset_y = padding + (usable_height - span_lat * scale) / 2

    svg_points = []
    for point in points:
        x = offset_x + (point["lng"] - min_lng) * scale
        y = offset_y + (max_lat - point["lat"]) * scale
        svg_points.append({"x": round(x, 2), "y": round(y, 2)})

    return {
        "width": width,
        "height": height,
        "polyline": " ".join(f"{point['x']},{point['y']}" for point in svg_points),
        "start": svg_points[0],
        "end": svg_points[-1],
        "point_count": len(svg_points),
    }
