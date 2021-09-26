import requests
import json
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import os
import math
import random
import numpy as np
import datetime as dt

# CONSTATS

DRAW_POSITIONS = {
    0: (500, 300),
    1: (50, 450),
    2: (50, 1200),
    3: (1000, 1200),
    4: (1000, 400),
}

FONT_FILE_NAME = "bitty_monospace.otf"
FONT_SIZE_INFO = 16
FONT_SIZE_SUBTITLE = 30

RESOURCE_FOLDER_NAME = "Resources"
BACKGROUND_FILE_NAME = "complete_bg.png"
ASTEROID_FILE_NAME = "asteroid_144.png"

EXPORT_FILE_NAME_NOEXT = "NEO-Situation"

RESOURCE_FOLDER = os.path.join(os.getcwd(), RESOURCE_FOLDER_NAME)
ASTEROID_IMAGE = Image.open(os.path.join(RESOURCE_FOLDER, ASTEROID_FILE_NAME))

MIN_ASTEROID_DISTANCE = 250
INTER_ASTEROID_DISTANCE = 50

with open("api_key.txt", "r") as f:
    API_KEY =  f.read().strip()

# CLASSES

class Asteroid():
    def __init__(self, name, id, speed, distance, date, min_diam, max_diam, diam, dist_rank):
        self.name = name
        self.id = id
        self.speed = speed
        self.distance = distance
        self.date = date
        self.min_diam = min_diam
        self.max_diam = max_diam
        self.diam = diam
        self.dist_rank = dist_rank

# FUNCTIONS

def request_neos(api_key, start_date, end_date=None):
    start = f"start_date={start_date}"
    end = "" if end_date == None else f"&end_date={end_date}" 
    api = f"&api_key={api_key}"
    link = f"https://api.nasa.gov/neo/rest/v1/feed?{start}{end}{api}"
    r = requests.get(link)
    return r.json()["near_earth_objects"]

def get_neos(raw_dict):
    neos_list = []
    raw_dates = []

    for date, data in raw_dict.items():
        raw_dates.append(date)
        for neo in data:
            try:
                ext_neo = {
                    "name": neo.get("name"),
                    "id": neo.get("id"),
                    "est_diam_meters": [round(neo.get("estimated_diameter").get("meters").get("estimated_diameter_min"), 2), 
                        round(neo.get("estimated_diameter").get("meters").get("estimated_diameter_max"), 2)],
                    "speed_kmh": round(float(neo.get("close_approach_data")[0].get("relative_velocity").get("kilometers_per_hour"))),
                    "miss_distance_km": round(float(neo.get("close_approach_data")[0].get("miss_distance").get("kilometers"))),
                    "approach_date": neo.get("close_approach_data")[0].get("close_approach_date")
                }
            except AttributeError:
                pass
            else:
                neos_list.append(ext_neo)

    dates_list = [dt.datetime.strptime(date, "%Y-%m-%d").date() for date in raw_dates]
    start = min(dates_list)
    end = max(dates_list)
    return neos_list, start, end

def add_rank(neos_df):
    neos_df["draw_rank"] = list(range(5))
    return neos_df

def create_df(neos_list):
    names = [i.get("name") for i in neos_list]
    ids = [i.get("id") for i in neos_list]

    min_diam = np.array([i.get("est_diam_meters")[0] for i in neos_list])
    max_diam = np.array([i.get("est_diam_meters")[1] for i in neos_list])
    avg_diam = min_diam + max_diam / 2

    speed = [i.get("speed_kmh") for i in neos_list]
    miss_dist = [i.get("miss_distance_km") for i in neos_list]
    app_dates = [i.get("approach_date") for i in neos_list]

    data = {
        "den": names,
        "id": ids,
        "min_diam": min_diam,
        "max_diam": max_diam,
        "avg_diam": avg_diam,
        "speed": speed,
        "miss_dist": miss_dist,
        "app_date": app_dates
    }

    raw_df = pd.DataFrame(data)
    
    dist_df = raw_df.sort_values(by="miss_dist")[:5]

    ranked_df = add_rank(dist_df)
    
    return ranked_df

