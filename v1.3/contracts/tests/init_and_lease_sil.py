#!/usr/bin/env python3
"""V1.1 INIT/UNKNOWN and ControlLease state-machine SIL tests.
Test logic is independent of motor drivers and has no physical safety claim.
Run: python tests/init_and_lease_sil.py
"""
from __future__ import annotations
import unittest
from dataclasses import dataclass

BANNED_UNKNOWN={'q2b','b2q','biped_balance','recovery','wheel_drive','overlay'}

class SafetyGate:
    def __init__(self):self.power_on()
    def power_on(self):
        self.state='INIT';self.form='UNKNOWN';self.support=False
        self.feedback=False;self.calibrated=False;self.hold_approved=False
        self.boot_motion_approved=False;self.output={'enabled':False,'mode':'PASSIVE'}
    def evaluate(self):
        if not(self.support and self.feedback and self.calibrated and self.form!='UNKNOWN'):
            self.state='DAMPING';self.output={'enabled':False,'mode':'PASSIVE'};return self.state
        if self.hold_approved:
            self.state='SAFE_HOLD';self.output={'enabled':True,'mode':'POSITION'};return self.state
        if self.boot_motion_approved:
            self.state='NORMAL';self.output={'enabled':True,'mode':'POSITION'};return self.state
        self.state='DAMPING';self.output={'enabled':False,'mode':'PASSIVE'};return self.state
    def action_allowed(self,a):
        return self.form!='UNKNOWN' and self.state=='NORMAL' and a not in ('estop','safety')
    def reset_estop(self):self.power_on()

@dataclass
class Lease:
    lease_id: str
    owner: str
    expiry_ms: int
    state: str='GRANTED'
    last_seq: int=0

class LeaseArbiter:
    def __init__(self):self.current={};self.revoked=[]
    def grant(self,scope,owner,lease_id,now_ms,ttl_ms=500):
        l=self.current.get(scope)
        if l and l.state in ('GRANTED','RENEWING') and now_ms<l.expiry_ms:return None
        l=Lease(lease_id,owner,now_ms+ttl_ms)
        self.current[scope]=l
        return l
    def renew(self,scope,owner,lease_id,seq,now_ms,ttl_ms=500):
        l=self.current.get(scope)
        if not l or now_ms>=l.expiry_ms:
            if l:l.state='EXPIRED'
            return False
        if l.owner!=owner or l.lease_id!=lease_id or seq<=l.last_seq:return False
        l.state='RENEWING';l.last_seq=seq
        # Simulate a signed renewal ACK. Until ACK, old expiry is still authoritative.
        l.expiry_ms=now_ms+ttl_ms;l.state='GRANTED';return True
    def allowed(self,scope,owner,lease_id,now_ms):
        l=self.current.get(scope)
        if not l or now_ms>=l.expiry_ms:
            if l:l.state='EXPIRED'
            return False
        return l.state in ('GRANTED','RENEWING') and l.owner==owner and l.lease_id==lease_id
    def revoke(self,scope):
        l=self.current.get(scope)
        if not l:return False
        l.state='REVOKING';self.revoked.append(l.lease_id)
        l.state='REVOKED';return True
    def takeover(self,scope,old,new,new_id,now_ms):
        # No hot writer handoff: revoke old first, invalidate existing reference.
        self.revoke(scope)
        return self.grant(scope,new,new_id,now_ms)

def lost_lease_fallback(action,phase,phase_plan_approved,hold_approved):
    if action=='quad_drive':return 'APPROVED_BRAKE'
    if action in ('q2b','b2q'):
        return 'PHASE_FALLBACK' if phase_plan_approved else 'HAL_SAFE_OUTPUT'
    if action=='balance':return 'APPROVED_SAFE_BALANCE' if phase_plan_approved else 'HAL_SAFE_OUTPUT'
    return 'SAFE_HOLD' if hold_approved else 'HAL_SAFE_OUTPUT'

