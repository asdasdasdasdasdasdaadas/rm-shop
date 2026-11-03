import base64
import copy
from datetime import datetime,timezone
from decimal import Decimal
import unittest
from tonsdk.boc import Cell
from app import gram

WALLET='UQBuU8RCIxH121MjJofAC2xyvn-7pr2LmdqIiO5d_xVkkGgT'

def transaction(comment='gram_order',value=10**9):
    cell=Cell();cell.bits.write_uint(0,32);cell.bits.write_string(comment)
    raw=gram.address_raw(WALLET)
    return dict(account=raw,hash=base64.b64encode(b'x'*32).decode(),lt='100',now=1793632157,
        mc_block_seqno=10,emulated=False,finality='finalized',
        description={'type':'ord','aborted':False,'compute_ph':{'success':True},'action':{'success':True}},
        in_msg={'source':'0:'+'1'*64,'destination':raw,'value':str(value),'bounced':False,
                'message_content':{'body':base64.b64encode(cell.to_boc()).decode()}})

class GramTest(unittest.TestCase):
    def test_telegram_wallet_link_uses_decimal_grams(self):
        order=gram.public_order({'id':'order','status':'pending','amount_rub':300,
            'nano_amount':3092857879,'rate_rub':Decimal('97.03'),'wallet':gram.address_raw(WALLET),
            'comment':'gram_order','expires_at':datetime(2026,1,1,tzinfo=timezone.utc)})
        self.assertEqual(order['telegram_wallet_url'],
            'https://t.me/sendgrams?to='+WALLET+'&amount=3.092857879')
        self.assertNotIn('wallet_url',order)
        self.assertNotIn('transfer_uri',order)

    def test_wallet_checksum_and_mainnet(self):
        self.assertEqual(gram.friendly_address(WALLET),WALLET)
        self.assertEqual(gram.friendly_address(gram.address_raw(WALLET)),WALLET)
        for value in (WALLET[:-1]+'A','garbage','-1:'+'1'*64):
            with self.assertRaises(ValueError): gram.address_raw(value)
        data=bytearray(base64.urlsafe_b64decode(WALLET));data[0]|=128
        import binascii
        data[-2:]=binascii.crc_hqx(data[:-2],0).to_bytes(2,'big')
        with self.assertRaises(ValueError): gram.address_raw(base64.urlsafe_b64encode(data).decode())

    def test_rate_freshness_and_exact_rounding(self):
        self.assertEqual(gram.nano_amount(100,3),33333333334)
        self.assertEqual(gram.validate_rate({'the-open-network':{'rub':97.03,'last_updated_at':100}},200),(Decimal('97.03'),100))
        for rate,stamp in [('NaN',100),(0,100),(100,0),(100,400)]:
            with self.assertRaises(ValueError): gram.validate_rate({'the-open-network':{'rub':rate,'last_updated_at':stamp}},200)

    def test_native_payment_and_rejected_messages(self):
        tx=transaction();result=gram.incoming(tx,gram.address_raw(WALLET),10)
        self.assertEqual(result['comment'],'gram_order');self.assertEqual(result['nano'],10**9)
        self.assertEqual(result['hash'],'78'*32)
        for change in ('aborted','bounced','compute','action','destination','emulated'):
            t=copy.deepcopy(tx)
            if change=='aborted':t['description']['aborted']=True
            elif change=='bounced':t['in_msg']['bounced']=True
            elif change=='compute':t['description']['compute_ph']['success']=False
            elif change=='action':t['description']['action']['success']=False
            elif change=='destination':t['in_msg']['destination']='0:'+'1'*64
            else:t['emulated']=True
            self.assertIsNone(gram.incoming(t,gram.address_raw(WALLET),10),change)
        with self.assertRaises(ValueError):gram.incoming(tx,gram.address_raw(WALLET),9)
        tx['finality']='pending'
        with self.assertRaises(ValueError):gram.incoming(tx,gram.address_raw(WALLET),10)
        self.assertEqual(gram.text_comment('bad'), '')
        cell=Cell();cell.bits.write_uint(0x7362d09c,32);cell.bits.write_string('gram_order')
        self.assertEqual(gram.text_comment(base64.b64encode(cell.to_boc()).decode()),'')