def neos_to_asteroids(ranked_df):
    ast_list = []
    for i in range(len(ranked_df)):
        ast = ranked_df.iloc[i]
        ast_obj = Asteroid(ast.den, ast.id, ast.speed, ast.miss_dist, ast.app_date, ast.min_diam, ast.max_diam, ast.avg_diam, ast.draw_rank)
        ast_list.append(ast_obj)
    ast_diams = [ast.diam for ast in ast_list]
    return ast_list, ast_diams

def draw_asteroids(image, ast_list, ast_diams):
    for ast in ast_list:

        ast_perc = (ast.diam -  min(ast_diams)) / (max(ast_diams) - min(ast_diams))
        size_perc = 0.5 + 0.5 * ast_perc
        ast_size = (int(size_perc * ASTEROID_IMAGE.size[0]), int(size_perc * ASTEROID_IMAGE.size[1]))

        size_diff = (ASTEROID_IMAGE.size[0] - ast_size[0]) / 2

        ast_image = ASTEROID_IMAGE.rotate(
            random.randrange(360)
            ).resize(ast_size)

        angle = 72 * ast.dist_rank / 180 * math.pi
        dist = MIN_ASTEROID_DISTANCE + INTER_ASTEROID_DISTANCE * ast.dist_rank
        
        paste_x = image.size[0]//2 - int(dist * math.sin(angle)) - ast_image.size[0]//2 + int(size_diff * math.sin(angle))
        paste_y = image.size[0]//2 - int(dist * math.cos(angle)) - ast_image.size[1]//2 + 72 + int(size_diff * math.cos(angle))
        image.paste(ast_image, (paste_x, paste_y), ast_image)

    return image

def draw_subtitle(image, start, end):
    font = ImageFont.truetype(os.path.join(RESOURCE_FOLDER, FONT_FILE_NAME), FONT_SIZE_SUBTITLE)
    d = ImageDraw.Draw(image)
    d.text((50, 140), f"from {start} to {end}", font= font, fill=(0, 172, 0))

    return image

def draw_info(image, ast_list):

    for ast in ast_list:
        info = Image.new("RGBA", (500, 250), (0, 0, 0, 0))
        font = ImageFont.truetype(os.path.join(RESOURCE_FOLDER, FONT_FILE_NAME), FONT_SIZE_INFO)
        d = ImageDraw.Draw(info)
        text = f"Name:{ast.name}\nMiss distance: {ast.distance} km\nApproach date: {ast.date}\nDiameter(min): {ast.min_diam} m\nDiameter(max): {ast.max_diam} m"
        d.multiline_text((10, 10), text, font= font, fill=(0, 172, 0))
        image.paste(info, DRAW_POSITIONS[ast.dist_rank], info)
    
    return image

def generate_report(image, ast_list, ast_diams, start, end):
    subtitled_report = draw_subtitle(image, start, end)
    drawn_report = draw_asteroids(subtitled_report, ast_list, ast_diams)
    info_report = draw_info(drawn_report, ast_list)
    info_report.save(f"{EXPORT_FILE_NAME_NOEXT}from{start}to{end}.png")

def get_dependencies(start, end):
    neos = request_neos(API_KEY, start, end)
    extracted_neos, date_start, date_end = get_neos(neos)
    df = create_df(extracted_neos)
    ast_list, ast_diams = neos_to_asteroids(df)
    return ast_list, ast_diams, date_start, date_end

def main(start, end):
    asteroid_list, asteroid_diameters, start_date, end_date = get_dependencies(start, end)
    report = Image.open(os.path.join(RESOURCE_FOLDER, BACKGROUND_FILE_NAME)).copy()
    generate_report(report, asteroid_list, asteroid_diameters, start_date, end_date)

