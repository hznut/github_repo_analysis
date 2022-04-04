# syntax=docker/dockerfile:1
FROM jupyter/minimal-notebook
COPY requirements.txt ./requirements.txt
COPY repo_analysis.ipynb ./repo_analysis.ipynb

RUN pip install -r requirements.txt
EXPOSE 8888