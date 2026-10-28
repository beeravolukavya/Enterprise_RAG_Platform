import json, os, time
from core import s3,table,embed,extract,chunks,ensure_index,search_request,BUCKET

def handler(event,context):
    failures=[]
    for record in event['Records']:
        try:
            event_data=json.loads(record['body'])
            for item in event_data.get('Records',[]):
                if item.get('eventName','').startswith('ObjectCreated:'):
                    from urllib.parse import unquote_plus
                    key=unquote_plus(item['s3']['object']['key'])
                    process(key)
        except Exception as e:
            print('Ingestion failure',str(e));failures.append({'itemIdentifier':record['messageId']})
    return {'batchItemFailures':failures}

def process(key):
    parts=key.split('/',3)
    if len(parts)!=4 or parts[0]!='uploads':raise ValueError('Invalid key')
    _,user,doc_id,filename=parts
    tbl=table();pk=f'TENANT#{user}';sk=f'DOC#{doc_id}'
    item=tbl.get_item(Key={'pk':pk,'sk':sk}).get('Item')
    if not item or item['object_key']!=key:raise ValueError('Document metadata mismatch')
    if item.get('status')=='READY':return
    try:
        obj=s3.get_object(Bucket=BUCKET,Key=key)
        if obj['ContentLength']>10*1024*1024:raise ValueError('File exceeds 10MB')
        content=extract(obj['Body'].read(),filename)
        pieces=chunks(content)
        if not pieces:raise ValueError('No extractable text; scanned PDFs require OCR')
        ensure_index()
        for i,piece in enumerate(pieces):
            doc={'tenant':user,'doc_id':doc_id,'chunk_id':f'{doc_id}-{i}','filename':filename,'text':piece,'vector':embed(piece)}
            search_request('PUT',f'/documents/_doc/{doc_id}-{i}',doc)
        tbl.update_item(Key={'pk':pk,'sk':sk},UpdateExpression='SET #s=:s,chunk_count=:n',ExpressionAttributeNames={'#s':'status'},ExpressionAttributeValues={':s':'READY',':n':len(pieces)})
    except Exception:
        tbl.update_item(Key={'pk':pk,'sk':sk},UpdateExpression='SET #s=:s',ExpressionAttributeNames={'#s':'status'},ExpressionAttributeValues={':s':'FAILED'})
        raise
