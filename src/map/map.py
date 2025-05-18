import os
import datetime
import collections
import requests
import geopandas
import shapely
import triangle as tri
import numpy as np
import matplotlib.pyplot as plt
import faulthandler

faulthandler.enable()

class Map:
    def __init__(self, config, language_distribution=None):
        self.config = config
        self.language_distribution = language_distribution

        sub_folder = config["sub_folder"]
        resources_folder = config["resources_folder"]
        self.resources_path = os.path.join(resources_folder, sub_folder)
        os.makedirs(self.resources_path, exist_ok=True)

        self.sources = []
        self.language_polygons = {}

        self.generate_map()

    def generate_map(self):
        file_path = self._download_data()
        print("Loading data...")
        geo_data_frame = geopandas.read_file(file_path)
        print("Data loaded successfully.")

        print("Creating country polygons...")
        country_polygons = self._generate_country_polygons(geo_data_frame)
        print("Country polygons created successfully.")

        # self._visualise_country_polygons(country_polygons)

        print("Assigning country polygons based on language distribution...")
        self.language_polygons = self._assign_country_polygons(country_polygons)
        print("Country polygons assigned successfully.")

    def get_language_polygons(self):
        return self.language_polygons

    def get_sources(self):
        return self.sources

    def _download_data(self):
        url = self.config["source"]["url"]
        file_name = self.config["source"]["file_name"]
        file_path = os.path.join(self.resources_path, file_name)

        print("Downloading data...")
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            with open(file_path, "wb") as file:
                for block in response.iter_content():
                    file.write(block)
            print("Download complete.")
        except Exception:
            print("Error downloading data from: " + url)
            print("Continuing with previously downloaded data...")

        self.sources.append({
            "name": "Natural Earth",
            "url": url,
            "copyright": "public domain",
            "accessed_on": datetime.date.today().isoformat()
        })

        return file_path

    def _generate_country_polygons(self, geo_data_frame):
        config = self.config["output"]

        excluded_countries = config["excluded_countries"]
        geo_data_frame = geo_data_frame[~geo_data_frame["NAME"].isin(excluded_countries)]

        southernmost_latitude = config.get("southernmost_latitude")
        northernmost_latitude = config.get("northernmost_latitude")
        bounds = geo_data_frame.total_bounds

        if southernmost_latitude is not None and bounds[1] < southernmost_latitude:
            bounds[1] = southernmost_latitude
        if northernmost_latitude is not None and bounds[3] > northernmost_latitude:
            bounds[3] = northernmost_latitude

        geo_data_frame = geo_data_frame.clip(bounds)
        geo_data_frame = geo_data_frame.to_crs(config["map_projection"])

        country_polygons = {}
        random_seed = config["random_seed"]
        grid_length = config["grid_length"]
        grid_relative_std_dev = config["grid_relative_std_dev"]
        min_relative_distance = config["min_relative_distance"]

        for _, entry in geo_data_frame.iterrows():
            country = entry["NAME"]
            country_code = entry["ISO_A3"]
            print(f"Processing {country}...")

            geometry = entry["geometry"]
            outlines = []

            if isinstance(geometry, shapely.geometry.Polygon):
                outlines.append(geometry)
            elif isinstance(geometry, shapely.geometry.MultiPolygon):
                outlines.extend(geometry.geoms)
            else:
                print("Unknown geometry type for country: " + country)
                continue

            random_number_generator = np.random.default_rng(random_seed)
            polygons = []

            for outline in outlines:
                outline = shapely.ops.transform(
                    lambda x, y, z=None: self._transform_coordinates(x, y, geo_data_frame),
                    outline
                )

                x_min, y_min, x_max, y_max = outline.bounds
                number_of_rows = int((y_max - y_min) / grid_length)
                number_of_columns = int((x_max - x_min) / grid_length)
                points = []

                for row in range(number_of_rows):
                    for column in range(number_of_columns):
                        x = random_number_generator.normal(
                            x_min + column * grid_length,
                            grid_relative_std_dev * grid_length
                        )
                        y = random_number_generator.normal(
                            y_min + row * grid_length,
                            grid_relative_std_dev * grid_length
                        )

                        point = shapely.geometry.Point(x, y)
                        if outline.contains(point) and (
                            outline.exterior.distance(point) > (grid_length * min_relative_distance)
                        ):
                            points.append(point)

                if points:
                    number_of_grid_points = len(points)
                    points.extend([shapely.geometry.Point(coord) for coord in outline.exterior.coords])

                    constraints = [
                        [number_of_grid_points + i, number_of_grid_points + i + 1]
                        for i in range(len(outline.exterior.coords) - 1)
                    ]
                    constraints.append([len(points) - 1, number_of_grid_points])

                    vertices = np.array([[p.x, p.y] for p in points])
                    result = tri.triangulate({"vertices": vertices, "segments": constraints}, "pi")

                    for triangle in result["triangles"]:
                        polygons.append([result["vertices"][i].tolist() for i in triangle])
                else:
                    polygons.append([[x, y] for x, y in outline.exterior.coords])

            country_polygons[country_code] = polygons
            print(f"Created {len(polygons)} polygons for {country}")

        return country_polygons

    def _transform_coordinates(self, x, y, geo_data_frame):
        bounds = geo_data_frame.total_bounds
        width = bounds[2] - bounds[0]
        height = bounds[3] - bounds[1]
        new_width = self.config["output"]["width"]
        new_height = self.config["output"]["height"]
        new_x = (x - bounds[0]) * new_width / width
        new_y = (y - bounds[1]) * new_height / height
        return new_x, new_y

    def _assign_country_polygons(self, country_polygons):
        language_polygons = {}
        for country_code, polygons in country_polygons.items():
            country_language_distribution = self.language_distribution.get(country_code)

            if country_language_distribution:
                n_country_polygons = len(polygons)
                country_polygon_distribution = self._dhont(n_country_polygons, country_language_distribution)

                assigned = collections.defaultdict(list)
                indices = np.arange(n_country_polygons)
                np.random.default_rng(self.config["output"]["random_seed"]).shuffle(indices)

                idx = 0
                for lang, count in country_polygon_distribution.items():
                    assigned[lang] = [polygons[i] for i in indices[idx:idx + count]]
                    idx += count

                for lang, polys in assigned.items():
                    if polys:
                        language_polygons.setdefault(lang, []).extend(polys)
            else:
                print(f"Country {country_code} not found in language distribution. Assigning to undefined.")
                undefined_code = self.config["output"]["undefined_code"]
                language_polygons.setdefault(undefined_code, []).extend(polygons)

        return language_polygons

    def _visualise_country_polygons(self, country_polygons):
        colors = ["#f3f4f6", "#e5e7eb", "#d1d5db"]
        plt.figure()
        plt.axis("equal")
        plt.xlim(0, 1920)
        plt.ylim(0, 1080)

        for i, polygons in enumerate(country_polygons.values()):
            for j, polygon in enumerate(polygons):
                plt.fill(*zip(*polygon), color=colors[(i + j) % len(colors)])

        plt.show()

    def _dhont(self, nSeats, votes):
        t_votes = votes.copy()
        seats = {key: 0 for key in votes}

        while sum(seats.values()) < nSeats:
            max_v = max(t_votes.values())
            next_seat = max(t_votes, key=t_votes.get)
            seats[next_seat] += 1
            t_votes[next_seat] = votes[next_seat] / (seats[next_seat] + 1)

        return seats
