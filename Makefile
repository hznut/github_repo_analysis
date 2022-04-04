api_venv:
	cd rest_api; test -d .venv || pipenv install; cd -

local_db:
	echo 'Local DB started.'

local_api: api_venv local_db
	cd rest_api; source ./.venv/bin/activate && uvicorn main:app --reload

infra_venv:
	cd infrastructure; test -d .venv || pipenv install; cd -

run:
	. ./run.sh && run_api

stop:
	. ./run.sh && cleanup

