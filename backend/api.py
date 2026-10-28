import json, os, re, uuid, time
from boto3.dynamodb.conditions import Key
from core import s3,table,embed,search_request,response,tenant_user,call_llm,BUCKET

ALLOWED={'.pdf':'application/pdf','.docx':'application/vnd.openxmlformats-officedocument.wordprocessingml.document','.txt':'text/plain','.md':'text/markdown'}
def handler(event,context):
    try:
        user=tenant_user(event)
        method=event.get('requestContext',{}).get('http',{}).get('method','GET')
        path=event.get('rawPath','/')
        body=json.loads(event.get('body') or '{}')
        if method=='GET' and path=='/health':return response(200,{'status':'ok'})
        if method=='POST' and path=='/documents/upload-url':
            filename=body.get('filename','')
            suffix=os.path.splitext(filename.lower())[1]
            if suffix not in ALLOWED:return response(400,{'error':'Unsupported file type'})
            if len(filename)>180 or not re.fullmatch(r'[\w .()\-]+',filename):return response(400,{'error':'Invalid filename'})
            doc_id=str(uuid.uuid4()); key=f'uploads/{user}/{doc_id}/{filename}'
            table().put_item(Item={'pk':f'TENANT#{user}','sk':f'DOC#{doc_id}','doc_id':doc_id,'filename':filename,'status':'PENDING','created_at':int(time.time()),'object_key':key})
            url=s3.generate_presigned_url('put_object',Params={'Bucket':BUCKET,'Key':key,'ContentType':ALLOWED[suffix]},ExpiresIn=600)
            return response(200,{'doc_id':doc_id,'upload_url':url,'content_type':ALLOWED[suffix]})
        if method=='GET' and path=='/documents':
            result=table().query(KeyConditionExpression=Key('pk').eq(f'TENANT#{user}') & Key('sk').begins_with('DOC#'),Limit=100)
            return response(200,{'documents':[{k:v for k,v in item.items() if k not in ('pk','sk','object_key')} for item in result.get('Items',[])]})
        if method=='POST' and path=='/query':
            q=str(body.get('question','')).strip()
            if not 3<=len(q)<=1500:return response(400,{'error':'Question must be 3-1500 characters'})
            vector=embed(q)
            result=search_request('POST','/documents/_search',{'size':5,'query':{'bool':{'filter':[{'term':{'tenant':user}}],'must':[{'knn':{'vector':{'vector':vector,'k':8}}}]}}})
            hits=[{'text':h['_source']['text'],'filename':h['_source']['filename'],'doc_id':h['_source']['doc_id'],'score':h['_score']} for h in result.get('hits',{}).get('hits',[])]
            if not hits:return response(200,{'answer':'No indexed documents matched your question.','sources':[]})
            return response(200,{'answer':call_llm(q,hits),'sources':hits})
        return response(404,{'error':'Not found'})
    except PermissionError:return response(401,{'error':'Unauthorized'})
    except Exception as e:
        print('API failure:',type(e).__name__,str(e))
        return response(500,{'error':'Internal service error; inspect CloudWatch logs'})
