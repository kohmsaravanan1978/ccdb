# CCDB


## Dev System

Copy the `docker-compose.override.yml.example` to `docker-compose.override.yml`.

Copy the django.env.example to django.env, and insert your API keys. Keep ``TEST_MODE=1`` – everything will work as
usual, but invoice delivery will be **turned off**, so no emails or letters will be sent.

### Dev System Container bauen
```
docker-compose build
docker-compose up -d
```

### Dev System initialisieren
```
docker-compose exec django bash
root@73155df6a499:/poetry# poetry install --with dev --with test
root@73155df6a499:/poetry# poetry run /code/manage.py migrate
root@73155df6a499:/poetry# poetry run /code/manage.py create_dev_users
# Compile translations
root@73155df6a499:/poetry# source .venv/bin/activate
root@73155df6a499:/poetry# cd /code
root@73155df6a499:/code# python3 manage.py compilemessages
```

Goto: http://localhost:8106/ (local login)
and login with: testing/LjERtTXIOkBG996h

For admin access, run ``createsuperuser`` instead of ``create_dev_users``, and log in at 
http://localhost:8106/admin

Next, continue to restore an included db dump, and then to import its data into the current data model:

### Run updates

After pulling from git, run these commands, then restart your containers:

```
docker-compose exec django bash
root@73155df6a499:/poetry# poetry run /code/manage.py migrate
```

### Restore dump

Answer all password prompts with `ccdb`.

```
$ docker-compose stop
$ docker-compose up -d postgres
< postgres should listen on host port 15432>
$ dropdb -h localhost -U ccdb -p 15432 ccdb
$ createdb -h localhost -U ccdb -p 15432 ccdb
$ pg_restore -h localhost -U ccdb -p 15432 -d ccdb 20220404_gwdb.dump  # for a dump file
$ PGPASSWORD=ccdb psql -h localhost -U ccdb -p 15432 < 20220404_gwdb.sql  # for a SQL file
$ docker-compose up -d
$ docker-compose exec django bash
root@73155df6a499:/poetry# poetry run /code/manage.py migrate
```

Check if data is there

```
$ docker-compose exec django bash
root@13b435712619:/poetry# poetry run /code/manage.py shell_plus
...
In [1]: GwCbsRechnungen.objects.all().count()
Out[1]: 44666
```


### Initial data import

After loading the dump for the first time, import all the historical data into the new schema, and collect customer
data:

```
$ docker-compose exec django bash
root@13b435712619:/poetry# poetry run /code/manage.py import_cbs
root@13b435712619:/poetry# poetry run /code/manage.py pull_customer_data [--customer number]
```

To push/sync all customers to Easybill, run 

```
root@13b435712619:/poetry# poetry run /code/manage.py push_customer_data [--customer number]  [--force-all]
```

### Make a dump

If you ever need to export all data, run these commands:

```
$ docker-compose exec postres bash
root@13b435712619:/poetry# sudo -u postgres pg_dump --user=ccdb ccdb > /persistence/do-backup/20220404_gwdb.dump
```

## Running commands

These commands are ready to be run with poetry, as ``poetry run /code/manage.py <command>``:

- ``import_cbs``, ``--delete`` to delete and re-import, ``--only-contracts`` / ``--only-accounts`` / ``--only-invoices``
  to limit imoprt types.
- ``run_invoicing``, ``--dry-run`` to only print new objects
- ``run_extensions``, ``--dry-run`` to only print new valid_till dates
