import datetime
import shutil
import zipfile
from os import listdir, makedirs, path

import lxml.etree as et
import requests
from celery import chord, current_task, shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth.models import User

from .custom_parsers import JsonToDocParser, process_tokenlist
from .tei import TeiReader


@shared_task(time_limit=1000)
def process_file(file, pipeline, file_type, fld_out):
    if file_type.lower() == 'tei' and pipeline[0].lower() == 'acdh-tokenizer':
        with open(file, 'r', encoding='utf-8') as file_str:
            headers = {
                'Content-type': 'application/xml;charset=UTF-8',
                'accept': 'application/xml'
            }
            url = 'https://xtx.acdh.oeaw.ac.at/exist/restxq/xtx/tokenize/default'
            res = requests.post(
                url, headers=headers, data=file_str.read().encode('utf8', ))
    if file_type.lower() == 'tei':
        res_tei = TeiReader(res.text)
        res = res_tei.create_tokenlist()
    if pipeline[1].lower() == "treetagger-tagger":
        url = "https://linguistictagging.eos.arz.oeaw.ac.at"
        headers = {'accept': 'application/json'}
        payload = {
            'tokenArray': res,
            'language': 'german',
            "outputproperties": {
                "lemma": True,
                "no-unknown": False
            }
        }
        res = requests.post(url, headers=headers, json=payload)
        if res.status_code != 200:
            print(res.text)
            res = res.text
        else:
            res = res.json()['tokenArray']
    spacy_pipeline = [
        x.split('-', )[1] for x in pipeline if x.startswith('spacy', )
    ]
    if spacy_pipeline:
        headers = {
            'content-type': "application/json+acdhlang",
            'accept': "application/json+acdhlang"
        }
        payload = {
            'tokenArray': res,
            'language': 'german',
            'options': {
                'outputproperties': {
                    'pipeline': spacy_pipeline
                }
            }
        }
        res = requests.post(
            "https://spacyapp.eos.arz.oeaw.ac.at/query/jsonparser-api/",
            headers=headers,
            json=payload)
        if res.status_code != 200:
            print(res.text)
            res = res.text
        else:
            res = res.json()
            res1 = [x['tokens'] for x in res['result']]
            res2 = [item for sublist in res1 for item in sublist]
    if file_type == 'tei':
        res = res_tei.process_tokenlist(res2)
        with open(path.join(fld_out, file.split('/')[-1]), 'wb') as outfile:
            outfile.write(et.tostring(res, encoding='utf8', pretty_print=True))
        return {
            'success': True,
            'path': path.join(
                fld_out,
                file.split('/', )[-1],
            )
        }


@shared_task(time_limit=500)
def pipe_zip_files(
        results,
        fld_out,
        dwld_dir,
        fn,
        user_id=None
):  # TODO: use the results for zip creation
    zipf = zipfile.ZipFile(
        '{}_output.zip'.format(fn, ),
        'w',
        zipfile.ZIP_DEFLATED,
    )
    for filename in listdir(fld_out):
        zipf.write(path.join(fld_out, filename), filename)
    zipf.close()
    shutil.copy('{}_output.zip'.format(fn, ), '{}{}_output.zip'.format(
        dwld_dir,
        fn.split('/', )[1],
    ))
    path = '{}{}_output.zip'.format(dwld_dir, fn.split('/', )[1])
    user_1 = False
    if user_id is not None:
        user_1 = User.objects.get(pk=user_id)
        if user_1.email is None:
            user_1 = False
    if user_1:
        message = "Your job has finished. Please download the file under: {}".format(path)
        send_mail(
            'Subject here',
            message,
            'acdh-tech@oeaw.ac.at',
            [user_1.email,],
            fail_silently=True,
        )
    return {
        'success': True,
        'path': path
    }


@shared_task(time_limit=1800)
def pipe_process_files(pipeline, file, fn, options, user, zip_type, file_type, user_id=None):
    dwld_dir = getattr(settings, "SPACYAPP_DOWNLOAD_DIR", 'download/')
    if zip_type is not None:
        makedirs('{}_folder'.format(fn))
        makedirs('{}_output'.format(fn))
        zip_ref = zipfile.ZipFile(file, 'r')
        fld_proc = '{}_folder'.format(fn)
        fld_out = '{}_output'.format(fn)
        zip_ref.extractall(fld_proc)
        zip_ref.close()
        lst_dir = listdir(fld_proc)
        res_group = chord(
            process_file.s(
                path.join(fld_proc, fn), pipeline, file_type, fld_out)
            for fn in lst_dir)(pipe_zip_files.s(fld_out, dwld_dir, fn))
        return {
            'success': True,
            'id_docs': res_group.id,
            'path': '{}{}_output.zip'.format(
                dwld_dir,
                fn.split('/', )[1],
            )
        }
