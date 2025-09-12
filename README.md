
# geninfografia

Generador de infografías para el Balance Social de la ESS.

## Requisitos
python >= 3.10

## Instrucciones

1. Clona el proyecto

```bash
  git clone https://github.com/Mercado-Social-de-Madrid/geninfografia
```

2. Accede al directorio del proyecto

```bash
  cd geninfografia
```

3. Modifica el fichero de configuración `config.yml` [(Saber más)](#configuración).

4. Prepara las hojas de datos [(Saber más)](#preparacion-de-hojas-de-datos).

5. Ejecuta el script
```bash
  python generar_infografias.py
```
## Preparación de hojas de datos

#### datos_autonomas.csv

#### datos_infografias.csv

#### datos_territorios.csv

## Configuración

### Ejemplo fichero config.yml:

```
YEAR: 2025

# MODO: entidad o autonoma
MODO: entidad

# TERRITORIOS DISPONIBLES: AND, ARA, AST, BAL, CAN, CAT, CYL, EUS, GAL, LRI, MAD, MUR, NAV, VAL
# DEJAR VACÍO PARA GENERAR TODOS LOS TERRITORIOS
TERRITORIOS: ARA, MUR, NAV

# IDIOMAS DISPONIBLES: CAS, CAT, EUS, GAL
# DEJAR VACÍO PARA GENERAR TODOS LOS IDIOMAS (SEGÚN TERRITORIO)
IDIOMAS: 

# Ubicación de pngquant
PNGQUANT_PATH: /usr/bin/pngquant

```


### Opciones disponibles

| Nombre        | Descripción | 
| ------------- | ----------- |
| YEAR          | Año que se mostrará en las infografías.        |
| MODO          | Para indicar si las infografías se van a generar usando el diseño para empresas o para personas autónomas. (Valores permitidos: `entidad` o `autonoma`) |
| TERRITORIOS   | Territorios que se van a generar. Indicar los territorios separados por comas. Por ejemplo:  `TERRITORIOS: ARA, MUR, NAV` generará las infografías para Aragón, Murcia y Navarra.       |
| IDIOMAS       | Idiomas en los que se van a generar las infografías, en base a lo que se especifique en la hoja de datos para cada territorio.      | 
| PNGQUANT_PATH | Ubicación de la librería para comprimir imágenes. Por defecto para Linux `/usr/bin/pngquant`      |  

