import spacy
from rest_framework.response import Response
from rest_framework.decorators import api_view, schema

nlp = spacy.load('de_core_news_sm')


@api_view(['GET', 'POST'])
@schema(None)
def textparser(request):
    """
    get:
    Send any text as value of a *longtext* paramter

    post:
    Processes any german text which is sent as value of a *longtext* param

    """
    enriched = {}
    if request.method == 'POST':
        longtext = request.POST.get('longtext')
    else:
        longtext = request.GET.get('longtext')
    if longtext:
        doc = nlp("{}".format(longtext))
        sents = [x for x in doc.sents]
        result = []
        for x in sents:
            chunk = {}
            chunk['sent'] = "{}".format(x)
            chunk['tokens'] = []
            for y in x:
                parts = {}
                parts['text'] = y.text
                parts['lemma'] = y.lemma_
                parts['pos'] = y.pos_
                parts['tag'] = y.tag_
                parts['dep'] = y.dep_
                parts['shape'] = y.shape_
                parts['is_alpha'] = y.is_alpha
                chunk['tokens'].append(parts)
            result.append(chunk)
        enriched['result'] = result
        return Response(enriched)
    return Response(
        {
            "Param-Name": "longtext",
            "Param-Value": "any text you want",
            "POST": "form-data or x-www-form-urlencoded"
        }
    )


@api_view()
def lemma(request):
    """
    get:
    Expects a `token` parameter (e.g. ?token=flog) which will be POS-tagged.

    """
    token = request.GET.get('token')
    enriched = {}
    if token:
        doc = nlp("{}".format(token))[0]
        enriched['token'] = token
        enriched['lemma'] = doc.lemma_
        enriched['pos'] = doc.pos_
        enriched['tag'] = doc.tag_
        return Response(enriched)
    else:
        return Response({'token': None})