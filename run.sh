#!/bin/bash -e

function cleanup {
  docker compose down
  # rm repo_analysis.log
}

function print_urls {
  api_port=$(docker container ls --format "table {{.Ports}}" -a -f name=^/repo-analysis-rest-api$ | grep -v 'PORTS' | cut -d ':' -f 2 | cut -d '-' -f 1)
  db_admin_port=$(docker container ls --format "table {{.Ports}}" -a -f name=^/repo-analysis-db-admin-console$ | grep -v 'PORTS' | cut -d ':' -f 2 | cut -d '-' -f 1)
  nb_port=$(docker container ls --format "table {{.Ports}}" -a -f name=^/repo-analysis-notebook$ | grep -v 'PORTS' | cut -d ':' -f 2 | cut -d '-' -f 1)
  echo "DB Admin Console: http://localhost:$db_admin_port/?server=db&username=root&db=repo_analysis"
  echo "REST API Swagger: http://localhost:$api_port/repo-analysis/api/docs"
  echo "Jupyter Notebook: http://127.0.0.1:$nb_port/lab?token=notoken"
}

function check_services {
  if [[ "$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8080/)" == "200" ]]; then
    echo 'DB admin console started';
  fi
  if [[ "$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:80/repo-analysis/api/status)" == "200" ]]; then
    echo 'REST API started';
  fi
  if [[ "$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8888/login)" == "200" ]]; then
    echo 'Jupyter Notebook started';
  fi
}

function run_api {
  docker compose --env-file ./local.env up -d --build --wait --quiet-pull
  check_services
  print_urls
  docker compose logs -f
}
