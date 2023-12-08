import locale

import pandas as pd


class Parser:

    int_properties = ["ind3d", "ind3h", "ind3a", "ind20d",
                      "ind97", "q1203", "q1201", "q1405",
                      "q1406", "q1413", "ind254", "ind6",
                      "ind7", "ind67agru", "ind1d", "ind1h", "ind1a"]

    float_properties = []

    boolean_properties = ["ind58", "ind62", "q4104a", "q4104b", "q4104c",
                          "q4104d", "q5305a", "q5305b", "q5305c",
                          "q5305d", "ind71", "ind105", "ind78", "ind80"]

    def parse_infografias(self):
        territories = self.parse_territories()
        df = pd.read_csv('data/datos_infografias.csv', encoding="utf-8")
        columns = df.columns.tolist()
        data = df.values

        props = [columns[1]] + df[columns[1]].to_list()

        entities = []
        for entity_index, territory_code in enumerate(columns[4:]):
            try:
                territory_code = territory_code.split(".")[0]
                entity_data = data[:, entity_index + 4]  # Get all rows for a specific entity
                entity = {props[0]: territory_code, **territories[territory_code]}

                for index, value in enumerate(list(entity_data)):
                    prop_name = str(props[index + 1])
                    prop_name = self.replace_unallowed_symbols(prop_name)
                    value = self.parse_value(prop_name, value)
                    entity[prop_name] = str(value)

                entities.append(entity)
            except KeyError:
                pass

        return entities

    def parse_territories(self):
        df = pd.read_csv('data/datos_territorios.csv', encoding="utf-8")
        df = df.fillna('')

        territories = {}
        for index, row in df.iterrows():
            territories[row["Código"]] = {}
            territories[row["Código"]]["logo_reas"] = row["Logo 1 reas"]
            territories[row["Código"]]["logo_mercado"] = row["Logo 2 mercado"]
            territories[row["Código"]]["web"] = row["web territorio"]
            territories[row["Código"]]["email"] = row["email"]

        return territories

    def parse_value(self, prop_name, value):
        if prop_name in self.int_properties:
            return self.parse_number(value, number_type=int)
        elif prop_name in self.float_properties:
            return self.parse_number(value, number_type=float)
        elif prop_name in self.boolean_properties:
            return self.parse_boolean(value)
        else:
            return value

    def parse_number(self, value, number_type):
        suffixes = ["", "<small>MIL</small>", "M"]
        suffix_index = 0

        try:
            locale.setlocale(locale.LC_ALL, 'es_ES')
            value = locale.atof(str(value).replace(" ", ""))
            if number_type is int:
                value = round(value)

        except ValueError:
            return value

        while value >= 1000 and suffix_index < len(suffixes) - 1:
            value /= 1000
            suffix_index += 1

        formatted_value = f"{value:,.1f}".rstrip('0').rstrip('.').replace('.', ',')

        return f"{formatted_value}{suffixes[suffix_index]}"

    def parse_boolean(self, value):
        if str(value).lower() == "si":
            return True
        elif str(value).lower() == "no":
            return False
        else:
            return value

    def replace_unallowed_symbols(self, prop_name):
        return str(prop_name).replace("/", "_")