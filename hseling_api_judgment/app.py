import io
import os
import sqlite3
import tempfile

import pandas as pd
from flask import Flask, jsonify, abort, request, send_file

from lib.metadata_extractor import get_metadict
from lib.classifier import get_parts

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

db = sqlite3.connect('sudact.sqlite', check_same_thread=False)

def get_law_data(db_id: int):
    sql = '''select id, name, url from uk_sections
    where level=3 and id=?'''

    cursor = db.cursor()
    cursor.execute(sql, (db_id,))
    res = cursor.fetchone()
    cursor.close()
    return res


def parse_document(doc_id):
    sql = '''select id, header, url, data
    from documents
    where id=?'''
    cursor = db.cursor()
    cursor.execute(sql, (doc_id,))
    data = cursor.fetchone()
    cursor.close()
    if data is None:
        abort(404)
    db_id, header, url, html = data
    try:
        parsed = get_parts(html)
    except ValueError:
        parsed = "NON_STANDARD_DOCUMENT"
    return {
        'db_id': db_id,
        'header': header,
        'url': url,
        'metadata': get_metadict(html),
        'parsed': parsed,
        # 'raw_html': html
    }


@app.route('/laws/', methods=['GET'])
def list_laws():
    sql = '''select id, name, url
    from uk_sections
    where level=3'''

    cursor = db.cursor()
    cursor.execute(sql)
    data = [{
        'db_id': db_id,
        'name': name,
        'url': url
    } for db_id, name, url in cursor]
    cursor.close()
    return jsonify(data)


@app.route('/regions/', methods=['GET'])
def list_regions():
    cursor = db.cursor()
    cursor.execute('select distinct(region) from metadata order by 1')
    regions = [item for item, in cursor]
    cursor.close()
    return jsonify(regions)


def get_params():

    page_size = int(request.args.get('page_size', 50))
    page_num = int(request.args.get('page_num', 1))

    params = {
        'limit': page_size,
        'offset': (page_num - 1) * page_size,
        'year': request.args.get('year', '%'),
        'region': request.args.get('region', '%'),
        'article': f'%{request.args.get("article", "")}%',
        'judge': f'%{request.args.get("judge", "")}%'
    }

    return page_size, page_num, params


def query_sql(params, batches=True):

    sql = '''select {selector}
        from documents d
        join metadata m on m.document_id=d.id
        where substr(m.date, 1, 4) like :year
         and m.region like :region
         and m.article like :article
         and judge like :judge
        order by d.id
        '''

    selector = ''' d.id id, d.header header, d.url url, m.date date, m.number number, m.court court, m.region region,
        m.judge judge, m.article article, m.accused accused, m.fabula fabula, m.witness witness, m.prove prove, 
        m.meditation meditation
        '''

    cursor = db.cursor()

    cursor.execute(sql.format(selector='count(*) as count'), params)
    size, = cursor.fetchone()

    if batches:
        sql += ' limit :limit offset :offset'

    cursor.execute(sql.format(selector=selector), params)
    column_names = [desc[0] for desc in cursor.description]
    # cursor.close()
    return size, [dict(zip(column_names, item)) for item in cursor.fetchall()]


@app.route('/documents/', methods=['GET'])
def get_documents():
    page_size, page_num, params = get_params()

    size, query = query_sql(params)

    res = {
        'page_num': page_num,
        'pages': (size-1) // page_size + 1,
        'documents': query
    }

    return jsonify(res)


@app.route('/laws/<int:law_id>', methods=['GET'])
def get_law(law_id: int):
    res = get_law_data(law_id)
    if res is None:
        abort(404)
    law_id, name, url = res
    return jsonify({'db_id': law_id, 'name': name, 'url': url})


@app.route('/documents/<int:doc_id>')
def parse_doc(doc_id):
    return jsonify(parse_document(doc_id))


@app.route('/documents/download')
def download_files():
    params = get_params()[-1]

    columns = ['id', 'Заголовок', 'Ссылка', 'Дата', 'Номер дела', 'Суд', 'Регион',
               'Судья', 'Статья', 'Обвиняемый', 'Фабула', 'Показания свидетелей',
               'Описание доказательств', 'Размышления судьи']
    res = pd.DataFrame(query_sql(params, batches=False)[1])
    res.columns = columns
    res = res.drop('id', axis=1)
    tmp_dir = tempfile.mkdtemp()
    base_name = 'судебная_практика.xlsx'
    filename = os.path.join(tmp_dir, base_name)
    res.to_excel(filename, index=False)
    return send_file(filename, attachment_filename=base_name, as_attachment=True, cache_timeout=-1)


@app.route('/documents/<int:doc_id>/download')
def download_file(doc_id):
    filename, file_data = create_file(doc_id)
    return send_file(file_data, attachment_filename=filename, as_attachment=True)


def create_file(doc_id):
    result = parse_document(doc_id)
    metadata = result['metadata']
    parsed = result['parsed']
    table = pd.DataFrame(index=['Информация о документе', '', 'Фабула', 'Показания свидетелей',
                                'Доказательства', 'Размышления судьи'],
                         columns=['Номер', 'Дата', 'Статьи',
                                  'Суд', 'Регион', 'Судья',
                                  'Подсудимый(ые)', 'url'])

    row = [result['header'], metadata['date'], metadata['article'], metadata['court'],
           metadata['region'], metadata['judge'], ' '.join(metadata['accused']), result['url']]

    table['Номер'][''] = 'Части документа:'
    table['Номер']['Фабула':'Размышления судьи'] = ['\n'.join(parsed.get(item, '')) for item in
                                                    ['fabula', 'witness', 'prove', 'meditation']]
    table.iloc[0] = row

    court = metadata['court'].split()[0] + '_'
    no = result['header'].split('от')[0].strip()
    no = no.replace('№', '').replace(r'/', '_').replace(' ', '_')

    name = court + no
    name = name.lower() + '.xlsx'

    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    table.to_excel(writer, sheet_name='Sheet1')
    writer.save()
    writer.close()
    output.seek(0)

    return name, output


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True, threaded=False)


if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=80)


