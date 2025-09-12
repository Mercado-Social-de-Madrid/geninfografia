import os
import pandas as pd
import json

from dataclasses import dataclass

@dataclass
class Lang:
    # Column names in strings.csv translations file
    code: str
    name: str


class Translations:
    translations_dir = os.path.join(os.path.dirname(__file__), "../translations")
    df = pd.read_csv(f"{translations_dir}/strings.csv")

    CAS = Lang('cas', "Castellano")
    CAT = Lang('cat', "Català")
    EUS = Lang('eus', "Euskera")
    GAL = Lang('gal', "Galego")

    def generate_translations(self, langs=None):
        if not langs:
            langs = [self.CAS, self.CAT, self.EUS, self.GAL]

        for lang in langs:
            output_filename = f"{self.translations_dir}/{lang.code}.json"
            data = dict(zip(self.df['Código'], self.df[lang.name].str.strip()))

            with open(output_filename, 'w', encoding='utf-8') as file:
                json.dump(data, file, ensure_ascii=False, indent=4)
