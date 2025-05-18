import os
from worldfactbook import WorldFactbook

class Populations:
    def __init__(self, config):
        self.config = config
        sub_folder = config["sub_folder"]
        resources_folder = config["resources_folder"]
        resources_path = os.path.join(resources_folder, sub_folder)
        self.resources_path = resources_path
        if not os.path.isdir(resources_path):
            os.makedirs(resources_path)
        self.worldfactbook = WorldFactbook(cache_folder=self.resources_path)
        self.generate_population_distribution()

    def generate_population_distribution(self):
        print("Generating population distribution...")
        populations = self.worldfactbook.get_populations()
        
        #replace empty strings with 0

        country_codes = self.worldfactbook.get_country_codes()
        #use country codes rather than names for easier mapping
        for country_name in populations.copy().keys():
            if country_name in country_codes:
                populations[country_codes[country_name]] = populations[country_name]
                del populations[country_name]
            else:
                print(f"Country name {country_name} not found in country codes. Skipping.")
                del populations[country_name]

        self.populations = populations

    def get_population_distribution(self):
        return self.populations

    def get_sources(self):
        return [self.worldfactbook.get_source_information()]
    





