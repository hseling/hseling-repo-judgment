import os
from base64 import b64decode, b64encode

from django.shortcuts import render
from django.http import HttpResponseRedirect, JsonResponse
from django import forms

import requests


HSE_API_ROOT = os.environ.get("HSELING_API_ROOT", "http://hse-api-web/")

PROJECT_TITLE = "Judgment"


def web_index(request):
    return render(request, 'index.html',
                  context={"project_title": PROJECT_TITLE})


def web_main(request):
    return render(request, 'main.html',
                  context={"project_title": PROJECT_TITLE,
                           "status": request.GET.get('status')})


def web_status(request):
    task_id = request.GET.get('task_id')
    if task_id:

        url = HSE_API_ROOT + "status/" + task_id
        content = requests.get(url)
        result = content.json()
        if result.get('status') == 'SUCCESS':
            content = requests.get(HSE_API_ROOT + 'files/' + result.get('result', [""])[0])
            result['raw_base64'] = b64encode(content.content).decode('utf-8')

        return JsonResponse(result)
    return JsonResponse({"error": "No task id"})


def handle_uploaded_file(f):

    files = {'file': f}
    url = HSE_API_ROOT + "upload"
    content = requests.post(url, files=files)
    file_id = content.json().get("file_id")

    if file_id:
        file_id = file_id[7:]
        url = HSE_API_ROOT + "process/" + file_id
        content = requests.get(url)

    else:
        raise Exception(content.json())

    return content.json().get('task_id')


class UploadFileForm(forms.Form):
    file = forms.FileField()


def web_upload_file(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():            
            task_id = handle_uploaded_file(request.FILES['file'])
            return HttpResponseRedirect('main?task_id=' + task_id)
    else:
        form = UploadFileForm()
    return render(request, 'main.html', {"project_title": PROJECT_TITLE,
                                         'form': form})
