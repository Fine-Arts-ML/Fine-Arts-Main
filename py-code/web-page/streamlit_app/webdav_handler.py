from urllib import response
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
import streamlit as st



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
            <d:getcontenttype/>
        </d:prop>
    </d:propfind>"""
    )

    # Parse XML response
    root = ET.fromstring(response.text)
    ns = {'oc': 'http://owncloud.org/ns'}
    fileid = root.find('.//oc:fileid', ns).text if root.find('.//oc:fileid', ns) is not None else None
    id = root.find('.//oc:id', ns).text if root.find('.//oc:id', ns) is not None else None
    regex = r"(?<=d\:getcontenttype\>)(.*)(?=\<\/d\:getcontenttype\>)"
    mime = re.search(regex, str(response.text))[0]
    return id, fileid, mime


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
            id, fileid, mime = get_meta(client, full_entry_path, server_url)
            children[entry] = {"name": entry, "id": id, "fileid": fileid, "path": full_entry_path, "mime": mime}
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
            id, fileid, mime = get_meta(client, full_entry_path, server_url)
            children[entry] = {"name": entry, "id": id, "fileid": fileid, "path": full_entry_path, "mime": mime}
    return children




@st.cache_data()
def get_images(file_id, file_path):
    DB_HOST = os.getenv("DB_HOST")
    NC_ACC = os.getenv("NC_ACC")
    NC_PASS = os.getenv("NC_PASS")

    # Send a GET request to download the file
    response = requests.get(file_path, auth=HTTPBasicAuth(NC_ACC, NC_PASS), stream=True)
  
    try:
        if response.status_code == 200:
            file_in_memory = BytesIO()
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    file_in_memory.write(chunk)
            file_in_memory.seek(0) 
            #img = Image.open(file_in_memory)
            return file_id, file_in_memory
        elif response.status_code == 404:
            print(f"No preview available for file: {file_id} {file_path}")
            return file_id, None
        else:
            print(f"Failed to download file. Status code: {response.status_code}")
            print(response.text)
            return file_id, None
    except Exception as e:
        print(f"Error downloading file {file_id}: {e}")
        return file_id, None



def make_img_link(file_path, file_id):
    DB_HOST = os.getenv("DB_HOST")
    NC_ACC = os.getenv("NC_ACC")
    # Construct the full WebDAV URL for the file
    file_path = re.sub(r'/[^/]*$', '', file_path)
    nextcloud_url = f"http://{DB_HOST}:8080/apps/files/files/{file_id}?dir={file_path}&editing=false&openfile=true"
    
    return nextcloud_url
