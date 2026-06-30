FROM registry.cdso.army.mil/cdso/containers/approved-base/alpine:3.23
LABEL image.authors="ADOC DMC"
WORKDIR /home/heather
COPY heather/ heather/
COPY pyproject.toml pyproject.toml
RUN apk add --no-cache --update python3 uv &&\
    uv venv &&\
    uv pip install . &&\
    adduser -D heather -h /home/heather/ &&\
    chown -R heather:heather /home/heather/
USER heather
CMD [ "python", "heather/main.py" ]
