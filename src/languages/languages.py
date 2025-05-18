import os
import json
from worldfactbook import WorldFactbook

class Languages:
    def __init__(self, config, population_distribution=None):
        self.config = config
        sub_folder = config["sub_folder"]
        resources_folder = config["resources_folder"]
        resources_path = os.path.join(resources_folder, sub_folder)
        self.resources_path = resources_path
        self.worldfactbook = WorldFactbook(cache_folder=self.resources_path)
        self.generate_language_distribution(population_distribution=population_distribution)

    def generate_language_distribution(self, population_distribution=None):        
        language_distribution_raw = self.worldfactbook.get_languages()
        sources = [self.worldfactbook.get_source_information()]
        country_codes = self.worldfactbook.get_country_codes()
        language_codes = self.worldfactbook.get_language_codes()

        # Normalize language codes by splitting semicolon-separated names
        for language_name in list(language_codes.keys()):
            if ";" in language_name:
                new_names = [name.strip() for name in language_name.split(";")]
                for name in new_names:
                    language_codes[name] = language_codes[language_name]
                del language_codes[language_name]

        # Cache config options
        excluded_words = self.config["output"]["excluded_words"]
        language_aliases = self.config["output"]["language_aliases"]

        # Build new distribution dict with cleaned country and language codes
        language_distribution = {}
        for country_name, country_languages in language_distribution_raw.items():
            if country_name not in country_codes:
                print(f"Country name {country_name} not found in country codes. Skipping.")
                continue

            cleaned_languages = {}
            for language_name, percentage in country_languages.items():
                # Strip excluded words
                cleaned_name = language_name
                for word in excluded_words:
                    if word in cleaned_name:
                        cleaned_name = cleaned_name.replace(word, "").strip()

                # Apply alias if available
                cleaned_name = language_aliases.get(cleaned_name, cleaned_name)

                if cleaned_name in language_codes:
                    language_code = language_codes[cleaned_name]
                    cleaned_languages[language_code] = percentage
                else:
                    print(f"Language name {cleaned_name} not found in language codes. Skipping.")

            language_distribution[country_codes[country_name]] = cleaned_languages

        # Sort countries by population distribution if available
        if population_distribution is not None:
            language_distribution = dict(sorted(
                language_distribution.items(),
                key=lambda item: population_distribution.get(item[0], 0),
                reverse=True
            ))

        # Add manual overrides
        overrides_file = self.config.get("overrides_file", None)
        if overrides_file is not None:
            with open(os.path.join(self.resources_path, overrides_file), "r") as file:
                overrides = json.load(file)
                for country_code, entry in overrides.items():
                    language_distribution[country_code] = entry["distribution"]
                    sources.append(entry["source"])

        for country_code, entry in language_distribution.items():
            #if there is only one language, set the percentage to 1
            if len(entry) == 1:
                for lang_code in entry.keys():
                    entry[lang_code] = 1
            else:
                #otherwise set unknown percentages to 0
                for lang_code in entry.keys():
                    if entry[lang_code] is None:
                        entry[lang_code] = 0
            if sum(entry.values()) < 1.0:
                # If the total is less than 1 add an undefined entry
                undefined_code = self.config["output"]["undefined_code"]
                entry[undefined_code] = 1.0 - sum(entry.values())
                
                

        # Aggregate language use (weighted by population if given)
        languages = {}
        for country_code, lang_percents in language_distribution.items():
            for lang_code, percent in lang_percents.items():
                if percent is not None and population_distribution is not None:
                    languages[lang_code] = languages.get(lang_code, 0) + percent * population_distribution.get(country_code, 0)
                else:
                    languages[lang_code] = languages.get(lang_code, 0)

        # Sort languages by total value
        languages = dict(sorted(languages.items(), key=lambda item: item[1], reverse=True))

        # Replace codes with language names (using reverse mappings)
        code_to_language = {v: k for k, v in language_codes.items()}
        language_aliases_reversed = {v: k for k, v in language_aliases.items()}

        for lang_code in list(languages.keys()):
            name = code_to_language.get(lang_code, lang_code)
            name = language_aliases_reversed.get(name, name)
            languages[lang_code] = name

        self.language_distribution = language_distribution
        self.languages = languages
        self.sources = sources

    def get_language_distribution(self):
        return self.language_distribution
    
    def get_sources(self):
        return self.sources
    
    def get_languages(self):
        return self.languages