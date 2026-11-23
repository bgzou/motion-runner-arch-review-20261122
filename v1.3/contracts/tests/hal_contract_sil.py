#!/usr/bin/env python3
"""Deterministic SIL implementation of V1.1 HAL acceptance contract.
Proves contract branch behavior only. Does NOT prove firmware watchdog or physical safety.
Run: python tests/hal_contract_sil.py
"""
from __future__ import annotations
import unittest

def crc32c(data: bytes) -> int:
    crc=0xFFFFFFFF
    for b in data:
        crc^=b
        for _ in range(8): crc=(crc>>1)^(0x82F63B78 if (crc&1) else 0)
    return (~crc)&0xFFFFFFFF

class FakeHal:
    def __init__(self):
        self.boot='boot1';self.writer=None;self.token=None;self.state='HAL_SAFE'
        self.epoch=0;self.pending=None;self.last_seq=0;self.last_accepted_ms=None
        self.watchdog='ARMED';self.fault=0;self.ack_event_seq=0
        self.rejection=None;self.accepted=False;self.bus_ok=True;self.drive_output='DISABLED'
    def grant(self,writer,token):
        if self.state!='HAL_SAFE' or not token:return False
        self.writer,self.token=writer,token;self.state='GRANTED';self.pending=None;return True
    def epoch_prepare(self,writer,token,old,new):
        if self.state not in ('ACTIVE','GRANTED') or writer!=self.writer or token!=self.token:return False
        if old!=self.epoch or new!=old+1:return False
        self.pending=new;return True
    def _reject(self,reason,seq):
        self.ack_event_seq+=1;self.accepted=False;self.rejection=reason;return reason
    def command(self,*,now_ms,writer,token,seq,epoch,deadline_ms,payload=b'cmd',crc=None,boot='boot1',count=16,mode='POSITION'):
        if crc is None: crc=crc32c(payload)
        if self.state not in ('GRANTED','ACTIVE') or self.fault:return self._reject('HAL_NOT_ACTIVE',seq)
        if writer!=self.writer or token!=self.token:return self._reject('NOT_OWNER',seq)
        if boot!=self.boot:return self._reject('WRONG_BOOT_ID',seq)
        if seq<=self.last_seq:return self._reject('STALE_SEQ',seq)
        if epoch not in (self.epoch,self.pending):return self._reject('EPOCH_MISMATCH',seq)
        if now_ms>=deadline_ms:return self._reject('DEADLINE_EXPIRED',seq)
        if crc!=crc32c(payload):return self._reject('CRC_MISMATCH',seq)
        if count!=16:return self._reject('JOINT_COUNT_MISMATCH',seq)
        if mode not in ('POSITION','VELOCITY'):return self._reject('UNSUPPORTED_MODE',seq)
        if not self.bus_ok:return self._reject('BUS_UNAVAILABLE',seq)
        if epoch==self.pending:
            self.epoch=self.pending;self.pending=None
        self.last_seq=seq;self.last_accepted_ms=now_ms;self.state='ACTIVE'
        self.drive_output='NORMAL';self.watchdog='REFRESHED';self.ack_event_seq+=1
        self.accepted=True;self.rejection='NONE';return 'ACCEPTED'
    def update(self,now_ms):
        # An independent firmware timer must implement this behavior on real hardware.
        if self.state=='ACTIVE' and self.last_accepted_ms is not None:
            if now_ms-self.last_accepted_ms>=15:self._fault('WATCHDOG_EXPIRED')
    def _fault(self,reason):
        self.fault|=1;self.watchdog='EXPIRED';self.state='HAL_FAULT';self.drive_output='DISABLED'
        self.token=None;self.writer=None;self.pending=None
    def disconnect_bus(self):self.bus_ok=False;self._fault('BUS_UNAVAILABLE')
    def reset(self):
        if self.state!='HAL_FAULT':return False
        self.__init__();return True

class HalTests(unittest.TestCase):
    def setUp(self):
        self.h=FakeHal();self.assertTrue(self.h.grant('rt','private-token'))
        self.assertEqual(self.h.command(now_ms=0,writer='rt',token='private-token',seq=1,epoch=0,deadline_ms=5),'ACCEPTED')
    def send(self,**kwargs):
        d=dict(now_ms=5,writer='rt',token='private-token',seq=2,epoch=0,deadline_ms=10)
        d.update(kwargs);return self.h.command(**d)
    def test_hal01_kill_rt_watchdog(self):
        self.h.update(14);self.assertEqual(self.h.state,'ACTIVE')
        self.h.update(15);self.assertEqual(self.h.state,'HAL_FAULT')
        self.assertEqual(self.h.drive_output,'DISABLED');self.assertIsNone(self.h.token)
    def test_hal02_bus_loss(self):
        self.h.disconnect_bus();self.assertEqual(self.h.drive_output,'DISABLED')
        self.assertEqual(self.h.state,'HAL_FAULT')
    def test_hal03_second_writer(self):
        self.assertFalse(self.h.grant('attacker','a'))
        self.assertEqual(self.send(writer='evil'),'NOT_OWNER')
        self.assertEqual(self.send(token='forged'),'NOT_OWNER')
        self.assertEqual(self.h.writer,'rt')
    def test_hal04_stale_seq(self):
        self.assertEqual(self.send(seq=1),'STALE_SEQ');self.assertEqual(self.h.last_seq,1)
        self.h.update(15);self.assertEqual(self.h.drive_output,'DISABLED')
    def test_hal05_epoch_protocol(self):
        self.assertEqual(self.send(epoch=1),'EPOCH_MISMATCH')
        self.assertTrue(self.h.epoch_prepare('rt','private-token',0,1))
        self.assertEqual(self.send(epoch=1),'ACCEPTED');self.assertEqual(self.h.epoch,1)
        self.assertEqual(self.send(seq=3,epoch=0),'EPOCH_MISMATCH')
    def test_hal06_deadline_expired(self):
        self.assertEqual(self.send(deadline_ms=5),'DEADLINE_EXPIRED')
        self.assertEqual(self.h.last_accepted_ms,0)
    def test_hal07_crc_count_mode(self):
        self.assertEqual(self.send(crc=0),'CRC_MISMATCH')
        self.assertEqual(self.send(count=15),'JOINT_COUNT_MISMATCH')
        self.assertEqual(self.send(mode='TORQUE'),'UNSUPPORTED_MODE')
    def test_hal08_reset_no_reuse(self):
        self.h.update(15);self.assertTrue(self.h.reset())
        self.assertEqual(self.h.command(now_ms=16,writer='rt',token='private-token',seq=2,epoch=0,deadline_ms=20),'HAL_NOT_ACTIVE')
        self.assertTrue(self.h.grant('new_rt','new_token'))
        self.assertEqual(self.h.command(now_ms=17,writer='new_rt',token='new_token',seq=1,epoch=0,deadline_ms=20),'ACCEPTED')
    def test_crc32c_standard_vector(self):
        self.assertEqual(crc32c(b'123456789'),0xE3069283)

if __name__=='__main__':unittest.main(verbosity=2)
