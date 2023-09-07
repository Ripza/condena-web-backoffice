import json
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
from dotenv import load_dotenv
import base64
import json

load_dotenv()

def update_json_with_sheet_data(sheet_data, json_data):
    # Crear un diccionario para un acceso más fácil usando el nombre como clave
    name_to_data = {}
    for row in sheet_data[1:]:
        data = {"Respuesta": row[3] if len(row) > 3 else None,
                "Frase": row[4] if len(row) > 4 else None,
                "Link Frase": row[5] if len(row) > 5 else None}
        name_to_data[row[0]] = data

    # print(name_to_data)
    
    # Actualizar el archivo .json con los datos de la hoja
    for entry in json_data:
        if entry["name"] in name_to_data:
            if name_to_data[entry["name"]]["Respuesta"]:
                entry["condena"] = name_to_data[entry["name"]]["Respuesta"]
            if name_to_data[entry["name"]]["Frase"]:
                entry["condena-quote"] = name_to_data[entry["name"]]["Frase"]
            if name_to_data[entry["name"]]["Link Frase"]:
                entry["condena-fuente"] = name_to_data[entry["name"]]["Link Frase"]
    
    return json_data


def get_github_file_content(repo, branch, filepath, token):
    """Obtiene el contenido del archivo en GitHub."""
    url = f'https://api.github.com/repos/{repo}/contents/{filepath}?ref={branch}'
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json',
    }
    response = requests.get(url, headers=headers)
    file_info = response.json()
    if 'content' in file_info:
        return base64.b64decode(file_info['content']).decode('utf-8'), file_info['sha']
    return None, None

def update_github_file(repo, branch, filepath, content, sha, token):
    """Actualiza el archivo en GitHub."""
    url = f'https://api.github.com/repos/{repo}/contents/{filepath}'
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json',
    }
    data = {
        'message': 'Actualizar archivo automático',
        'content': base64.b64encode(content.encode('utf-8')).decode('utf-8'),
        'sha': sha,
        'branch': branch,
    }
    response = requests.put(url, headers=headers, json=data)
    return response.json()


# Configuración de Google Sheets
# CREDENTIALS_FILE = 'credentials.json'

# Autoriza usando las credenciales de la API de Google Sheets
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

credentials_env = json.loads(base64.b64decode(os.environ['SHEETS_SERVICE_ACCOUNT']).decode('utf-8'))
credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_env, scope)
client = gspread.authorize(credentials)

# Leer los datos de la hoja "parlamentarios"
sheet = client.open_by_key(os.environ['SPREADSHEET_ID']).worksheet(os.environ['SHEET_NAME'])
sheet_data = sheet.get(os.environ['RANGE_NAME'])

print("Obteniendo archivo desde github")

# Obtener el contenido del archivo en GitHub
github_content, sha = get_github_file_content(os.environ['REPO_PATH'], os.environ['REPO_BRANCH'], os.environ['REPO_FILE_PATH'], os.environ['REPO_GITHUB_TOKEN'])

json_data = json.loads(str(github_content))

print("Revisando cambios en sheets")

# Actualizar el archivo .json con los datos de la hoja
updated_json_data = update_json_with_sheet_data(sheet_data, json_data)

local_content = json.dumps(updated_json_data, indent=4)

# Si los contenidos son diferentes, subir el archivo
if local_content != github_content:
    result = update_github_file(os.environ['REPO_PATH'], os.environ['REPO_BRANCH'], os.environ['REPO_FILE_PATH'], local_content, sha, os.environ['REPO_GITHUB_TOKEN'])
    print("Archivo actualizado en GitHub.")
else:
    print("El archivo no ha cambiado, no se subió.")