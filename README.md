# Fine-Arts-Main
Main Repository 


## Postrges - Where to Find What Data
- File Locations are availible in Table `oc_filechache` in column `path`


## Cloud - Docker env setup
The Docker-Compose.yml is an all in one Setup file for this work enviroment.
It is important to setup an .env file for the envoirement credentials & settings.
<br>_See files in `docker-compose-setup`_

It includes a Nextcloud installation which is published via a cloudflare tunnel.
The Nextcloud Database is PSQL and can be accessed via ssh/5432.
Nextcloud is used as Source Database. <br> 
It will be extended via another Database to save porgress from developement and more importantly the classified data and other results.
