# Fine-Arts-Webdav
## Image taging
Webdav Repository
- This Solution has clean(er) API connection for file download, no more bruteforce
- File and metadata download succesfull
    - files wont be written to disk anymore and are kept in ram
    - files metadata is downloaded in a dictionary and saved in a json for testing purposes
        - for some reason the propfind ```<oc:tags>``` still returns no values
        - therefore exiting tags have to be managed via direct psql access
            - same goes for tag upload & mapping, can't use webDAV. currently works only with psql
    - all folder info and file metadata download is done in +-6 minutes (1500 files)
    - since most files now do have a preview, it might be worth getting those, instead of the big source files <br>
        - like this ``` GET: https://cloud.yourserver.org/core/preview?fileId=11750924&x=250&y=250 ``` 
    - json/dict format example: 
    ```json
                "AI_art/": {
                "bearbeitet/": {
                    "1265.jpg": {
                        "name": "1265.jpg",
                        "id": "00019515s6w8qwy7q",
                        "fileid": "195",
                        "tags": null,
                        "path": "/path/to/file/1265.jpg"
                    },
                    "etc/":"12.jpg": {
                        "name": "12.jpg",
                        "id": "000115s6w8qwy7q",
                        "fileid": "95",
                        "tags": null,
                        "path": "/path/to/file/12.jpg"}
                    }}
    ```
 - this info also goes for the same folder in /ipynb-test-bench/image taging


## Postrges - Where to Find What Data
- File Locations are availible in Table `oc_filechache` in column `path`
- File tags are availible in Table `oc_systemtag`
- File tag mappings are availible in Table `oc_systemtag_object_mapping`

## Cloud - Docker env setup
The Docker-Compose.yml is an all in one Setup file for this work enviroment.
It is important to setup an .env file for the envoirement credentials & settings.
<br>_See files in `docker-compose-setup`_
<br>Install from folder with `docker compose up -d`

It includes a Nextcloud installation which is published via a cloudflare tunnel.
The Nextcloud Database is PSQL and can be accessed via ssh/5432.
Nextcloud is used as Source Database. <br> 
It will be extended via another Database to save porgress from developement and more importantly the classified data and other results.
