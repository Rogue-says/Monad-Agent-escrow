# Monad Agent Escrow

Native-token job escrow contracts and a Python client for agent-to-agent payments. The local workflow covers funding, work submission, approval, disputes, deadline refunds and withdrawal.

**Status: tested local prototype, not an audited production marketplace.** This revision fixes a critical flaw in the old dispute mechanism: clients and workers can no longer award themselves disputed funds.

## Run the complete demo

Requires Node.js 22+ and npm. Python integration requires Python 3.10+.

```bash
git clone https://github.com/Rogue-says/Monad-Agent-escrow.git
cd Monad-Agent-escrow
npm ci
npm test
npm run demo
```

The demo creates an in-memory blockchain, deploys a factory, funds a job, starts and submits work, approves it, and withdraws payment. It uses local test accounts and no real tokens. The local chain disappears when the demo exits.

## Payment lifecycle

| Action | Caller | Requirement / result |
| --- | --- | --- |
| `createEscrow(jobId, worker, amount)` | Client | Exact native-token funding; unique global job ID |
| `startWork()` | Worker | Created job, before the seven-day work deadline |
| `submitWork()` | Worker | In progress, before the work deadline; starts a two-day review window |
| `approveWork()` | Client | Completed work; credits payment to the worker |
| `raiseDispute()` | Either party | In progress before deadline, or completed before review expires |
| `resolveDispute(winner)` | Arbitrator | Disputed job; winner must be its client or worker |
| `autoRelease()` | Anyone | Completed, undisputed work after the review window |
| `refund()` | Client | Unstarted or unfinished work after the work deadline |
| `withdraw(recipient)` | Beneficiary | Transfers the credited payment once; recipient may differ from beneficiary |

**Settlement and withdrawal are separate transactions.** Approval, arbitration, refund and timeout settle who owns the deposit. The beneficiary then withdraws. This prevents a recipient that rejects transfers from blocking settlement.

The factory deployer is its immutable arbitrator. It must differ from both parties, so use three separate accounts. Deploying with an EOA trusts that EOA; a multisig is not automatically created. Disputed deposits remain locked until the arbitrator decides. There is no DAO, automatic evidence verification, dispute timeout, scheduler, web UI, or discovery marketplace.

States retain their old numeric values: `CREATED=0`, `IN_PROGRESS=1`, `COMPLETED=2`, `DISPUTED=3`, `RELEASED=4`; `REFUNDED=5` is new. `released` means settled, including refunds; inspect `withdrawable` to see unpaid credits.

## Persistent local node and Python client

Terminal 1:

```bash
npm run node
```

Terminal 2:

```bash
npm run deploy:local
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set `.env` with `RPC_URL=http://127.0.0.1:8545`, `CHAIN_ID=1337`, the factory address from `deployments/localhost.json`, and the appropriate local client's private key. Use a different local account for the worker; account 0 deployed the factory and is the arbitrator. Never fund Hardhat's publicly known accounts on a public network.

```bash
python monad_escrow_client.py balance
python monad_escrow_client.py create --job-id 1 --worker 0xWORKER_ADDRESS --amount 0.1
python monad_escrow_client.py show --job-id 1
# Switch PRIVATE_KEY to the worker:
python monad_escrow_client.py start --job-id 1
python monad_escrow_client.py submit --job-id 1
# Switch PRIVATE_KEY to the client:
python monad_escrow_client.py approve --job-id 1
# Switch PRIVATE_KEY to the worker:
python monad_escrow_client.py withdraw --job-id 1 --recipient 0xWORKER_ADDRESS
```

Replace address placeholders with actual addresses. `dispute`, `resolve --recipient`, `release` and `refund` are also supported. Running the CLI without an action prints help and cannot accidentally send a payment.

The client loads the compiled contract ABIs, checks the RPC chain ID and factory bytecode, estimates gas, requests pending nonces, and verifies receipt success. Amounts use decimal strings to preserve wei precision. `job_data` is returned locally; it is not written on-chain. RPC errors propagate instead of appearing as zero counts or missing jobs. A confirmation timeout reports the transaction hash: check that hash before retrying.

Use one process per signing account. The instance lock does not coordinate separate agents sharing a key.

## Monad testnet

Configure `PRIVATE_KEY`, `MONAD_TESTNET_RPC` and `RPC_URL` for a testnet account, then:

```bash
npm run deploy:testnet
```

The configured testnet chain ID is `10143`. Deployment metadata records the actual network, chain ID, block and factory address in `deployments/monadTestnet.json`. The default RPC is `https://testnet-rpc.monad.xyz`; check [Monad documentation](https://docs.monad.xyz/) for current endpoints. No public-network deployment was performed as part of this repair. The old mainnet configuration contained placeholder values and has been removed.

## Validation

```bash
npm test
npm run demo
python -m unittest discover -s tests -v
```

Contract tests cover access control, independent arbitration, duplicate IDs, payment settlement, refunds, deadline boundaries and repeated withdrawals. Python tests launch a local Hardhat node and exercise the real client through creation, submission, approval and withdrawal, plus wrong-chain and exact-amount checks.

The compiler is pinned to `solc` 0.8.20 and loaded locally after dependency installation. CI runs both suites.

## Migration and remaining limitations

These contract changes require a **new factory deployment**. Existing deployed escrows retain their original code and vulnerability. The constructor ABI, review deadline and pull-payment behavior changed; rebuild artifacts and update clients together.

Global numeric job IDs can be claimed by another funded transaction; use unpredictable IDs and verify the returned escrow's parties. Arbitration remains trusted and has no liveness guarantee. Deposits sent by forced transfers are not part of the job's credited amount. Tests are not a security audit. Use testnet tokens until independent review and an operational arbitration process exist.

## Dependency audit

The retained Hardhat 2 / Solidity development toolchain still has published npm audit advisories, including transitive ZIP handling, serialization, temporary-file handling and HTTP client dependencies. Compatible updates were applied; a clean audit is **not** claimed. A Hardhat 3 migration and compiler/toolchain review remain necessary. Do not expose the local Hardhat node to untrusted networks.

MIT license; see [LICENSE](LICENSE).
