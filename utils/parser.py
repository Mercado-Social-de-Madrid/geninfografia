import pandas as pd


class Parser:

    numeric_properties = ["ind3d", "ind3h", "ind3a", "ind20d", "ind97", "ind27", "q1203", "q1201", "q1405", "q1406", "q1413"]
    boolean_properties = ["ind58", "ind71", "ind105", "ind78", "ind80"]

    def parse_csv(self):
        df = pd.read_csv('data/datos_infografias.csv', encoding="utf-8")
        columns = df.columns.tolist()
        data = df.values

        props = [columns[1]] + df[columns[1]].to_list()

        entities = []
        for entity_index, territory_code in enumerate(columns[3:]):
            entity_data = data[:, entity_index + 3]  # Get all rows for a specific entity
            entity = {props[0]: territory_code}

            for index, value in enumerate(list(entity_data)):
                prop_name = str(props[index + 1])
                value = self.parse_value(prop_name, value)
                entity[prop_name] = str(value)

            entities.append(entity)

        return entities

    def parse_value(self, prop_name, value):
        if prop_name in self.numeric_properties:
            n = self.parse_number(value)
            return n
        elif prop_name in self.boolean_properties:
            return self.parse_boolean(value)
        else:
            return value

    def parse_number(self, value):
        suffixes = ["", "<small>MIL</small>", "M"]
        suffix_index = 0

        try:
            value = float(str(value).replace('.', '').replace(',', '.'))
        except ValueError:
            return value

        while value >= 1000 and suffix_index < len(suffixes) - 1:
            value /= 1000
            suffix_index += 1

        formatted_value = f"{value:,.1f}".rstrip('0').rstrip('.')

        return f"{formatted_value}{suffixes[suffix_index]}"

    def parse_boolean(self, value):
        return str(value).lower() == "si"
