import base64
import json
import os
import sys
from pathlib import Path
from datetime import datetime

import sass
import jinja2
from pathvalidate import sanitize_filename
from fuzzywuzzy import fuzz
from selenium import webdriver
from selenium.webdriver.common.print_page_options import PrintOptions

from utils.translations import Translations
from utils.parser import Parser

export_percent = 0


def compile_sass():
    os.makedirs('static/css', exist_ok=True)

    with open('static/sass/styles.scss', 'r') as scss:
        scss.read()

    sass.compile(dirname=('static/sass', 'static/css'))


def get_custom_props():
    return {
        "year": datetime.now().year
    }


def generar_infografias(entities_data, entity_name=None):
    print("\n======== Generando ficheros HTML de las infografías =============")
    output_path = "infografias/html"
    os.makedirs(output_path, exist_ok=True)
    custom_props = get_custom_props()

    if entity_name:
        entities_data = [entity for entity in entities_data if entity_name == entity["Nombre"]]

    total_entities = len(entities_data)
    for index, entity in enumerate(entities_data):
        print(f"[{index+1}/{total_entities}] Generando infografia para la entidad {entity['Nombre']}...")
        langs = entity['Idioma'].split(';')
        for lang in langs:
            translations = get_translations_from_lang(lang)

            template_loader = jinja2.FileSystemLoader(searchpath="template")
            template_env = jinja2.Environment(loader=template_loader)
            template_file = "main.html"
            template = template_env.get_template(template_file)
            output_text = template.render(**{**entity, **translations, **custom_props})

            filename = sanitize_filename(entity["NIF"])
            html_path = f'{output_path}/{filename}_{lang.lower()}.html'
            html_file = open(html_path, 'w', encoding="utf-8")
            html_file.write(output_text)
            html_file.close()
            print(f"[{index+1}/{total_entities}] Infografía para la entidad [{entity['Nombre']}] generada.")


def get_translations_from_lang(lang):
    translations = {}
    try:
        with open(f"translations/{lang}.json", "r", encoding="utf-8") as translations_file:
            translations = json.loads(translations_file.read())
    except FileNotFoundError:
        pass

    return translations


def exportar_infografias(entity_name):
    global total_tasks
    print("\n\n======== Exportando infografías =============")
    html_path = "infografias/html"
    files_list = os.listdir(html_path)

    if entity_name:
        files_list = [filename for filename in files_list if sanitize_filename(entity_name) == filename.split('.')[0]]

    total_tasks = len(files_list)

    for filename in files_list:
        html2img(filename, total_tasks)
        html2pdf(filename, total_tasks)


def html2pdf(filename, total_tasks):
    global export_percent
    html_path = "infografias/html"
    output_path = "infografias/pdf"
    os.makedirs(output_path, exist_ok=True)

    input_file = f"{html_path}/{filename}"
    pdf_path = f"{output_path}/{filename.split('.')[0]}.pdf"

    print(f"[{round(export_percent)}%] Exportando infografía en formato PDF [{str(Path(pdf_path).absolute())}]...")

    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--hide-scrollbars')
    chrome_options.add_argument('--window-size=2480,3508')
    settings = {
        "recentDestinations": [{
            "id": "Save as PDF",
            "origin": "local",
            "account": ""
        }],
        "selectedDestinationId": "Save as PDF",
        "version": 2,
        "isHeaderFooterEnabled": False,
        "isCssBackgroundEnabled": True
    }

    prefs = {
        "printing.print_preview_sticky_settings.appState": json.dumps(settings),
    }
    chrome_options.add_argument('--kiosk-printing')
    chrome_options.add_experimental_option('prefs', prefs)
    # driver_path = ChromeDriverManager().install()
    driver = webdriver.Chrome(options=chrome_options)

    try:
        driver.get(str(Path(input_file).absolute()))
        print_options = PrintOptions()
        print_options.page_height = 2480
        print_options.page_width = 3508
        pdf = driver.print_page()
        decoded = base64.b64decode(pdf)
        with open(pdf_path, 'wb') as output_file:
            output_file.write(decoded)

        export_percent += 100 / total_tasks
        print(f"[{round(export_percent)}%] Infografía exportada a PDF [{pdf_path}]")
    finally:
        driver.quit()


def html2img(filename, total_tasks, extension="png"):
    global export_percent
    html_path = "infografias/html"
    output_path = f"infografias/{extension}"

    os.makedirs(output_path, exist_ok=True)

    input_file = f"{html_path}/{filename}"
    img_path = f"{output_path}/{filename.split('.')[0]}.{extension}"

    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--hide-scrollbars')
    chrome_options.add_argument('--window-size=2480,3508')

    chrome_options.add_argument('--kiosk-printing')
    # driver_path = ChromeDriverManager().install()
    driver = webdriver.Chrome(options=chrome_options)

    try:
        print(f"[{round(export_percent)}%] Exportando infografia en formato {extension.upper()} [{img_path}]...")
        driver.set_window_size(width=2480, height=3508)
        driver.get(str(Path(input_file).absolute()))

        driver.save_screenshot(filename=img_path)
        export_percent += 100 / total_tasks
        print(f"[{round(export_percent)}%] Infografía exportada a {extension.upper()} [{img_path}]")
    finally:
        driver.quit()


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


def get_entity_name_from_args():
    entity_name = None
    if len(sys.argv) == 2 and sys.argv[1].startswith("nombre="):
        _, entity_name = sys.argv[1].split("=")
        entity_name = find_best_match(entity_name, [entity["Nombre"] for entity in entities_data])
    return entity_name


if __name__ == "__main__":
    compile_sass()
    entities_data = Parser().parse_csv()
    Translations().generate_translations()
    entity_name = get_entity_name_from_args()
    generar_infografias(entities_data, entity_name)
    exportar_infografias(entity_name)


