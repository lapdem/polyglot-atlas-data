import yaml
import os
import json

from populations.populations import Populations
from languages.languages import Languages
from map.map import Map


config = yaml.safe_load(open("config.yaml", "r"))

output_folder = config["output"]["folder"]
if not os.path.isdir(output_folder):
        os.makedirs(output_folder)

sources = {}


populatins = Populations(config["populations"])
population_distribution = populatins.get_population_distribution()
with open(os.path.join(output_folder, "population_distribution.json"), "w") as file:
    json.dump(population_distribution, file, indent=4)

sources["populations"] = populatins.get_sources()


languages = Languages(config["languages"], population_distribution=population_distribution)

language_distribution = languages.get_language_distribution()
with open(os.path.join(output_folder, "language_distribution.json"), "w") as file:
    json.dump(language_distribution, file, indent=4)

language_translations = languages.get_languages()
translations_folder = config["output"]["translations_folder"]
if not os.path.isdir(os.path.join(output_folder, translations_folder)):
    os.makedirs(os.path.join(output_folder, translations_folder))
with open(os.path.join(output_folder, translations_folder,"languages.json"), "w") as file:
    json.dump(language_translations, file, indent=4)

language_keys = list(language_translations.keys())
with open(os.path.join(output_folder, "language_keys.json"), "w") as file:
    json.dump(language_keys, file, indent=4)

sources["languages"] = languages.get_sources()


map = Map(config["map"], language_distribution=language_distribution)
language_polygons = map.get_language_polygons()
with open(os.path.join(output_folder, "language_polygons.json"), "w") as file:
    json.dump(language_polygons, file, indent=4)

sources["map"] = map.get_sources()


with open(os.path.join(output_folder, "sources.json"), "w") as file:
    json.dump(sources, file, indent=4)

