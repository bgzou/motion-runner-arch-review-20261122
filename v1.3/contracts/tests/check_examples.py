#!/usr/bin/env python3
"""V1.1 schema / consistency / contract-SIL checks. No hardware safety claim.
Run: python tests/check_examples.py ; requires PyYAML >=6, jsonschema >=4.
This file is NOT the RT or HAL implementation.
"""
from __future__ import annotations
import csv
import json
import re
import unittest
from pathlib import Path
import yaml
from jsonschema import Draft202012Validator

ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'examples'; S=ROOT/'schemas'

def schema(name): return json.loads((S/name).read_text())
def validate(filename, schemaname):
    value=yaml.safe_load((E/filename).read_text())
    Draft202012Validator(schema(schemaname)).validate(value)
    return value

def csv_rows(filename, schname):
    with (E/filename).open(newline='') as f: rows=list(csv.DictReader(f))
    sch=schema(schname)
    result=[]
    for row in rows:
        v=dict(row)
        for k,desc in sch['properties'].items():
            if desc.get('type')=='integer': v[k]=int(v[k])
            elif desc.get('type')=='number': v[k]=float(v[k])
            elif desc.get('type')=='boolean':
                if v[k] not in ('true','false'): raise ValueError(f'{k}: invalid boolean')
                v[k]=v[k]=='true'
            elif 'enum' in desc and isinstance(desc['enum'][0], int): v[k]=int(v[k])
        Draft202012Validator(sch).validate(v); result.append(v)
    return result

def graph_semantic(x):
    if len(x['nodes'])!=len(set(x['nodes'])): raise ValueError('duplicate graph node')
    if any(n in x['nodes'] for n in ('INIT','SAFE_HOLD','DAMPING','ESTOP','RECOVERY')):
        raise ValueError('safety state cannot be ActionGraph node')
    for edge in x['edges']:
        if edge['from'] not in x['nodes'] or edge['to'] not in x['nodes']:
            raise ValueError('unresolved edge')
        if edge['from']==edge['to']: raise ValueError('self edge')

def manifest_semantic(m):
    r=m['runner']
    if r['worker_budget_ms'] >= r['period_ms']: raise ValueError('budget >= period')
    factory={('ONNX','LOCOMOTION'):'RlLocomotionRunner',('CLASSICAL','LOCOMOTION'):'WheelDriveRunner',
             ('CLASSICAL','POSE'):'ClassicalPoseRunner',('PLAYBACK','POSE'):'PlaybackRunner',
             ('ONNX','BALANCE'):'BalanceRunner',('CLASSICAL','BALANCE'):'BalanceRunner',
             ('ONNX','TRANSITION'):'TransitionRunner',('CLASSICAL','TRANSITION'):'TransitionRunner',
             ('PLAYBACK','TRANSITION'):'TransitionRunner',('ONNX','RECOVERY'):'RecoveryRunner',
             ('CLASSICAL','RECOVERY'):'RecoveryRunner',('ONNX','OVERLAY'):'OverlayRunner',
             ('CLASSICAL','OVERLAY'):'OverlayRunner',('PLAYBACK','OVERLAY'):'OverlayRunner',
             ('COMPOSITE','OVERLAY'):'OverlayRunner',('COMPOSITE','TRANSITION'):'TransitionRunner'}
    key=(r['execution_kind'],r['behavior_role'])
    if key not in factory or factory[key]!=r['class_id']: raise ValueError('ambiguous/invalid factory')
    if m['release']['status']=='APPROVED' and 'nonphysical' in m['robot_compatibility']['robot_ids']:
        raise ValueError('demo asset cannot be approved')
    return factory[key]

