#!/usr/bin/env python3
"""Synchronous escrow client. One process per signing account; amounts are decimal strings."""
import argparse
import json
import os
from decimal import Decimal, InvalidOperation
from pathlib import Path
from threading import Lock
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / '.env')


def load_abi(name):
    path = ROOT / 'artifacts' / 'contracts' / f'{name}.sol' / f'{name}.json'
    if not path.exists():
        raise FileNotFoundError('Contract artifacts missing. Run npm run compile first.')
    return json.loads(path.read_text())['abi']


def amount_to_wei(value):
    try:
        amount = Decimal(str(value)) * Decimal(10**18)
        if not amount.is_finite() or amount <= 0 or amount != amount.to_integral_value():
            raise ValueError('Amount must be positive with at most 18 decimal places')
        return int(amount)
    except InvalidOperation as exc:
        raise ValueError('Invalid MON amount') from exc


class MonadEscrowClient:
    def __init__(self, private_key, rpc_url=None, chain_id=None):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url or os.getenv('RPC_URL', 'https://testnet-rpc.monad.xyz'),
                                       request_kwargs={'timeout': 30}))
        if not self.w3.is_connected():
            raise ConnectionError('RPC is unavailable')
        self.chain_id = int(chain_id if chain_id is not None else os.getenv('CHAIN_ID', '10143'))
        if self.w3.eth.chain_id != self.chain_id:
            raise ValueError('RPC chain ID does not match the expected chain')
        self.account = Account.from_key(private_key)
        self.address = self.account.address
        self.escrow_factory_abi = load_abi('EscrowFactory')
        self.job_abi = load_abi('JobEscrow')
        self.escrow_factory_address = None
        self._lock = Lock()

    def set_factory_address(self, address):
        address = Web3.to_checksum_address(address)
        if not self.w3.eth.get_code(address):
            raise ValueError('No factory contract code at this address')
        self.escrow_factory_address = address

    def _factory(self):
        if self.escrow_factory_address is None:
            raise ValueError('EscrowFactory address not set')
        return self.w3.eth.contract(address=self.escrow_factory_address, abi=self.escrow_factory_abi)

    def _send(self, function, value=0):
        # Serialize nonce assignment and confirmation for this client instance.
        with self._lock:
            fields = {'from': self.address, 'value': value, 'chainId': self.chain_id,
                      'nonce': self.w3.eth.get_transaction_count(self.address, 'pending'),
                      'gasPrice': self.w3.eth.gas_price}
            fields['gas'] = (function.estimate_gas(fields) * 120 + 99) // 100
            transaction = function.build_transaction(fields)
            signed = self.account.sign_transaction(transaction)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            try:
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            except Exception as exc:
                raise RuntimeError(f'Transaction broadcast: {tx_hash.hex()}; confirmation unknown. Check it before retrying.') from exc
            if receipt['status'] != 1:
                raise RuntimeError(f'Transaction reverted: {tx_hash.hex()}')
            return receipt

    def get_balance(self):
        return str(self.w3.from_wei(self.w3.eth.get_balance(self.address), 'ether'))

    def post_job(self, job_id, worker_address, budget_in_mon, job_data=None):
        if isinstance(job_id, bool) or not isinstance(job_id, int) or not 0 <= job_id < 2**256:
            raise ValueError('job_id must be a uint256 integer')
        worker = Web3.to_checksum_address(worker_address)
        amount = amount_to_wei(budget_in_mon)
        factory = self._factory()
        receipt = self._send(factory.functions.createEscrow(job_id, worker, amount), amount)
        logs = factory.events.EscrowCreated().process_receipt(receipt)
        if not logs:
            raise RuntimeError('Confirmed transaction did not emit EscrowCreated')
        return {'status': 'success', 'job_id': job_id, 'escrow_address': logs[0]['args']['escrowAddress'],
                'tx_hash': receipt['transactionHash'].hex(), 'block_number': receipt['blockNumber'],
                'gas_used': receipt['gasUsed'], 'job_data': job_data or {}}

    def get_escrow_address(self, job_id):
        address = self._factory().functions.getEscrow(job_id).call()
        return None if int(address, 16) == 0 else address

    def get_factory_escrow_count(self):
        return self._factory().functions.getEscrowCount().call()

    def _job(self, job_id):
        address = self.get_escrow_address(job_id)
        if address is None:
            raise ValueError('Job does not exist')
        return self.w3.eth.contract(address=address, abi=self.job_abi)

    def get_job(self, job_id):
        job = self._job(job_id)
        fields = ['client', 'worker', 'arbitrator', 'amount', 'deadline', 'reviewDeadline',
                  'released', 'beneficiary', 'withdrawable', 'getState']
        return {'address': job.address, **{key: getattr(job.functions, key)().call() for key in fields}}

    def act(self, job_id, action, recipient=None):
        allowed = {'start': 'startWork', 'submit': 'submitWork', 'approve': 'approveWork',
                   'dispute': 'raiseDispute', 'resolve': 'resolveDispute', 'release': 'autoRelease',
                   'refund': 'refund', 'withdraw': 'withdraw'}
        if action not in allowed:
            raise ValueError('Unknown escrow action')
        fn = getattr(self._job(job_id).functions, allowed[action])
        if action in {'resolve', 'withdraw'}:
            if not recipient:
                raise ValueError('This action requires a recipient or dispute winner')
            fn = fn(Web3.to_checksum_address(recipient))
        else:
            fn = fn()
        receipt = self._send(fn)
        return {'status': 'success', 'tx_hash': receipt['transactionHash'].hex()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['balance', 'count', 'show', 'create', 'start', 'submit',
                                          'approve', 'dispute', 'resolve', 'release', 'refund', 'withdraw'])
    parser.add_argument('--job-id', type=int)
    parser.add_argument('--worker')
    parser.add_argument('--amount', help='MON as a decimal string')
    parser.add_argument('--recipient', help='Withdrawal recipient or arbitration winner')
    args = parser.parse_args()
    if args.action not in {'balance', 'count'} and args.job_id is None:
        parser.error('--job-id is required')
    if args.action == 'create' and (not args.worker or not args.amount):
        parser.error('create requires --worker and --amount')
    try:
        if not os.getenv('PRIVATE_KEY'):
            raise ValueError('PRIVATE_KEY is required')
        client = MonadEscrowClient(os.environ['PRIVATE_KEY'])
        if args.action == 'balance':
            result = {'balance': client.get_balance()}
        else:
            client.set_factory_address(os.getenv('ESCROW_FACTORY_ADDRESS', ''))
            if args.action == 'count': result = {'count': client.get_factory_escrow_count()}
            elif args.action == 'show': result = client.get_job(args.job_id)
            elif args.action == 'create': result = client.post_job(args.job_id, args.worker, args.amount)
            else: result = client.act(args.job_id, args.action, args.recipient)
        print(json.dumps(result, indent=2))
    except Exception as exc:
        parser.exit(1, f'Error: {exc}\n')


if __name__ == '__main__':
    main()
