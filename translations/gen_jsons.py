import pandas as pd
import json

df = pd.read_csv("strings.csv")

def gen_json(column_name, output_filename):

    data = dict(zip(df['Código'], df[column_name].str.strip()))

    with open(output_filename, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

gen_json('Castellano', 'cas.json')
gen_json('Català', 'cat.json')
gen_json('Euskera', 'eus.json')
gen_json('Galego', 'gal.json')