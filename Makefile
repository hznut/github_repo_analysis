api_venv:
	cd rest_api; test -d .venv || pipenv install --dev; pipenv update --dev; ls -al ./; cd -

local_db:
	echo 'Local DB started.'

local_api: api_venv local_db
	cd rest_api; . ./.venv/bin/activate && uvicorn main:app --reload --app-dir src; cd -

infra_venv:
	cd infrastructure; test -d .venv || pipenv install; cd -

build: api_venv
	cd rest_api; . ./.venv/bin/activate && docker build -t repo-analysis-rest-api . ; cd -

tests: build
	cd rest_api; . ./.venv/bin/activate && pytest --tb=short; cd -

run:
	echo $SHELL
	. ./run.sh && run_api && docker ps -a | grep repo-analysis

logs:
	. ./run.sh && api_logs

stop:
	echo $SHELL
	. ./run.sh && cleanup

