import base64
import json
import os
import sys
import yaml
import time
from pathlib import Path
from datetime import datetime

import sass
import jinja2
import pngquant
from jinja2 import TemplateNotFound
from pathvalidate import sanitize_filename
from fuzzywuzzy import fuzz
from selenium import webdriver
from wakepy import keep

from utils.translations import Translations
from utils.parser import Parser


def get_custom_props():
    config_file = "config.yaml"
    with open(config_file, 'r', encoding='utf-8') as file:
        config = yaml.safe_load(file)
    return config


custom_props = get_custom_props()
export_percent = 0


def compile_sass():
    os.makedirs('static/css', exist_ok=True)

    styles_path = "static/sass"
    for file in os.listdir(styles_path):
        if file.startswith("styles") and file.endswith(".scss"):
            with open(f'static/sass/{file}', 'r') as scss:
                scss.read()

    sass.compile(dirname=('static/sass', 'static/css'))


def float_with_comma(value):
    try:
        cleaned_value = str(value).replace(',', '.')
        return float(cleaned_value)
    except ValueError:
        return value


def is_float(value):
    try:
        cleaned_value = str(value).replace(',', '.')
        float(cleaned_value)
        return True
    except ValueError:
        return False


def generar_infografias(entities_data, entity_name=None, regenerate=False):
    print("\n======== Generando ficheros HTML de las infografías =============")
    output_path = "infografias/html"
    os.makedirs(output_path, exist_ok=True)

    if entity_name:
        entities_data = [entity for entity in entities_data if entity_name == entity["Nombre"]]

    total_entities = len(entities_data)
    for index, entity in enumerate(entities_data):
        if not custom_props["TERRITORIOS"] or entity['Codigo Territorio'].upper() in custom_props["TERRITORIOS"]:
            print(f"[{index+1}/{total_entities}] Generando infografia para la entidad {entity['Nombre']}...")
            filename = sanitize_filename(entity["NIF"])
            langs = entity['Idioma'].split(';')
            for lang in langs:
                if not custom_props["IDIOMAS"] or lang.upper() in custom_props["IDIOMAS"]:
                    translations = get_translations_from_lang(lang)
                    html_root = f"{output_path}/{entity['Codigo Territorio'].upper()}/{lang.upper()}"
                    os.makedirs(html_root, exist_ok=True)
                    html_path = f"{html_root}/{filename}.html"
                    if regenerate or not os.path.isfile(html_path):
                        template_loader = jinja2.FileSystemLoader(searchpath="template")
                        template_env = jinja2.Environment(loader=template_loader)
                        template_env.filters['float'] = float_with_comma
                        template_env.filters['is_float'] = is_float
                        template_file = f"main_{lang}.html"
                        try:
                            template = template_env.get_template(template_file)
                        except TemplateNotFound:
                            template = template_env.get_template(custom_props["DEFAULT_TEMPLATE"])
                        output_text = template.render(**{**entity, **translations, **custom_props})

                        html_file = open(html_path, 'w', encoding="utf-8")
                        html_file.write(output_text)
                        html_file.close()
                        print(f"[{index+1}/{total_entities}] Infografía para la entidad [{entity['Nombre']}] generada.")
                    else:
                        print(f"[{index + 1}/{total_entities}] Infografía para la entidad [{entity['Nombre']}] ya existe.")


def get_translations_from_lang(lang):
    translations = {}
    try:
        with open(f"translations/{lang}.json", "r", encoding="utf-8") as translations_file:
            translations = json.loads(translations_file.read())
    except FileNotFoundError:
        pass

    return translations


def exportar_infografias(nif=None, regenerate=False):
    global export_percent
    print("\n\n======== Exportando infografías =============")

    driver = get_driver()
    driver.set_script_timeout(999999999)

    try:
        html_path = "infografias/html"
        total_tasks = get_file_count(html_path)
        territories_dirs = os.listdir(html_path)
        for territory in territories_dirs:
            if not custom_props["TERRITORIOS"] or territory.upper() in custom_props["TERRITORIOS"]:
                lang_dirs = os.listdir(f"{html_path}/{territory}")
                for lang in lang_dirs:
                    if not custom_props["IDIOMAS"] or lang.upper() in custom_props["IDIOMAS"]:
                        files_list = os.listdir(f"{html_path}/{territory}/{lang}")

                        if nif:
                            files_list = [filename for filename in files_list if nif == filename.split(".")[0]]

                        for filename in files_list:
                            html_path = "infografias/html"
                            input_file = f"{html_path}/{territory}/{lang}/{filename}"
                            driver.delete_all_cookies()
                            driver.execute_cdp_cmd('Storage.clearDataForOrigin', {
                                "origin": '*',
                                "storageTypes": 'all',
                            })
                            # driver.get(str(Path(input_file).absolute()))
                            export_percent += 100 / total_tasks
                            html2img(driver, filename, extension="png", output_path=f"infografias/png/{territory}/{lang}", regenerate=regenerate)
                            # html2img(driver, filename, extension="jpg", output_path=f"infografias/jpg/{territory}/{lang}", regenerate=regenerate)
                            # html2pdf(driver, filename, output_path=f"infografias/pdf/{territory}/{lang}", regenerate=regenerate)

    finally:
        driver.quit()


