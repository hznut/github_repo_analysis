api_venv:
	pushd rest_api; test -d .venv || pipenv install --dev; pipenv update --dev; popd

local_db:
	echo 'Local DB started.'

local_api: api_venv local_db
	pushd rest_api;source ./.venv/bin/activate && uvicorn main:app --reload --app-dir src; popd

infra_venv:
	cd infrastructure; test -d .venv || pipenv install; cd -

tests: api_venv
	pushd rest_api;source ./.venv/bin/activate && pytest; popd

run:
	. ./run.sh && run_api

stop:
	. ./run.sh && cleanup

