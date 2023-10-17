import asyncio
import os
import sys

import sass
import jinja2
from pathvalidate import sanitize_filename
import pdfgen
from fuzzywuzzy import fuzz
from pyppeteer import launch

from utils.parser import Parser

total_tasks = 0
export_percent = 0

def compile_sass():
    os.makedirs('static/css', exist_ok=True)

    with open('static/sass/styles.scss', 'r') as scss:
        scss.read()

    sass.compile(dirname=('static/sass', 'static/css'))


def generar_infografias(entities_data, entity_name=None):
    print("\n======== Generando ficheros HTML de las infografías =============")
    output_path = "infografias/html"
    os.makedirs(output_path, exist_ok=True)

    if entity_name:
        entities_data = [entity for entity in entities_data if entity_name == entity["Nombre"]]

    total_entities = len(entities_data)
    for index, entity in enumerate(entities_data):
        print(f"\033[K[{index+1}/{total_entities}] Generando infografia para la entidad {entity['Nombre']}...", end="\r")
        template_loader = jinja2.FileSystemLoader(searchpath="template")
        template_env = jinja2.Environment(loader=template_loader)
        template_file = "main.html"
        template = template_env.get_template(template_file)
        output_text = template.render(**entity)

        filename = sanitize_filename(entity["Nombre"])
        html_path = f'{output_path}/{filename}.html'
        html_file = open(html_path, 'w', encoding="utf-8")
        html_file.write(output_text)
        html_file.close()
        print(f"\033[K[{index+1}/{total_entities}] Infografía para la entidad [{entity['Nombre']}] generada.", end="\r")


def exportar_infografias(entity_name):
    print("\n\n======== Exportando infografías =============")
    loop = asyncio.get_event_loop()
    html2img_task = loop.create_task(html2img(entity_name))
    html2pdf_task = loop.create_task(html2pdf(entity_name))
    loop.run_until_complete(asyncio.gather(html2img_task, html2pdf_task))


async def html2pdf(entity_name):
    global total_tasks, export_percent
    html_path = "infografias/html"
    output_path = "infografias/pdf"
    os.makedirs(output_path, exist_ok=True)

    options = {
        'scale': 1.0,
        'format': 'A4',
        'encoding': "UTF-8",
        'custom-header': [
            ('Accept-Encoding', 'gzip')
        ],

        'pageRanges': '1',
    }

    files_list = os.listdir(html_path)
    total_tasks += len(files_list)

    if entity_name:
        files_list = [filename for filename in files_list if sanitize_filename(entity_name) == filename.split('.')[0]]

    for index, filename in enumerate(files_list):
        input_file = f"{html_path}/{filename}"
        pdf_path = f"{output_path}/{filename.split('.')[0]}.pdf"

        print(f"\033[K[{round(export_percent)}%] Exportando infografía en formato PDF [{pdf_path}]...", end='\r')
        await pdfgen.from_file(input_file, pdf_path, options=options)
        print(f"\033[K[{round(export_percent)}%] Infografía exportada a PDF [{pdf_path}]", end='\r')
        export_percent += 100 / total_tasks


async def html2img(entity_name, format="jpg"):
    global total_tasks, export_percent
    html_path = "infografias/html"
    output_path = f"infografias/{format}"

    os.makedirs(output_path, exist_ok=True)
    browser = await launch({"headless": True})
    page = await browser.newPage()
    await page.setViewport(viewport={"width": 2480, "height": 3508})

    options = {
        "fullPage": True,
        "quality": 90
    }

    files_list = os.listdir(html_path)
    total_tasks += len(files_list)

    if entity_name:
        files_list = [filename for filename in files_list if sanitize_filename(entity_name) == filename.split('.')[0]]

    for index, filename in enumerate(files_list):
        input_file = f"{html_path}/{filename}"
        img_path = f"{output_path}/{filename.split('.')[0]}.{format}"
        options["path"] = img_path

        print(f"\033[K[{round(export_percent)}%] Exportando infografia en formato {format.upper()} [{img_path}]...", end='\r')
        await page.goto(f"file://{os.path.abspath(input_file)}")
        await page.screenshot(options)
        print(f"\033[K[{round(export_percent)}%] Infografía exportada a {format.upper()} [{img_path}]", end='\r')
        export_percent += 100 / total_tasks

    await browser.close()


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
    entity_name = get_entity_name_from_args()
    generar_infografias(entities_data, entity_name)
    exportar_infografias(entity_name)


