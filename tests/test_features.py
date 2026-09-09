import ast
import json
from pathlib import Path
import pytest
from pydantic import ValidationError

from fusion_native_mcp.bridge import script_result, script_wrapper, COMPLETION_MARKER, Bridge
from fusion_native_mcp.features import EntityQuery, FeatureSpec, AssemblySpec, ExportSpec
from fusion_native_mcp.existing_features import ComponentParameterEdit
from fusion_native_mcp.cam_features import DrawingSpec, NCProgramSpec


def test_long_script_transport_preserves_source():
    source = '#' + 'x' * 20000 + '\ndef run(c):\n    print("héllo")\n'
    wrapped = script_wrapper(source, 'doc')
    tree = ast.parse(wrapped)
    assignment = next(n for n in ast.walk(tree) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id=='source' for t in n.targets))
    assert ast.literal_eval(assignment.value) == source
    assert max(map(len,wrapped.splitlines())) < 4096


def test_missing_completion_is_not_success():
    result={'content':[{'type':'text','text':json.dumps({'success':True,'message':''})}]}
    with pytest.raises(RuntimeError,match='completion marker'):
        script_result(result,require_completion=True)


@pytest.mark.parametrize('escaped',[False,True])
def test_stdout_completion_decoding(escaped):
    stdout=json.dumps({'name':'Part "A"','path':'C:\\test','value':12})+'\n'+COMPLETION_MARKER+'\n'
    if escaped:
        stdout=json.dumps(stdout)[1:-1]
    result=script_result({'content':[{'type':'text','text':json.dumps({'success':True,'message':stdout})}]},True)
    assert result['data']['name']=='Part "A"'
    assert result['data']['value']==12
    assert COMPLETION_MARKER not in result['stdout']


@pytest.mark.parametrize('query',[{'kind':'faces'},{'kind':'bodies','radius_mm':5},{'kind':'bodies','limit':501}])
def test_invalid_entity_queries(query):
    with pytest.raises(ValidationError):
        EntityQuery(**query)


@pytest.mark.parametrize('args',[{'kind':'sweep','entities':['x']},{'kind':'combine','entities':['a','b']},{'kind':'loft','entities':['x']}])
def test_feature_missing_inputs(args):
    with pytest.raises(ValidationError):
        FeatureSpec(**args)


def test_external_export_paths_and_formats(tmp_path):
    with pytest.raises(ValidationError):
        ExportSpec(format='step',path='relative.step')
    with pytest.raises(ValidationError):
        ExportSpec(format='step',path=str(tmp_path/'wrong.stl'))
    with pytest.raises(ValidationError):
        ExportSpec(format='dxf',path=str(tmp_path/'sketch.dxf'))


def test_joint_limits_and_required_origin():
    with pytest.raises(ValidationError):
        AssemblySpec(action='joint',one='a',two='b',motion='slider')
    with pytest.raises(ValidationError):
        AssemblySpec(action='joint',one='a',two='b',minimum=1)


def test_component_edits_require_current_fingerprint():
    with pytest.raises(ValidationError):
        ComponentParameterEdit(path='Group:1+Part:1',expected_component='token',expected_fingerprint='bad',expressions={'d1':'10 mm'})
    spec=ComponentParameterEdit(path='Group:1+Part:1',expected_component='token',expected_fingerprint='a'*64,expressions={'d1':'10 mm'})
    assert spec.allow_shared_definition_edit is False


def test_drawing_sheet_standard_and_nc_filename(tmp_path):
    with pytest.raises(ValidationError):
        DrawingSpec(standard='ASMEDrawingStandardType')
    with pytest.raises(ValidationError):
        NCProgramSpec(operation_ids=['1'],post_url='library://post',output_folder=str(tmp_path),filename='../escape')


def test_runtime_sources_compile():
    root=Path(__file__).parents[1]/'src/fusion_native_mcp'
    for name in ['runtime.py','runtime_cam.py','runtime_existing.py']:
        compile((root/name).read_text(),name,'exec')
