"""Opt-in acceptance checks for additional feature creation kinds in a new document."""
import json, sys, uuid
from pathlib import Path
from fusion_native_mcp.bridge import Bridge
from fusion_native_mcp.features import FeatureService, SketchSpec, FeatureSpec, AssemblySpec, EntityQuery, HoleSpec

out=Path(sys.argv[1]).resolve(); out.mkdir(parents=True,exist_ok=True)
b=Bridge(out/'state'); s=FeatureService(b)
active=b.inspect()['data']['document']; before=active['id'] if active else '__NO_DOCUMENT__'
new=b.execute('import adsk.core,json\ndef run(c):\n d=adsk.core.Application.get().documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)\n d.name="MCP Feature Kinds"\n print(json.dumps({"id":d.creationId}))',False,before,str(uuid.uuid4()))
assert new['state']=='succeeded',new
doc=new['result']['data']['id']; report={'document_id':doc}

def call(action,spec,read=False):
    value=s.call(action,spec,doc,None if read else str(uuid.uuid4()),read)
    if not read:
        if value['state']!='succeeded':
            report['failure']=value
            (out/'kinds-report.json').write_text(json.dumps(report,indent=2))
            raise RuntimeError(value)
        value=value['result']
    return value['data']

def component(name):
    return call('assembly',AssemblySpec(action='create_component',name=name))['component']['token']

def sketch(c,shape='rectangle',**args):
    return call('sketch',SketchSpec(shape=shape,component=c,width='20 mm',height='15 mm',**args))

def feature(c,kind,tokens,**args):
    return call('feature',FeatureSpec(kind=kind,component=c,entities=tokens,**args))

def query(kind,scope):
    return call('entities',EntityQuery(kind=kind,scope=scope),True)['items']

def solid(name,shape='rectangle'):
    c=component(name); sk=sketch(c,shape)
    feature(c,'extrude',[sk['profile_references'][0]['token']],distance='10 mm')
    return c,query('bodies',c)[0]

for kind in ('chamfer','shell','revolve','loft','combine','rectangular_pattern','circular_pattern','holes','sweep'):
    if kind in ('chamfer','shell','rectangular_pattern','circular_pattern','combine'):
        c,body=solid(kind)
        if kind=='chamfer':
            result=feature(c,kind,[e['token'] for e in query('edges',body['token'])],distance='1 mm')
        elif kind=='shell':
            faces=query('faces',body['token']); top=next(f for f in faces if abs(f['bounds_mm']['min'][2]-10)<1e-6)
            result=feature(c,kind,[top['token']],distance='1 mm')
        elif kind=='combine':
            circle=sketch(c,'circle'); feature(c,'extrude',[circle['profile_references'][0]['token']],distance='10 mm')
            bodies=query('bodies',c)
            result=feature(c,kind,[v['token'] for v in bodies],operation='cut',keep_tools=True)
        else:
            result=feature(c,kind,[body['token']],quantity=3,distance='30 mm')
    elif kind=='revolve':
        c=component(kind); sk=sketch(c)
        result=feature(c,kind,[sk['profile_references'][0]['token']],axis='y')
    elif kind=='loft':
        c=component(kind); a=sketch(c,'circle'); z=sketch(c,'circle',offset='30 mm')
        result=feature(c,kind,[a['profile_references'][0]['token'],z['profile_references'][0]['token']])
    elif kind=='holes':
        c,body=solid(kind,'circle'); top=sketch(c,'circle',offset='10 mm')
        points=query('sketch_points',top['token'])
        result=call('holes',HoleSpec(component=c,points=[points[0]['token']],diameter='4 mm',depth='5 mm'))
    else:
        c=component(kind); sk=sketch(c,'circle',plane='yz')
        code=f'''import adsk.core,adsk.fusion,json
def run(context):
 d=adsk.fusion.Design.cast(adsk.core.Application.get().activeProduct)
 c=d.findEntityByToken({c!r})[0]
 s=c.sketches.add(c.xYConstructionPlane)
 line=s.sketchCurves.sketchLines.addByTwoPoints(adsk.core.Point3D.create(0,0,0),adsk.core.Point3D.create(4,0,0))
 print(json.dumps({{'token':line.entityToken}}))
'''
        raw=b.execute(code,False,doc,str(uuid.uuid4())); assert raw['state']=='succeeded',raw
        result=feature(c,kind,[sk['profile_references'][0]['token']],path_token=raw['result']['data']['token'])
    assert result.get('health',0)==0,result
    report[kind]=result
    (out/'kinds-report.json').write_text(json.dumps(report,indent=2))
    print(kind,'passed',flush=True)
print('Additional feature kinds passed')
