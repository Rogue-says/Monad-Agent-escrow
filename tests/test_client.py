import json
import subprocess
import time
import unittest
from pathlib import Path
from eth_account import Account
from web3 import Web3
from monad_escrow_client import MonadEscrowClient, amount_to_wei, load_abi

ROOT = Path(__file__).resolve().parents[1]

class ClientIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.node = subprocess.Popen(['node', 'node_modules/hardhat/internal/cli/cli.js', 'node', '--port', '18545'],
                                    cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cls.w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:18545', request_kwargs={'timeout': 2}))
        for _ in range(100):
            if cls.w3.is_connected(): break
            time.sleep(.1)
        else:
            cls.node.terminate()
            raise RuntimeError('Local test node did not start')
        Account.enable_unaudited_hdwallet_features()
        mnemonic='test test test test test test test test test test test junk'
        cls.keys=[Account.from_mnemonic(mnemonic, account_path=f"m/44'/60'/0'/0/{i}").key for i in range(3)]
        artifact=json.loads((ROOT/'artifacts/contracts/EscrowFactory.sol/EscrowFactory.json').read_text())
        factory=cls.w3.eth.contract(abi=artifact['abi'],bytecode=artifact['bytecode'])
        receipt=cls.w3.eth.wait_for_transaction_receipt(factory.constructor().transact({'from':cls.w3.eth.accounts[0]}))
        cls.address=receipt.contractAddress

    @classmethod
    def tearDownClass(cls):
        cls.node.terminate()
        cls.node.wait(timeout=10)

    def client(self,index):
        client=MonadEscrowClient(self.keys[index], 'http://127.0.0.1:18545',1337)
        client.set_factory_address(self.address)
        return client

    def test_full_python_lifecycle(self):
        buyer,worker=self.client(1),self.client(2)
        result=buyer.post_job(123,worker.address,'0.001')
        self.assertIsNotNone(result['escrow_address'])
        worker.act(123,'start'); worker.act(123,'submit'); buyer.act(123,'approve')
        self.assertEqual(worker.get_job(123)['withdrawable'],10**15)
        worker.act(123,'withdraw',worker.address)
        self.assertEqual(worker.get_job(123)['withdrawable'],0)
        self.assertEqual(buyer.get_factory_escrow_count(),1)
        self.assertIsNone(buyer.get_escrow_address(999))

    def test_wrong_network_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'chain ID'):
            MonadEscrowClient(self.keys[1],'http://127.0.0.1:18545',10143)

class AmountTests(unittest.TestCase):
    def test_exact_wei_and_invalid_amounts(self):
        self.assertEqual(amount_to_wei('0.000000000000000001'),1)
        for value in ('NaN','Infinity','-1','0','0.0000000000000000001'):
            with self.assertRaises(ValueError): amount_to_wei(value)

if __name__=='__main__': unittest.main()
