FROM hseling/hseling-api-base:python3.6-alpine3.7 as build

LABEL maintainer="Vera Davydova <info@linghub.ru>"

RUN mkdir /dependencies
COPY ./hseling_api_judgment/requirements.txt /dependencies/requirements.txt
COPY ./hseling_api_judgment/setup.py /dependencies/setup.py

RUN pip install -r /dependencies/requirements.txt

FROM hseling/hseling-api-base:python3.6-alpine3.7 as production

COPY --from=build /usr/local/lib/python3.6/site-packages /usr/local/lib/python3.6/site-packages
COPY --from=build /usr/lib/python3.6/site-packages /usr/lib/python3.6/site-packages

COPY --from=build /dependencies /dependencies

COPY ./hseling_lib_judgment /dependencies/hseling_lib_judgment
RUN pip install /dependencies/hseling_lib_judgment

COPY ./hseling_api_judgment/hseling_api_judgment /app/hseling_api_judgment
COPY ./hseling_api_judgment/main.py /app/main.py

ENV HSELING_API_JUDGMENT_SETTINGS="/app/hseling_api_judgment/default_settings.py"

HEALTHCHECK CMD curl --fail http://localhost/healthz || exit 1
