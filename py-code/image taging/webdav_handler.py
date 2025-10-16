from webdav3.client import Client
from dotenv import load_dotenv
load_dotenv()
import os
import pandas as pd
import xml.etree.ElementTree as ET
import regex as re
from tqdm import tqdm
import json
import requests
from requests.auth import HTTPBasicAuth
from io import BytesIO
from IPython.display import display, Image
from PIL import Image as PILImage
import gc
from sqlalchemy import create_engine, MetaData, Table, select, insert
from sqlalchemy.exc import SQLAlchemyError



def webdav_login(server_url, username, password):
    try:
        # connect 2 webdav server
        client = Client({
            'webdav_hostname': server_url,
            'webdav_login': username,
            'webdav_password': password
        })

       #check connection
        if client.check():
            return client
        else:
            print("Wrong login data.")
            return None
    except Exception as e:
        print(f"Exception: {e}")
        return None
    

def get_meta(client, path, server_url):
    url=f"{server_url}{path}"
    # PROPFIND Anfrage senden
    response = client.session.request(
        method="PROPFIND",
        url=url,
        headers={'Depth': '1'},
        data="""<?xml version="1.0" encoding="utf-8"?>
    <d:propfind xmlns:d="DAV:" xmlns:oc="http://owncloud.org/ns">
        <d:prop>
            <oc:id/>
            <oc:fileid/>
            <oc:tags/>
            <d:getcontenttype/>
        </d:prop>
    </d:propfind>"""
    )

    # Parse XML response
    root = ET.fromstring(response.text)
    ns = {'oc': 'http://owncloud.org/ns'}
    fileid = root.find('.//oc:fileid', ns).text if root.find('.//oc:fileid', ns) is not None else None
    id = root.find('.//oc:id', ns).text if root.find('.//oc:id', ns) is not None else None
    tags = root.find('.//oc:tags', ns).text if root.find('.//oc:tags', ns) is not None else None
    #mime = root.find('.//d:getcontenttype').text if root.find('.//d:getcontenttype') is not None else 'unknown'
    regex = r"(?<=d\:getcontenttype\>)(.*)(?=\<\/d\:getcontenttype\>)"
    mime = re.search(regex, str(response.text))[0]
    return id, fileid, tags, mime


def folder_to_dict(path, client):
    entries = client.list(path)[1:]  # skip the listing of the directory itself
    children = {}
    for entry in entries:
        full_entry_path = path + entry
        if entry.endswith("/"):
            # recurse into subfolder
            children[entry] = folder_to_dict(full_entry_path, client)
        else:
            # file
            children[entry] = entry
    return children

def folder_to_dict_w_meta_tqdm(path, client, server_url):
    entries = client.list(path)[1:]  # skip the listing of the directory itself
    children = {}
    for entry in tqdm(entries):
        full_entry_path = path + entry
        if entry.endswith("/"):
            # recurse into subfolder
            children[entry] = folder_to_dict_w_meta(full_entry_path, client, server_url)
        else:
            # file: call file_id and store the response
            id, fileid, tags, mime = get_meta(client, full_entry_path, server_url)
            children[entry] = {"name": entry, "id": id, "fileid": fileid, "tags": tags, "path": full_entry_path, "mime": mime}
    return children


def folder_to_dict_w_meta(path, client, server_url):
    entries = client.list(path)[1:]  # skip the listing of the directory itself
    children = {}
    for entry in entries:
        full_entry_path = path + entry
        if entry.endswith("/"):
            # recurse into subfolder
            children[entry] = folder_to_dict_w_meta(full_entry_path, client, server_url)
        else:
            # file: call file_id and store the response
            id, fileid, tags, mime = get_meta(client, full_entry_path, server_url)
            children[entry] = {"name": entry, "id": id, "fileid": fileid, "tags": tags, "path": full_entry_path, "mime": mime}
    return children

def get_images(file_id,file_path):
    DB_HOST = os.getenv("DB_HOST")
    NC_ACC = os.getenv("NC_ACC")
    NC_PASS = os.getenv("NC_PASS")

    server_url = f'''http://{DB_HOST}:8080/remote.php/dav/files/{NC_ACC}'''
    preview_url = f'''http://{DB_HOST}:8080/core/preview?fileId={file_id}&x=1080&y=1080'''
    username = NC_ACC
    password = NC_PASS

    # Construct the full URL
    file_url = f"{server_url}{file_path}"

    # Send a GET request to download the file
    response = requests.get(preview_url, auth=HTTPBasicAuth(username, password), stream=True)
 
    # Check if the request was successful
    if response.status_code == 200:
        # Save the file content in memory using BytesIO
        file_in_memory = BytesIO()
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                file_in_memory.write(chunk)
        file_in_memory.seek(0)  # Move the pointer to the start of the BytesIO object
        size_in_bytes = len(file_in_memory.getvalue())
        size_in_mb = size_in_bytes / (1024 * 1024)  # Convert bytes to megabytes
        #print(f"Image size: {size_in_mb:.2f} MB")

        # Open the image using Pillow (PIL)
        img = PILImage.open(file_in_memory)
        #w, h = img.size
        #print('width:', w, 'height:', h)
        img = img.resize((256, 256))
        #display(img)
    elif response.status_code == 404:
        #print("No preview available for this file.")
        try:
            response = requests.get(file_url, auth=HTTPBasicAuth(username, password), stream=True)
            file_in_memory = BytesIO()
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    file_in_memory.write(chunk)
            file_in_memory.seek(0)  # Move the pointer to the start of the BytesIO object
            size_in_bytes = len(file_in_memory.getvalue())
            size_in_mb = size_in_bytes / (1024 * 1024)  # Convert bytes to megabytes
            #print(f"File size: {size_in_mb:.2f} MB")
            source_img = PILImage.open(file_in_memory)
            img = source_img.resize((1080, 1080))
            img_display = source_img.resize((256, 256))
            #display(img_display)
        except Exception as e:
            print(f"Failed to download file. Exception: {e}")
    else:
        print(f"Failed to download file. Status code: {response.status_code}")
        print(response.text)
    try:
        import gc
        del file_in_memory
        gc.collect()
    except:
        pass
    return img