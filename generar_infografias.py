import base64
import json
import os
import sys
import yaml
import re
import shutil

import sass
import jinja2
import pngquant
from jinja2 import TemplateNotFound, pass_context
from markupsafe import Markup
from pathvalidate import sanitize_filename
from fuzzywuzzy import fuzz
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from wakepy import keep
from PIL import Image

from .utils.translations import Translations
from .utils.parser import Parser

ROOT_DIR = os.path.dirname(__file__)

def get_custom_props():
    config_file = os.path.join(ROOT_DIR, "config.yaml")
    with open(config_file, 'r', encoding='utf-8') as file:
        config = yaml.safe_load(file)
    return config


custom_props = get_custom_props()
export_percent = 0


def compile_sass():
    sass_dir = os.path.join(ROOT_DIR, "static/sass")
    css_dir = os.path.join(ROOT_DIR, "static/css")

    os.makedirs(css_dir, exist_ok=True)

    for file in os.listdir(sass_dir):
        if file.startswith("styles") and file.endswith(".scss"):
            with open(os.path.join(sass_dir, file), 'r') as scss:
                scss.read()

    sass.compile(dirname=(sass_dir, css_dir))

compile_sass()


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

@pass_context
def subrender_filter(context, value):
    _template = context.eval_ctx.environment.from_string(value)
    result = _template.render(**context)
    if context.eval_ctx.autoescape:
        result = Markup(result)
    return result

def generar_infografias(output_path, mode, entities_data, entity_name=None, regenerate=False):
    print("\n======== Generando ficheros HTML de las infografías =============")
    output_path = f"{output_path}/html"
    os.makedirs(output_path, exist_ok=True)

    if entity_name:
        entities_data = [entity for entity in entities_data if entity_name == entity["Nombre"]]

    total_entities = len(entities_data)
    print(f"Número de entidades: {total_entities}")
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
                        template_loader = jinja2.FileSystemLoader(searchpath=os.path.join(ROOT_DIR, "template"))
                        template_env = jinja2.Environment(loader=template_loader)
                        template_env.filters['float'] = float_with_comma
                        template_env.filters['is_float'] = is_float
                        template_env.filters['subrender'] = subrender_filter
                        template_file = f"{mode}_{lang.upper()}.html"
                        try:
                            template = template_env.get_template(template_file)
                        except TemplateNotFound:
                            template = template_env.get_template(f"{mode}.html")

                        output_text = template.render(**{**entity, **translations, **custom_props})

                        html_file = open(html_path, 'w', encoding="utf-8")
                        html_file.write(output_text)
                        html_file.close()
                        print(f"[{index+1}/{total_entities}] Infografía para la entidad [{entity['Nombre']}] generada.")
                    else:
                        print(f"[{index + 1}/{total_entities}] Infografía para la entidad [{entity['Nombre']}] ya existe.")


def get_translations_from_lang(lang):
    translations = {}
    translations_dir = os.path.join(ROOT_DIR, "translations")

    try:
        with open(os.path.join(translations_dir, f"{lang}.json"), "r", encoding="utf-8") as translations_file:
            translations = json.loads(translations_file.read())
    except FileNotFoundError:
        pass

    return translations

def copy_static_files(output_path):
    static_dir = "static"
    source = os.path.join(ROOT_DIR, static_dir)
    dest = os.path.join(output_path, "html", static_dir)
    shutil.copytree(source, dest, dirs_exist_ok=True)

