"""Exercise existing nested shared definitions through actual MCP stdio tools.

Creates its own fixture document. No cloud save or user's geometry is touched.
"""
import asyncio
import json
import os
from pathlib import Path
import sys
import uuid
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    root = Path(__file__).resolve().parents[1]
    out = Path(sys.argv[1]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, FUSION_MCP_STATE_DIR=str(out / "state"))
    report = {}
    async with stdio_client(StdioServerParameters(command=sys.executable, args=[str(root / 'run.py')], env=env)) as (read, write):
        async with ClientSession(read, write) as client:
            await client.initialize()
            async def call(name, args):
                value = await client.call_tool(name, args)
                assert not value.isError, value
                return json.loads(value.content[0].text)
            async def edit(name, spec):
                value = await call(name, dict(document_id=doc, operation_id=str(uuid.uuid4()), spec=spec))
                assert value['state'] == 'succeeded', value
                return value['result']['data']
            before = await call('fusion_inspect', {})
            original = before['data']['document']['id'] if before['data']['document'] else '__NO_DOCUMENT__'
            fixture = '''import adsk.core, json
def run(c):
    d=adsk.core.Application.get().documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    d.name='MCP Existing Nested Assembly Test'
    print(json.dumps({'id':d.creationId}))
'''
            created = await call('fusion_execute_python', dict(script=fixture, expected_document_id=original, operation_id=str(uuid.uuid4())))
            assert created['state']=='succeeded', created
            doc = created['result']['data']['id']
            group = await edit('fusion_assembly', dict(action='create_component', name='Module', translation_mm=[20,0,0]))
            group_token = group['component']['token']
            child = await edit('fusion_assembly', dict(action='create_component', name='Pin', component=group_token, translation_mm=[0,0,5]))
            child_token = child['component']['token']
            sk = await edit('fusion_create_sketch', dict(shape='circle', component=child_token, width='12 mm', name='Pin Profile'))
            await edit('fusion_create_feature', dict(kind='extrude', entities=[sk['profile_references'][0]['token']], component=child_token, distance='20 mm', name='Pin Length'))
            await edit('fusion_assembly', dict(action='insert_component', source=group_token, translation_mm=[100,0,0]))
            independent = await edit('fusion_assembly', dict(action='create_component', name='Unrelated'))
            other_token=independent['component']['token']
            sk2=await edit('fusion_create_sketch',dict(shape='rectangle',component=other_token,width='30 mm',height='10 mm'))
            await edit('fusion_create_feature',dict(kind='extrude',entities=[sk2['profile_references'][0]['token']],component=other_token,distance='5 mm'))
            tree=(await call('fusion_assembly_tree',dict(document_id=doc)))['data']
            pins=[o for o in tree['items'] if o['component']['name']=='Pin']
            assert len(pins)==2 and all('+' in o['path'] for o in pins), tree
            path=pins[0]['path']
            async def context(path):
                return (await call('fusion_component_context',dict(document_id=doc,occurrence_path=path)))['data']
            target=await context(path)
            other_path=next(o['path'] for o in tree['items'] if o['component']['name']=='Unrelated')
            other_before=await context(other_path)
            param=next(v['name'] for v in target['model_parameters'] if v['role']=='AlongDistance')
            request=dict(path=path,expected_component=target['component']['token'],expected_fingerprint=target['definition_fingerprint'],expressions={param:'25 mm'})
            async def rejected(request, expected_error):
                result=await call('fusion_edit_component_parameters',dict(document_id=doc,operation_id=str(uuid.uuid4()),spec=request))
                assert result['state']=='uncertain' and expected_error in result['result']['error'],result
                same=await context(path)
                assert same['definition_fingerprint']==(await context(path))['definition_fingerprint']
                return result,same
            result,same=await rejected(request,'SHARED_DEFINITION')
            assert same['definition_fingerprint']==target['definition_fingerprint']
            await call('fusion_acknowledge_operation',dict(operation_id=result['id'],resolution='Expected shared-definition precondition failure returned synchronously. Re-read target fingerprint is unchanged.'))
            request['allow_shared_definition_edit']=True
            changed=await edit('fusion_edit_component_parameters',request)
            after=await context(path)
            second=await context(pins[1]['path'])
            other_after=await context(other_path)
            assert len(changed['affected_occurrence_paths'])==2
            assert after['definition_fingerprint']==second['definition_fingerprint']
            assert other_before['definition_fingerprint']==other_after['definition_fingerprint']
            assert abs(after['native_bodies'][0]['bounds_mm']['max'][2]-25)<1e-6
            result,same=await rejected(request,'STALE_COMPONENT_STATE')
            assert same['definition_fingerprint']==after['definition_fingerprint']
            await call('fusion_acknowledge_operation',dict(operation_id=result['id'],resolution='Expected stale-state rejection returned synchronously. Target fingerprint equals independently verified post-edit state.'))
            foreign=other_after['model_parameters'][0]['name']
            bad=dict(request,expected_fingerprint=after['definition_fingerprint'],expressions={foreign:'50 mm'})
            result,same=await rejected(bad,'PARAMETER_OUTSIDE_TARGET')
            assert same['definition_fingerprint']==after['definition_fingerprint']
            await call('fusion_acknowledge_operation',dict(operation_id=result['id'],resolution='Expected foreign-parameter rejection returned synchronously. Target fingerprint and unrelated component unchanged.'))
            report=dict(document_id=doc,tools=len((await client.list_tools()).tools),tree=tree,target_before=target,target_after=after,
                shared_instance_verified=True,stale_state_rejected=True,foreign_parameter_rejected=True,
                unrelated_component_unchanged=True,second_instance=second)
    (out/'existing-report.json').write_text(json.dumps(report,indent=2))
    print('Nested existing-assembly MCP acceptance passed')


if __name__=='__main__':
    asyncio.run(main())