class TestInit(unittest.TestCase):
    def test_power_on_unknown_not_hold(self):
        s=SafetyGate()
        self.assertEqual(s.state,'INIT')
        self.assertFalse(s.output['enabled'])
        self.assertEqual(s.evaluate(),'DAMPING')
        self.assertFalse(s.output['enabled'])
        for action in BANNED_UNKNOWN:self.assertFalse(s.action_allowed(action))
    def test_feedback_missing_blocks_hold(self):
        s=SafetyGate();s.form='QUAD';s.support=True;s.calibrated=True;s.hold_approved=True
        self.assertEqual(s.evaluate(),'DAMPING')
    def test_support_verified_allows_hold(self):
        s=SafetyGate();s.form='QUAD';s.support=True;s.feedback=True;s.calibrated=True;s.hold_approved=True
        self.assertEqual(s.evaluate(),'SAFE_HOLD')
    def test_auto_normal_only_explicit(self):
        s=SafetyGate();s.form='QUAD';s.support=True;s.feedback=True;s.calibrated=True
        self.assertNotEqual(s.evaluate(),'NORMAL')
        s.boot_motion_approved=True;self.assertEqual(s.evaluate(),'NORMAL')
    def test_estop_reset_returns_init(self):
        s=SafetyGate();s.form='BIPED';s.support=True;s.feedback=True;s.calibrated=True;s.hold_approved=True
        s.evaluate();s.reset_estop()
        self.assertEqual(s.state,'INIT');self.assertEqual(s.form,'UNKNOWN');self.assertFalse(s.output['enabled'])

class TestLease(unittest.TestCase):
    def setUp(self):self.a=LeaseArbiter()
    def test_competition_no_two_active(self):
        self.a.grant('body_velocity','nav','lease1',0)
        self.assertIsNone(self.a.grant('body_velocity','remote','lease2',100))
        self.assertTrue(self.a.allowed('body_velocity','nav','lease1',100))
        self.assertFalse(self.a.allowed('body_velocity','remote','lease2',100))
    def test_lease_expiry_invalidates_reference(self):
        self.a.grant('body_velocity','nav','lease1',0)
        self.assertFalse(self.a.allowed('body_velocity','nav','lease1',500))
        self.assertEqual(self.a.current['body_velocity'].state,'EXPIRED')
    def test_renewal_seq_and_owner(self):
        self.a.grant('body_velocity','nav','lease1',0)
        self.assertTrue(self.a.renew('body_velocity','nav','lease1',1,150))
        self.assertFalse(self.a.renew('body_velocity','nav','lease1',1,200))
        self.assertFalse(self.a.renew('body_velocity','remote','lease1',2,200))
        self.assertTrue(self.a.allowed('body_velocity','nav','lease1',600))
    def test_revocation(self):
        self.a.grant('body_velocity','nav','lease1',0);self.a.revoke('body_velocity')
        self.assertFalse(self.a.allowed('body_velocity','nav','lease1',10))
        self.assertIn('lease1',self.a.revoked)
    def test_takeover_invalidates_old_owner(self):
        self.a.grant('body_velocity','nav','lease1',0)
        new=self.a.takeover('body_velocity','nav','remote','lease2',100)
        self.assertEqual(new.owner,'remote')
        self.assertFalse(self.a.allowed('body_velocity','nav','lease1',101))
        self.assertTrue(self.a.allowed('body_velocity','remote','lease2',101))
    def test_transition_lost_lease_no_blind_reverse(self):
        self.assertEqual(lost_lease_fallback('q2b','TRANSFER',False,False),'HAL_SAFE_OUTPUT')
        self.assertEqual(lost_lease_fallback('q2b','TRANSFER',True,False),'PHASE_FALLBACK')
        self.assertEqual(lost_lease_fallback('balance','BALANCE',False,False),'HAL_SAFE_OUTPUT')

if __name__=='__main__':unittest.main(verbosity=2)
