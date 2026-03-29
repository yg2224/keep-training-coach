from datetime import datetime
from html import escape
from math import asin, cos, radians, sin, sqrt


EARTH_RADIUS_METERS = 6371000


def _segment_distance_meters(start, end):
    lat1 = radians(float(start["lat"]))
    lng1 = radians(float(start["lng"]))
    lat2 = radians(float(end["lat"]))
    lng2 = radians(float(end["lng"]))
    delta_lat = lat2 - lat1
    delta_lng = lng2 - lng1
    hav = sin(delta_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(delta_lng / 2) ** 2
    return 2 * EARTH_RADIUS_METERS * asin(sqrt(hav))


def trim_route_points_for_privacy(points, trim_meters=200):
    if trim_meters <= 0:
        return points
    if len(points) < 3:
        return []

    total_distance = sum(
        _segment_distance_meters(points[index], points[index + 1])
        for index in range(len(points) - 1)
    )
    if total_distance <= trim_meters * 2:
        return []

    start_index = 0
    distance_from_start = 0.0
    while start_index < len(points) - 2 and distance_from_start < trim_meters:
        distance_from_start += _segment_distance_meters(points[start_index], points[start_index + 1])
        start_index += 1

    end_index = len(points) - 1
    distance_from_end = 0.0
    while end_index > start_index + 1 and distance_from_end < trim_meters:
        distance_from_end += _segment_distance_meters(points[end_index - 1], points[end_index])
        end_index -= 1

    trimmed = points[start_index : end_index + 1]
    return trimmed if len(trimmed) >= 2 else []


def _format_point_value(value):
    formatted = f"{float(value):.6f}"
    return formatted.rstrip("0").rstrip(".")


def _format_gpx_time(start_time):
    if not start_time:
        return ""
    if isinstance(start_time, datetime):
        return start_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    parsed = datetime.strptime(str(start_time), "%Y-%m-%d %H:%M:%S")
    return parsed.strftime("%Y-%m-%dT%H:%M:%SZ")


def build_gpx_document(activity_name, start_time, points, moving_time=None, distance_meters=None):
    timestamp = _format_gpx_time(start_time)
    track_name = escape(activity_name or "Keep Run")
    description_parts = []
    if distance_meters not in (None, ""):
        description_parts.append(f"distance_km={round(float(distance_meters) / 1000, 2)}")
    if moving_time:
        description_parts.append(f"moving_time={moving_time}")
    description = escape(" | ".join(description_parts))
    point_lines = []
    for point in points:
        lat = _format_point_value(point["lat"])
        lng = _format_point_value(point["lng"])
        if timestamp:
            point_lines.append(f'      <trkpt lat="{lat}" lon="{lng}"><time>{timestamp}</time></trkpt>')
        else:
            point_lines.append(f'      <trkpt lat="{lat}" lon="{lng}"></trkpt>')
    joined_points = "\n".join(point_lines)
    metadata_lines = [f"    <name>{track_name}</name>"]
    if description:
        metadata_lines.append(f"    <desc>{description}</desc>")
    if moving_time:
        metadata_lines.append(f"    <type>{escape(str(moving_time))}</type>")
    metadata_block = "\n".join(metadata_lines)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<gpx version="1.1" creator="keep-training-coach" '
        'xmlns="http://www.topografix.com/GPX/1/1">\n'
        "  <trk>\n"
        f"{metadata_block}\n"
        "    <trkseg>\n"
        f"{joined_points}\n"
        "    </trkseg>\n"
        "  </trk>\n"
        "</gpx>\n"
    )


def build_gpx_filename(run_id, is_private=False):
    suffix = "-private" if is_private else ""
    return f"keep-run-{run_id}{suffix}.gpx"
