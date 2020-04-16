"""
данный модуль разбивает документы судакта на части и возвращает json с ключами:
- fabula (фактические обстоятельства дела)
- witness (показания свидетелей)
- prove (доказательная база)
- meditation (рассуждения судьи)
"""

import re
from pathlib import Path
from bs4 import BeautifulSoup
from rusenttokenize import ru_sent_tokenize
import pickle

MODELS_DIR = Path(__file__).parent / 'models'

def to_bound_pattern(patterns):
    """формируем паттерны для разбиения документа на начальную, основную и финальную части"""
    return re.compile(r'(?:{}):?'.format('|'.join(r'\s*'.join(s) for s in patterns)), re.IGNORECASE)


def divide_into_parts(text):
    """делим документ на части по паттернам"""
    begin_pattern = to_bound_pattern(["УСТАНОВИЛ"])
    end_pattern = to_bound_pattern(["ПРИГОВОРИЛ", "ПОСТАНОВИЛ", "РЕШИЛ"])
    begin, main_part = re.split(begin_pattern, text, 1)
    main_part, end = re.split(end_pattern, main_part, 1)
    return begin, main_part, end


def split_sentences(html):
    """делим на предложения основную часть приговора"""
    soup = BeautifulSoup(html, 'html.parser')
    for script in soup(["script", "style"]):
        script.decompose()
    text = soup.text
    begin, main_part, end = divide_into_parts(text)

    return ru_sent_tokenize(main_part)


def predict_parts(text, clf_filename=MODELS_DIR/'finalized_parts_clf.sav'):
    """предсказываем метки частей для каждого предложения из основной части документа"""
    clf = pickle.load(open(clf_filename, 'rb'))
    return clf.predict(text)


def concatenate_parts(lines, tags):
    """собираем предложения с общими метками в части"""
    current_tag = None
    groups, accum = [], []
    for i, (line, tag) in enumerate(zip(lines, tags)):
        if tag != current_tag and (len(line) > 30 or len(tags) <= (i+1) or tags[i+1] != current_tag):
            if accum:
                groups.append([current_tag, ' '.join(accum)])
                accum = []
            current_tag = tag
        accum.append(line)
    groups.append([current_tag, ' '.join(accum)])
    parts = {}
    for x in groups:
        if x[0] not in parts:
            parts[x[0]] = [x[1]]
        else:
            parts[x[0]].append(x[1])
    return parts


def get_parts(html):
    """разбиваем основную часть документа на части, возвращаем json {'название части': [список строк]}"""
    sents = split_sentences(html)
    predictions = predict_parts(sents)
    return concatenate_parts(sents, predictions)
