#!/usr/bin/env python3
"""CI: verify V1.1 Markdown full examples match the only schema/examples.
Run: python tests/check_doc_contracts.py
No robot hardware or protobuf code generator is needed for this text-level test.
"""
from pathlib import Path
import re, csv, io, unittest, yaml
from jsonschema import Draft202012Validator
import json

P=Path(__file__).resolve().parents[1]
D=(P/'Collie_MC_V1.1_定点修订_PartA-E.md').read_text()
C=(P/'SCHEMA_CANON.md').read_text()

def fenced(text):
    return list(re.finditer(r'```(yaml|csv|cpp|text)\s*\n(.*?)\n```',text,re.S))

class TestDocs(unittest.TestCase):
    def test_all_complete_yaml_graphs_same_as_file(self):
        canonical=yaml.safe_load((P/'examples/action_graph.yaml').read_text())
        schema=json.loads((P/'schemas/action_graph.schema.json').read_text())
        count=0
        for d in (D,C):
            for f in fenced(d):
                if f.group(1)!='yaml' or 'nodes:' not in f.group(2) or 'edges:' not in f.group(2): continue
                sample=yaml.safe_load(f.group(2))
                self.assertEqual(sample,canonical)
                Draft202012Validator(schema).validate(sample)
                count+=1
        self.assertGreaterEqual(count,2)
    def test_16_joint_examples_identical_to_csv(self):
        blocks=[]
        for f in fenced(D):
            if f.group(1)=='csv' and ('demo_obs,' in f.group(2) or 'demo_act,' in f.group(2)):
                blocks.append(f.group(2))
        self.assertEqual(len(blocks),2)
        for body,name in zip(blocks,['demo16_obsspec.csv','demo16_actionspec.csv']):
            self.assertEqual(body.strip(),(P/'examples'/name).read_text().strip())
    def test_schema_design_frozen_across_docs(self):
        proto=(P/'proto/collie_mc_v11.proto').read_text()
        for field in ('HAL_UNKNOWN','mode_plan_id','mode_plan_ready','prepared_mode_plan_id',
                      'control_lease_id','history_order','valid_until_ns','retry_not_before_ns'):
            text=(proto+C+D+' '.join(p.read_text() for p in (P/'schemas').glob('*.json')))
            self.assertIn(field,text)
        for k in ('"execution_kind"','"behavior_role"','"backend_id"'):
            self.assertIn(k,(P/'schemas/runner_manifest.schema.json').read_text())
    def test_old_active_config_forms_absent(self):
        for doc in (D,C,(P/'HAL_CONTRACT.md').read_text()):
            for f in fenced(doc):
                body=f.group(2)
                self.assertNotRegex(body,r'(?m)^\s*actions:\s*')
                self.assertNotRegex(body,r'\bdeadline_ms\b')
                self.assertNotRegex(body,r'\b64\s+MiB\b')
        for f in (P/'examples').glob('*.yaml'):
            self.assertNotRegex(f.read_text(),r'(?m)^\s*actions:\s*')

if __name__=='__main__':unittest.main(verbosity=2)
