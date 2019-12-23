import os
from base64 import b64decode, b64encode
from flask import Flask, jsonify, request
from logging import getLogger



from hseling_api_judgment import boilerplate

from hseling_lib_judgment.process import process_data
from hseling_lib_judgment.query import query_data


app = Flask(__name__)
app.config['DEBUG'] = False
app.config['LOG_DIR'] = '/tmp/'
app.config.from_envvar('HSELING_API_JUDGMENT_SETTINGS')
app.config.update(
    CELERY_BROKER_URL=boilerplate.CELERY_BROKER_URL,
    CELERY_RESULT_BACKEND=boilerplate.CELERY_RESULT_BACKEND
)
celery = boilerplate.make_celery(app)

if not app.debug:
    import logging
    from logging.handlers import TimedRotatingFileHandler
    # https://docs.python.org/3.6/library/logging.handlers.html#timedrotatingfilehandler
    file_handler = TimedRotatingFileHandler(os.path.join(app.config['LOG_DIR'], 'hseling_api_judgment.log'), 'midnight')
    file_handler.setLevel(logging.WARNING)
    file_handler.setFormatter(logging.Formatter('<%(asctime)s> <%(levelname)s> %(message)s'))
    app.logger.addHandler(file_handler)

log = getLogger(__name__)


ALLOWED_EXTENSIONS = ['txt']


def do_process_task(file_ids_list):
    files_to_process = boilerplate.list_files(recursive=True,
                                              prefix=boilerplate.UPLOAD_PREFIX)
    if file_ids_list:
        files_to_process = [boilerplate.UPLOAD_PREFIX + file_id
                            for file_id in file_ids_list
                            if (boilerplate.UPLOAD_PREFIX + file_id)
                            in files_to_process]
    data_to_process = {file_id[len(boilerplate.UPLOAD_PREFIX):]:
                       boilerplate.get_file(file_id)
                       for file_id in files_to_process}
    processed_file_ids = list()
    for processed_file_id, contents in process_data(data_to_process):
        processed_file_ids.append(
            boilerplate.add_processed_file(
                processed_file_id,
                contents,
                extension='txt'
            ))
    return processed_file_ids

@celery.task
def process_task(file_ids_list=None):
    return do_process_task(file_ids_list)
@app.route('/healthz')
def healthz():
    app.logger.info('Health checked')
    return jsonify({"status": "ok", "message": "Application Judgment"})

@app.route('/upload', methods=['GET', 'POST'])
def upload_endpoint():
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({"error": boilerplate.ERROR_NO_FILE_PART})
        upload_file = request.files['file']
        if upload_file.filename == '':
            return jsonify({"error": boilerplate.ERROR_NO_SELECTED_FILE})
        if upload_file and boilerplate.allowed_file(
                upload_file.filename,
                allowed_extensions=ALLOWED_EXTENSIONS):
            return jsonify(boilerplate.save_file(upload_file))
    return boilerplate.get_upload_form()

@app.route('/files/<path:file_id>')
def get_file_endpoint(file_id):
    if file_id in boilerplate.list_files(recursive=True):
        return boilerplate.get_file(file_id)
    return jsonify({'error': boilerplate.ERROR_NO_SUCH_FILE})

@app.route('/files')
def list_files_endpoint():
    return jsonify({'file_ids': boilerplate.list_files(recursive=True)})

def do_process(file_ids):
    file_ids_list = file_ids and file_ids.split(",")
    task = process_task.delay(file_ids_list)
    return {"task_id": str(task)}

@app.route('/process')
@app.route("/process/<file_ids>")
def process_endpoint(file_ids=None):
    return jsonify(do_process(file_ids))


def do_query(file_id, query_type):
    if not query_type:
        return {"error": boilerplate.ERROR_NO_QUERY_TYPE_SPECIFIED}
    processed_file_id = boilerplate.PROCESSED_PREFIX + file_id
    if processed_file_id in boilerplate.list_files(recursive=True):
        return {
            "result": query_data({
                processed_file_id: boilerplate.get_file(processed_file_id)
            }, query_type=query_type)
        }
    return {"error": boilerplate.ERROR_NO_SUCH_FILE}

@app.route("/query/<path:file_id>")
def query_endpoint(file_id):
    query_type = request.args.get('type')
    return jsonify(do_query(file_id, query_type))

@app.route("/status/<task_id>")
def status_endpoint(task_id):
    return jsonify(boilerplate.get_task_status(task_id))

def do_test_mysql():
    conn = boilerplate.get_mysql_connection()
    cur = conn.cursor()
    cur.execute("SELECT table_name, column_name FROM INFORMATION_SCHEMA.COLUMNS")
    schema = dict()
    for table_name, column_name in cur.fetchall():
        schema.setdefault(table_name.decode('utf-8'), []).append(column_name)
    return {"schema": schema}

@app.route("/test_mysql")
def test_mysql_endpoint():
    return jsonify(do_test_mysql())

def get_endpoints(ctx):
    def endpoint(name, description, active=True):
        return {
            "name": name,
            "description": description,
            "active": active
        }

    all_endpoints = [
        endpoint("root", boilerplate.ENDPOINT_ROOT),
        endpoint("scrap", boilerplate.ENDPOINT_SCRAP,
                 not ctx["restricted_mode"]),
        endpoint("upload", boilerplate.ENDPOINT_UPLOAD),
        endpoint("process", boilerplate.ENDPOINT_PROCESS),
        endpoint("query", boilerplate.ENDPOINT_QUERY),
        endpoint("status", boilerplate.ENDPOINT_STATUS)
    ]

    return {ep["name"]: ep for ep in all_endpoints if ep}


@app.route("/")
def main_endpoint():
    ctx = {"restricted_mode": boilerplate.RESTRICTED_MODE}
    return jsonify({"endpoints": get_endpoints(ctx)})

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=80)


__all__ = [app, celery]