def exportar_infografias(output_path, nif, regenerate, selenium_host, selenium_port):
    global export_percent
    print("\n\n======== Exportando infografías =============")

    options = webdriver.ChromeOptions()
    options.add_argument('--hide-scrollbars')
    options.add_argument('--window-size=2480,3508')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.add_argument('--log-level=3')

    with webdriver.Remote(f"http://{selenium_host}:{selenium_port}/wd/hub", options=options) as driver:
        html_path = os.path.join(ROOT_DIR, output_path, "html")
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
                            filename = filename.split('.')[0]
                            input_file = f"{html_path}/{territory}/{lang}/{filename}.html"
                            print(f"Input file: file://{input_file}")
                            driver.delete_all_cookies()
                            # driver.execute_cdp_cmd('Storage.clearDataForOrigin', {
                            #     "origin": '*',
                            #     "storageTypes": 'all',
                            # })

                            try:
                                driver.get(f"file://{input_file}")
                                WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.CLASS_NAME, "highcharts-container")))
                            except TimeoutException:
                                print("Timout waiting for highchart to load.")
                            export_percent += 100 / total_tasks
                            html2img(driver, filename, extension="png", output_path=f"{output_path}/png/{territory}/{lang}", regenerate=regenerate)
                            img2pdf(filename, input_path=f"{output_path}/png/{territory}/{lang}", output_path=f"{output_path}/pdf/{territory}/{lang}")
                            # html2img(driver, filename, extension="jpg", output_path=f"infografias/jpg/{territory}/{lang}", regenerate=regenerate)
                            # html2pdf(driver, filename, output_path=f"infografias/pdf/{territory}/{lang}", regenerate=regenerate)


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
        print(f"[{round(export_percent)}%] Exportando infografía {filename.split('.')[0]} en formato PDF.")
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
    img_path = f"{output_path}/{filename}.{extension}"

    if regenerate or not os.path.isfile(img_path):
        print(f"[{round(export_percent)}%] Exportando infografia en formato {extension.upper()} [{img_path}]...")
        driver.set_window_size(width=2480, height=3700)
        driver.save_screenshot(filename=img_path)
        try:
            pngquant.config(custom_props["PNGQUANT_PATH"], min_quality=85, max_quality=85)
            pngquant.quant_image(img_path)
        except KeyError as e:
            print(e)
            print("No es posible optimizar la imagen")
            print("- Añade la ubicación de pngquant en el archivo config.yaml usando la propiedad PNGQUANT_PATH.")
            print("Puedes descargarlo en https://pngquant.org/")
        print(f"[{round(export_percent)}%] Infografía exportada a {extension.upper()} [{img_path}]")
    else:
        print(f"[{round(export_percent)}%] Infografía [{img_path}] ya existe")


def img2pdf(filename, input_path, output_path, regenerate=False):
    os.makedirs(output_path, exist_ok=True)
    input_path = input_path + f"/{filename}.png"
    output_path = output_path + f"/{filename}.pdf"
    if regenerate or not os.path.isfile(output_path):
        print(f"[{round(export_percent)}%] Exportando infografia en formato PDF [{output_path}]...")
        image = Image.open(input_path).convert("RGB")
        image.save(output_path, optimize=True, quality=65)
        print(f"[{round(export_percent)}%] Infografía exportada a PDF [{output_path}]")
    else:
        print(f"[{round(export_percent)}%] Infografía [{output_path}] ya existe")


def get_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("-headless")
    options.add_argument('--hide-scrollbars')
    options.add_argument('--window-size=2480,3508')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.add_argument('--log-level=3')

    driver = webdriver.Chrome(options=options)
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


Translations().generate_translations()

# Asumes a selenium service running in localhost at port 4444. This is required for exporting the PNGs
def run(data_file, output_path="infografias", entity_name=None, regenerate=False, selenium_host="127.0.0.1", selenium_port="4444"):
    entities_data = Parser().parse_infografias(data_file)
    nif_to_export = None
    if entity_name is not None:
        entity_name = find_best_match(entity_name, [entity["Nombre"] for entity in entities_data])
        nif_to_export = next((entity["NIF"] for entity in entities_data if entity["Nombre"] == entity_name))

    mode = re.search(r".*datos_(.*).csv", data_file).group(1)
    generar_infografias(output_path, mode, entities_data, entity_name, regenerate)
    copy_static_files(output_path)

    with keep.presenting() as k:
        exportar_infografias(output_path, nif_to_export, regenerate, selenium_host, selenium_port)


if __name__ == "__main__":
    entity_name, regenerate = get_args()
    for datos_infografias in custom_props["ARCHIVOS_INFOGRAFIAS"].split(', '):
        run(f'{custom_props["DIRECTORIO_INFOGRAFIAS"]}/{datos_infografias}', entity_name=entity_name, regenerate=regenerate)
