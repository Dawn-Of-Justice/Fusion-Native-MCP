"""Export/reopen the known nested-assembly fixture, then edit its existing component.

Closes ONLY the test fixture after its F3D export, not any user document.
"""
import asyncio,json,os,sys,uuid
from pathlib import Path
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    root=Path(__file__).resolve().parents[1]
    previous=json.loads(Path(sys.argv[1]).read_text())
    out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
    async with stdio_client(StdioServerParameters(command=sys.executable,args=[str(root/'run.py')],env=dict(os.environ,FUSION_MCP_STATE_DIR=str(out/'state')))) as (r,w):
        async with ClientSession(r,w) as client:
            await client.initialize()
            async def call(name,args):
                res=await client.call_tool(name,args);assert not res.isError,res
                return json.loads(res.content[0].text)
            async def mutation(name,args):
                res=await call(name,dict(args,operation_id=str(uuid.uuid4())))
                assert res['state']=='succeeded',res
                return res['result']['data']
            current=(await call('fusion_inspect',{}))['data']['document']['id']
            target=previous['document_id']
            await mutation('fusion_activate_document',dict(current_document_id=current,target_document_id=target))
            archive=str(out/'nested-assembly.f3d')
            await mutation('fusion_export',dict(document_id=target,spec=dict(format='f3d',path=archive)))
            close='import adsk.core,json\ndef run(c):\n d=adsk.core.Application.get().activeDocument\n if d.name!="MCP Existing Nested Assembly Test":\n  raise ValueError("Not the disposable test fixture")\n print(json.dumps({"closed":d.close(False)}))'
            await mutation('fusion_execute_python',dict(expected_document_id=target,script=close))
            current=(await call('fusion_inspect',{}))['data']['document']
            reopened=await mutation('fusion_open_archive',dict(path=archive,expected_document_id=current['id'] if current else '__NO_DOCUMENT__'))
            doc=reopened['id']
            tree=(await call('fusion_assembly_tree',dict(document_id=doc)))['data']
            path=next(x['path'] for x in tree['items'] if x['component']['name']=='Pin')
            before=(await call('fusion_component_context',dict(document_id=doc,occurrence_path=path)))['data']
            parameter=next(x['name'] for x in before['model_parameters'] if x['role']=='AlongDistance')
            edit=await mutation('fusion_edit_component_parameters',dict(document_id=doc,spec=dict(path=path,
                expected_component=before['component']['token'],expected_fingerprint=before['definition_fingerprint'],
                allow_shared_definition_edit=True,expressions={parameter:'30 mm'})))
            after=(await call('fusion_component_context',dict(document_id=doc,occurrence_path=path)))['data']
            assert abs(after['native_bodies'][0]['bounds_mm']['max'][2]-30)<1e-6
            assert len(edit['affected_occurrence_paths'])==2
            report=dict(passed=True,reopened=reopened,archive=archive,affected_paths=edit['affected_occurrence_paths'],before=before['definition'],after=after['definition'])
    (out/'reopen-report.json').write_text(json.dumps(report,indent=2))
    print('Archived existing nested assembly reopened and edited successfully')

asyncio.run(main())
