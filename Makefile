api_venv:
	cd rest_api; test -d .venv || pipenv install --dev; pipenv update --dev; cd -

local_db:
	echo 'Local DB started.'

local_api: api_venv local_db
	cd rest_api; . ./.venv/bin/activate && uvicorn main:app --reload --app-dir src; cd -

infra_venv:
	cd infrastructure; test -d .venv || pipenv install; cd -

tests: api_venv
	cd rest_api; . ./.venv/bin/activate && docker build -t repo-analysis-rest-api . && pytest --tb=short; cd -

run:
	. ./run.sh && run_api

logs:
	. ./run.sh && api_logs

stop:
	. ./run.sh && cleanup

