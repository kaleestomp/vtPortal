import random
import math
import re
from datetime import timedelta

class general_utilities:
    @staticmethod

    def make_color_brighter(color: str, factor: float = 0.5) -> str:
        if not color.startswith('rgb(') or not color.endswith(')'):
            raise ValueError("Color must be in the format 'rbg(xxx,xxx,xxx)'")
        color = color[4:-1].replace(" ", "")
        r, b, g = map(int, color.split(','))

        r = min(int(r + (255 - r) * factor), 255)
        g = min(int(g + (255 - g) * factor), 255)
        b = min(int(b + (255 - b) * factor), 255)

        return f'rgb({r},{b},{g})'

    def add_alpha(color: str, alpha: float = 0.5) -> str:
        return f"rgba({color[4:-1]}, {alpha})"
    
    def get_points(n, width, length, min_distance:list=[1.2,0.8,0.4], max_attempts=20):
        points = []
        collision_count = 0
        for _ in range(n):
            compromise_level = 0
            while compromise_level < len(min_distance) - 1:
                coordinate_found = False
                for attempt in range(max_attempts):
                    min_dist = min_distance[compromise_level]
                    x = random.uniform(min_dist/2, width - min_dist/2)
                    y = random.uniform(min_dist/2, length - min_dist/2)
                    collision = False
                    for px, py in points:
                        if math.hypot(px - x, py - y) < min_distance[compromise_level]:
                            collision = True
                            break
                    if not collision:
                        points.append((x, y))
                        coordinate_found = True
                        break
                    elif attempt == max_attempts - 1:
                        compromise_level += 1
                        continue
                if coordinate_found: 
                    break
            if not coordinate_found:
                collision_count += 1
                points.append((x, y))
        print(f"Warning: {collision_count} people can not fit.")
        return points
    def get_points2(n, width, length, min_distance=1.2, max_attempts=50):
        points = []
        collision_count = 0
        for _ in range(n):
            for attempt in range(max_attempts):
                x = random.uniform(min_distance/2, width - min_distance/2)
                y = random.uniform(min_distance/2, length - min_distance/2)
                collision = False
                for px, py in points:
                    if math.hypot(px - x, py - y) < min_distance:
                        collision = True
                        break
                if not collision:
                    points.append((x, y))
                    break
                elif attempt == max_attempts - 1:
                    collision_count += 1
                    points.append((x, y))
        print(f"Warning: {collision_count} point has to compromise.")
        return points
    
    def los_calculator (area:float) -> dict:
        grade_references = [
            {"grade": "A", "min": 1.21, "max": float('inf'), "tag": "Free Circulation Zone", "description": "Space is provided for standing and free cirulation wtihout distubring others."},
            {"grade": "B", "min": 0.93, "max": 1.21, "tag": "Restricted Circulation Zone", "description": "Space is provided for standing and restricted cirulation wtihout distubring others."},
            {"grade": "C", "min": 0.65, "max": 0.93, "tag": "Personal Comfort Zone", "description": "Within perosnal comfort range space is provided for standing and restricted circulation without disturbing others."},
            {"grade": "D", "min": 0.28, "max": 0.65, "tag": "No Touch Zone", "description": "Space is provided for standing without personal contact with others. Circulation is severely restricted."},
            {"grade": "E", "min": 0.19, "max": 0.28, "tag": "Touch Zone", "description": "Space is provided for standing but personal contact with others is unavoidable."},
            {"grade": "F", "min": 0.0, "max": 0.19, "tag": "The Body Ellipse", "description": "Standing is possible but close unavoidable contact with surrounding standees cause physical and psychological discomfort."},
        ]
        for i, ref in enumerate(grade_references):
            if area >= ref["min"] and area < ref["max"]:
                return ref
    
    def get_ellipse_radius(area, ratio = 450/600) -> tuple:
        r = math.sqrt(area / (math.pi * ratio))
        return r, r* ratio
    def get_radius(area):
        return math.sqrt(area / math.pi)

    def get_path_from_svg(svg_path: str) -> str:
        svg_content = ""
        with open(svg_path, 'r', encoding='utf-8') as file:
            svg_content = file.read()
        """
        Extracts all <path> d attributes from the SVG content and concatenates them
        into a single ECharts symbol string (path://...).

        Args:
            svg_content (str): The SVG file content as a string.

        Returns:
            str: ECharts-compatible symbol string.
        """
        # Find all d="..." attributes in <path> tags
        path_ds = re.findall(r'<path[^>]*d="([^"]+)"', svg_content)
        if not path_ds:
            raise ValueError("No <path> elements with d attribute found.")
        # Concatenate all d paths, separated by space (no separator is also fine)
        combined_path = ' '.join(path_ds)
        # Return in ECharts path symbol format
        return f'path://{combined_path}'
    
    def seconds_to_hhmmss(seconds):
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def hhmmss_to_timedelta(hhmmss_str):
        h, m, s = map(int, hhmmss_str.split(":"))
        return timedelta(hours=h, minutes=m, seconds=s)
    
    def hhmmss_to_seconds(hhmmss_str):
        h, m, s = map(int, hhmmss_str.split(":"))
        return h * 3600 + m * 60 + s