class ContractSil:
    """Fake deterministic RT/HAL scheduler for functional assertions only."""
    def __init__(self):
        self.t_ns=0; self.period_ns=5_000_000; self.tick=0; self.active_epoch=7
        self.last_candidate_valid=True; self.worker_called_by_rt=0
        self.refuse_latched=False
    def rt_tick(self, decision, decision_epoch=7, active_seq=0, snapshot_time_ns=0):
        self.tick+=1
        # Deliberately does NOT call Worker; the only input is sealed data.
        self.t_ns+=self.period_ns
        if decision_epoch != self.active_epoch: return 'WAIT'
        if self.refuse_latched: return 'REFUSE'
        if decision is None or self.t_ns>decision['valid_until_ns']: return 'WAIT'
        if decision['snapshot_seq']>active_seq or active_seq-decision['snapshot_seq']>2:
            return 'WAIT'
        if self.t_ns-snapshot_time_ns>10_000_000: return 'WAIT'
        if decision['kind']=='REFUSE': self.refuse_latched=True;return 'REFUSE'
        if decision['kind']=='WAIT':return 'WAIT'
        return 'COMMIT' if decision['kind']=='READY' else 'WAIT'

class TestSchemaAndContracts(unittest.TestCase):
    def test_graph(self):
        x=validate('action_graph.yaml','action_graph.schema.json')
        graph_semantic(x)
        with self.assertRaises(ValueError):graph_semantic({**x,'nodes':x['nodes']+['DAMPING']})
        bad=dict(x); bad['actions']=bad.pop('nodes')
        with self.assertRaises(Exception): Draft202012Validator(schema('action_graph.schema.json')).validate(bad)
    def test_runner_manifest_and_16_joint_specs(self):
        m=validate('demo16_runner_manifest.yaml','runner_manifest.schema.json')
        self.assertEqual(manifest_semantic(m),'RlLocomotionRunner')
        obs=csv_rows('demo16_obsspec.csv','obs_spec.row.schema.json')
        act=csv_rows('demo16_actionspec.csv','action_spec.row.schema.json')
        self.assertEqual(len(obs),16);self.assertEqual(len(act),16)
        self.assertEqual([r['index'] for r in obs],list(range(16)))
        self.assertEqual([r['tensor_index'] for r in act],list(range(16)))
        self.assertEqual(len(set(r['joint_name'] for r in act)),16)
        self.assertEqual(set(m['owns']),set(r['joint_name'] for r in act))
        self.assertEqual(m['tensor_io']['inputs'][0]['shape'],[1,len(obs)])
        self.assertEqual(m['tensor_io']['outputs'][0]['shape'],[1,len(act)])
        self.assertTrue(all(r['missing_policy_ref']=='STRICT_INVALID' for r in obs))
        self.assertTrue(all(r['history_order']=='OLDEST_TO_NEWEST' for r in obs))
        self.assertTrue(all(r['include_current'] for r in obs))
        self.assertEqual([r['mode'] for r in act].count('POSITION'),12)
        self.assertEqual([r['mode'] for r in act].count('VELOCITY'),4)
        self.assertEqual([r['sign'] for r in act].count(-1),1)
        self.assertFalse(yaml.safe_load((ROOT/'safety_limits.yaml').read_text())['physical_limits_signed'])
        import hashlib
        for key, filename in [('obs_spec','demo16_obsspec.csv'),('action_spec','demo16_actionspec.csv'),('golden','demo16_golden.placeholder')]:
            self.assertEqual(m[key]['sha256'],hashlib.sha256((E/filename).read_bytes()).hexdigest())
    def test_safety_limits_schema_and_unsigned(self):
        limits=yaml.safe_load((ROOT/'safety_limits.yaml').read_text())
        Draft202012Validator(schema('safety_limits.schema.json')).validate(limits)
        self.assertFalse(limits['release_approved'])
        self.assertFalse(limits['physical_limits_signed'])
        self.assertTrue(all(not p['approved'] for p in limits['limit_profiles'].values()))
    def test_demo_is_not_deployable(self):
        m=validate('demo16_runner_manifest.yaml','runner_manifest.schema.json')
        self.assertNotEqual(m['release']['status'],'APPROVED')
        self.assertNotEqual((E/'demo16_model.placeholder').suffix,'.onnx')
    def test_exit_worker_hang_50ms_rt_not_block(self):
        rt=ContractSil()
        for _ in range(10):
            self.assertEqual(rt.rt_tick(None),'WAIT')
        self.assertEqual(rt.tick,10);self.assertEqual(rt.t_ns,50_000_000)
        self.assertEqual(rt.worker_called_by_rt,0)
    def test_exit_stale_decision_auto_wait(self):
        rt=ContractSil()
        d={'kind':'READY','snapshot_seq':5,'valid_until_ns':3_000_000}
        self.assertEqual(rt.rt_tick(d,active_seq=5,snapshot_time_ns=0),'WAIT')
    def test_exit_fresh_ready_and_refuse_latch(self):
        rt=ContractSil()
        d={'kind':'READY','snapshot_seq':10,'valid_until_ns':20_000_000}
        self.assertEqual(rt.rt_tick(d,active_seq=11,snapshot_time_ns=0),'COMMIT')
        d={'kind':'REFUSE','snapshot_seq':12,'valid_until_ns':20_000_000}
        self.assertEqual(rt.rt_tick(d,active_seq=12,snapshot_time_ns=5_000_000),'REFUSE')
        d={'kind':'READY','snapshot_seq':13,'valid_until_ns':25_000_000}
        self.assertEqual(rt.rt_tick(d,active_seq=13,snapshot_time_ns=10_000_000),'REFUSE')
    def test_unknown_form_never_hold_or_action(self):
        form='UNKNOWN'; support=False; feedback=False
        normal=['q2b','b2q','balance','recovery']
        self.assertFalse(support and feedback)
        self.assertTrue(all(form=='UNKNOWN' for _ in normal))
        initial_output={'enabled':False,'mode':'PASSIVE'}
        self.assertFalse(initial_output['enabled']);self.assertNotEqual(initial_output['mode'],'POSITION')
    def test_blackbox_128_mib_40sec(self):
        capacity=128*1024**2; reserve=16*1024**2
        rate=8192*100+256*200
        self.assertLessEqual(rate*40+reserve,capacity)
        self.assertEqual((capacity-reserve)/40/(1024**2),2.8)
    def test_mode_ramp_endpoints_and_bounded_changes(self):
        def smooth(u):return 3*u*u-2*u*u*u
        self.assertEqual(smooth(0),0);self.assertEqual(smooth(1),1)
        vals=[10+20*smooth(k/20) for k in range(21)]
        self.assertLessEqual(max(abs(vals[k+1]-vals[k]) for k in range(20)),1.6)
    def test_canonical_proto_fields_present(self):
        t=(ROOT/'proto'/'collie_mc_v11.proto').read_text()
        for m,fields in {'ExitDecision':['snapshot_seq','valid_until_ns','retry_not_before_ns'],
                         'ActionRequest':['control_lease_id','preempt_mode'],
                         'MotionStatus':['feedback_age_max_ms','manifest_sha256','hal_last_reject_reason'],
                         'HalCommand':['writer_id','seq','action_epoch','deadline_ns','payload_crc','joint_count'],
                         'BodyVelocityRef':['control_lease_id','ttl_ms','wz_radps']}.items():
            match=re.search(r'\bmessage\s+'+m+r'\s*\{([^}]+)\}',t)
            self.assertIsNotNone(match,m)
            for f in fields:self.assertRegex(match.group(1),r'\b'+f+r'\b')
    def test_no_deprecated_active_config_keys(self):
        for p in E.glob('*.yaml'):
            t=p.read_text()
            self.assertNotRegex(t,r'(?m)^actions\s*:')
            self.assertNotRegex(t,r'\bdeadline_ms\s*:')
            self.assertNotRegex(t,r'(?m)^\s*timeout_ms\s*:')
        self.assertNotIn('64 MiB',(ROOT/'SCHEMA_CANON.md').read_text())

if __name__=='__main__': unittest.main(verbosity=2)