def get_file_count(path):
    file_list = []

    for root, dirs, files in os.walk(path):
        for file in files:
            file_path = os.path.join(root, file)
            file_list.append(file_path)

    return len(file_list)


def html2pdf(driver, filename, output_path="infografias/pdf", regenerate=False):
    global export_percent

    os.makedirs(output_path, exist_ok=True)
    pdf_path = f"{output_path}/{filename.split('.')[0]}.pdf"

    if regenerate or not os.path.isfile(pdf_path):
        print(f"[{round(export_percent)}%] Exportando infografía en formato PDF [{str(Path(pdf_path).absolute())}]...")
        params = {
            "paperWidth": 8.268,
            "paperHeight": 11.693,
            "marginTop": 0,
            "marginLeft": 0,
            "marginBottom": 0,
            "marginRight": 0,
            "pageRanges": "1",
            "printBackground": True
        }
        pdf = driver.execute_cdp_cmd('Page.printToPDF', params)
        decoded = base64.b64decode(pdf["data"])
        with open(pdf_path, 'wb') as output_file:
            output_file.write(decoded)

        print(f"[{round(export_percent)}%] Infografía exportada a PDF [{pdf_path}]")
    else:
        print(f"[{round(export_percent)}%] Infografía [{pdf_path}] ya existe")


def html2img(driver, filename, extension, output_path="infografias/png", regenerate=False):
    global export_percent

    os.makedirs(output_path, exist_ok=True)
    img_path = f"{output_path}/{filename.split('.')[0]}.{extension}"

    if regenerate or not os.path.isfile(img_path):
        print(f"[{round(export_percent)}%] Exportando infografia en formato {extension.upper()} [{img_path}]...")
        driver.set_window_size(width=2480, height=3508)
        driver.save_screenshot(filename=img_path)
        try:
            pngquant.config(os.environ["PNGQUANT_PATH"], min_quality=85, max_quality=85)
            pngquant.quant_image(img_path)
        except KeyError:
            print("No es posible optimizar la imagen")
            print("- Añade la variable de entorno PNGQUANT_PATH con la ubicación del ejecutable de pngquant.")
            print("Puedes descargarlo en https://pngquant.org/")
        print(f"[{round(export_percent)}%] Infografía exportada a {extension.upper()} [{img_path}]")
    else:
        print(f"[{round(export_percent)}%] Infografía [{img_path}] ya existe")


def get_driver():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--hide-scrollbars')
    chrome_options.add_argument('--window-size=2480,3508')
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    chrome_options.add_argument('--log-level=3')

    driver = webdriver.Chrome(options=chrome_options)
    return driver


def find_best_match(input_text, string_list):
    string_scores = {string: fuzz.token_sort_ratio(input_text, string) for string in string_list}
    string_scores = sorted(string_scores.items(), key=lambda item: item[1], reverse=True)
    top_matches = string_scores[:3]  # Get best three matches
    top_score = top_matches[0][1]
    if top_score >= 95:
        return top_matches[0][0]
    else:
        print(f"1. {top_matches[0][0]}")
        print(f"2. {top_matches[1][0]}")
        print(f"3. {top_matches[2][0]}")
        user_input = input("Selecciona una entidad escribiendo el número de su izquierda: ")

        if user_input in ["1", "2", "3"]:
            return top_matches[int(user_input)-1][0]
        else:
            exit(-1)


def get_args():
    entity_name = None
    regenerate = False
    if len(sys.argv) > 1:
        for arg in sys.argv:
            if arg.startswith("nombre="):
                _, entity_name = arg.split("=")
            if arg.startswith("--regenerate") or arg.startswith("-r"):
                regenerate = True

    return entity_name, regenerate


def main():
    compile_sass()
    entities_data = Parser().parse_infografias()
    Translations().generate_translations()
    entity_name, regenerate = get_args()
    nif_to_export = None
    if entity_name is not None:
        entity_name = find_best_match(entity_name, [entity["Nombre"] for entity in entities_data])
        nif_to_export = next((entity["NIF"] for entity in entities_data if entity["Nombre"] == entity_name))

    generar_infografias(entities_data, entity_name, regenerate)

    with keep.presenting() as k:
        exportar_infografias(nif_to_export, regenerate)


if __name__ == "__main__":
    main()
