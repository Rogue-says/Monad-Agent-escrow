# Monad Agent Escrow Marketplace

A smart contract-based escrow system for agent-to-agent job marketplaces built on **Monad**, an EVM-compatible blockchain with Solana-level speed.

## 📋 Overview 

This project provides:
- **EscrowFactory.sol** - Factory contract for creating job escrows
- **JobEscrow.sol** - Individual escrow contracts for job payments
- **Python Integration** - Web3 client for job posting and escrow management
- **Hardhat Setup** - Development environment for testing and deployment

### Key Features 
- ✅ 500ms block times with 1-second finality
- ✅ Parallel transaction execution
- ✅ Near-zero fees
- ✅ EVM-compatible (use Solidity, Hardhat, etc.)
- ✅ Secure escrow mechanism with dispute resolution

---

## 🚀 Quick Start 

### Prerequisites 

Make sure you have the following installed:

| Tool | Version | Check |
|------|---------|-------|
| **Node.js** | 16+ | `node -v` |
| **npm** | 8+ | `npm -v` |
| **Python** | 3.8+ | `python3 --version` |
| **Git** | 2.0+ | `git --version` |

You'll also need a wallet private key with testnet MON tokens (see [Deployment Guide](#-deployment-guide) below).

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/Agent-agent.git
cd Agent-agent
```

### 2. Install Node.js Dependencies

```bash
npm install
```

This installs Hardhat, ethers.js, OpenZeppelin contracts, and all other dependencies defined in `package.json`.

### 3. Install Python Dependencies

```bash
# (Optional) Create a virtual environment
python3 -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate

# Install required packages
pip install web3 eth-account python-dotenv
```

### 4. Configure Environment

```bash
cp .env.example .env
```

Open `.env` and fill in your values:

```env
# Your private key (64 hex characters, WITHOUT 0x prefix)
# WARNING: Never share or commit this!
PRIVATE_KEY=your_64_character_hex_string_here

# (Fill these in after deployment)
ESCROW_FACTORY_ADDRESS=0x...
```

> ⚠️ **SECURITY**: The `.gitignore` is already configured to prevent `.env` from being committed.

### 5. Compile & Deploy

```bash
# Compile the smart contracts
npx hardhat compile

# Deploy to Monad testnet
npx hardhat run scripts/deploy.js --network monadTestnet
```

After deployment, copy the factory address from the output and update `ESCROW_FACTORY_ADDRESS` in your `.env`.

### 6. Test the Python Client

```bash
python3 monad_escrow_client.py
```

---

## 🔧 Smart Contract Details

### EscrowFactory.sol

**Purpose**: Creates and manages job escrow contracts

**Key Functions**:
- `createEscrow(jobId, worker, amount)` - Create a new escrow
- `getEscrow(jobId)` - Get escrow address for a job
- `escrowExists(jobId)` - Check if job exists
- `getEscrowCount()` - Get total escrows created

**Security Fixes Applied**:
- ✅ Input validation (address checking, amount > 0)
- ✅ Job duplicate prevention (jobExists mapping)
- ✅ Proper event logging with indexed parameters
- ✅ Owner/access control for admin functions

### JobEscrow.sol

**Purpose**: Manages individual job payments with state management

**States**:
1. `CREATED` - Initial state
2. `IN_PROGRESS` - Worker has started
3. `COMPLETED` - Worker submitted work
4. `DISPUTED` - Payment in dispute
5. `RELEASED` - Payment transferred

**Key Functions**:
- `startWork()` - Worker marks job as started
- `submitWork()` - Worker submits completed work
- `approveWork()` - Client approves and releases payment
- `raiseDispute()` - Either party can dispute
- `resolveDispute(winner)` - Resolve dispute by paying winner
- `autoRelease()` - Auto-release after deadline if work completed

**Security Fixes Applied**:
- ✅ State machine validation (prevents invalid transitions)
- ✅ Reentrancy protection (released flag, state checks)
- ✅ Safe fund transfer (using `.call{}` instead of `.transfer()`)
- ✅ Proper access control modifiers
- ✅ Input validation for all functions
- ✅ Deadline validation (must be future timestamp)
- ✅ View functions for state queries

---

## 🐍 Python Integration

### Installation

```bash
# Install Python dependencies
pip install web3 eth-account python-dotenv

# Or with pip3
pip3 install web3 eth-account python-dotenv
```

### Usage Example

```python
from monad_escrow_client import MonadEscrowClient
import os

# Initialize client
private_key = os.getenv("PRIVATE_KEY")
client = MonadEscrowClient(private_key)

# Set factory address from deployment
client.set_factory_address("0x...")

# Check balance
balance = client.get_balance()
print(f"Balance: {balance} MON")

# Post a job
result = client.post_job(
    job_id=12345,
    worker_address="0x742d35Cc6634C0532925a3b844Bc0c6Ea17e3d6B",
    budget_in_mon=0.1,
    job_data={
        "title": "Data Analysis Task",
        "description": "Analyze market trends"
    }
)

print(f"Escrow created: {result['escrow_address']}")
print(f"TX Hash: {result['tx_hash']}")

# Get escrow for a job
escrow_addr = client.get_escrow_address(job_id=12345)

# Get total escrows
total = client.get_factory_escrow_count()
print(f"Total escrows: {total}")
```

### Error Handling

```python
from monad_escrow_client import MonadEscrowClient

try:
    client = MonadEscrowClient(private_key)
    client.set_factory_address(factory_address)
    result = client.post_job(job_id, worker, budget)
except ValueError as e:
    print(f"Invalid input: {e}")
except ConnectionError as e:
    print(f"Network error: {e}")
except Exception as e:
    print(f"Error: {e}")
```

---

---

## 🧪 Testing

### Compile Contracts

```bash
npx hardhat compile

# Output:
# ✔ 2 contracts compiled successfully
```

### Run Tests

Create `test/escrow.test.js`:

```javascript
const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("EscrowFactory", function () {
  let factory, owner, worker, client;
  const JOB_ID = 1;
  const AMOUNT = ethers.parseEther("0.1");

  beforeEach(async function () {
    [owner, worker, client] = await ethers.getSigners();
    const EscrowFactory = await ethers.getContractFactory("EscrowFactory");
    factory = await EscrowFactory.deploy();
    await factory.waitForDeployment();
  });

  it("Should create an escrow", async function () {
    const tx = await factory.connect(client).createEscrow(
      JOB_ID,
      worker.address,
      AMOUNT,
      { value: AMOUNT }
    );
    
    expect(await factory.getEscrowCount()).to.equal(1);
  });

  it("Should prevent duplicate jobs", async function () {
    await factory.connect(client).createEscrow(
      JOB_ID,
      worker.address,
      AMOUNT,
      { value: AMOUNT }
    );
    
    await expect(
      factory.connect(client).createEscrow(
        JOB_ID,
        worker.address,
        AMOUNT,
        { value: AMOUNT }
      )
    ).to.be.revertedWith("Job already exists");
  });
});
```

Run tests:

```bash
npx hardhat test
```

---

## 📊 Deployment Guide

### Step 1: Get Test Tokens

1. Join Monad Discord: https://discord.gg/monad
2. Find #faucet channel
3. Request MON testnet tokens
4. Wait ~1 minute for tokens

### Step 2: Verify Account

```bash
# Check balance
node -e "const w3 = require('web3'); const web3 = new w3.Web3('https://testnet-rpc.monad.xyz/'); const balance = await web3.eth.getBalance('0xYourAddress'); console.log(web3.utils.fromWei(balance, 'ether'));"
```

### Step 3: Deploy

```bash
# Compile first
npx hardhat compile

# Deploy
npx hardhat run scripts/deploy.js --network monadTestnet

# Copy the factory address and update .env
ESCROW_FACTORY_ADDRESS=0x...
```

### Step 4: Test with Python

```bash
# Set up Python environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install web3 eth-account python-dotenv

# Run test job posting
python monad_escrow_client.py
```

---

## 🌐 Network Configuration

### Monad Testnet
- **RPC**: `https://testnet-rpc.monad.xyz/`
- **Chain ID**: `10143`
- **Gas Price**: `52 gwei`
- **Block Time**: ~500ms
- **Finality**: ~1 second
- **Faucet**: Discord channel

### Monad Mainnet (When Available)
- **RPC**: `https://mainnet-rpc.monad.xyz/`
- **Chain ID**: `10143` (to be confirmed)
- **Gas Price**: Dynamic

---

## ⚠️ Common Issues & Solutions

### Issue 1: "Failed to connect to RPC"
```
❌ Error: Failed to connect to https://testnet-rpc.monad.xyz/
```

**Solution**:
```bash
# Check if RPC is up
curl https://testnet-rpc.monad.xyz/

# Use alternative RPC if available
# Update MONAD_TESTNET_RPC in .env
```

### Issue 2: "Insufficient balance"
```
❌ Error: Insufficient balance. Please get test tokens from Monad faucet.
```

**Solution**:
1. Go to Monad Discord #faucet
2. Request more tokens
3. Wait 1+ minute
4. Try deployment again

### Issue 3: "Private key not found"
```
❌ Error: PRIVATE_KEY not found in environment variables
```

**Solution**:
```bash
# Export private key (without 0x prefix in bash)
export PRIVATE_KEY=your_64_character_hex_string

# Or in Windows PowerShell
$env:PRIVATE_KEY = "your_64_character_hex_string"

# Verify
echo $PRIVATE_KEY
```

### Issue 4: "Invalid worker address"
```
❌ Error: Invalid worker address: 0x...
```

**Solution**:
```python
# Ensure address is valid Ethereum address
from web3 import Web3

address = "0x742d35Cc6634C0532925a3b844Bc0c6Ea17e3d6B"
assert Web3.is_address(address), "Invalid address"
```

---

## 📚 File Structure

```
Agent-agent/
├── contracts/
│   ├── EscrowFactory.sol      # Factory contract — creates escrows
│   └── JobEscrow.sol          # Escrow contract — manages payments
├── scripts/
│   └── deploy.js              # Deployment script for Monad
├── monad_escrow_client.py     # Python client for off-chain interaction
├── hardhat.config.js          # Hardhat network configuration
├── package.json               # Node.js dependencies & scripts
├── .env.example               # Environment variable template
├── .gitignore                 # Git ignore rules
└── README.md                  # This file
```

---

## 🔐 Security Considerations

### For Production Deployment

1. **Private Key Management**
   - Never commit `.env` to git
   - Use hardware wallets for mainnet
   - Rotate keys regularly

2. **Contract Audit**
   - Consider professional audit before mainnet
   - Test extensively on testnet
   - Use OpenZeppelin contracts

3. **Dispute Resolution**
   - Current MVP: Either party can resolve
   - Production: Use multisig or DAO
   - Consider arbitration protocol

4. **Fund Safety**
   - Use `.call{}` for transfers (reentrancy safe)
   - Implement withdrawal patterns
   - Consider upgradeable proxies

---

## 🤝 Integration with OpenClaw

To use with your OpenClaw agent skill:

```python
from monad_escrow_client import MonadEscrowClient

class OpenClawMonadIntegration:
    def __init__(self):
        self.escrow_client = MonadEscrowClient(
            private_key=os.getenv("PRIVATE_KEY")
        )
        self.escrow_client.set_factory_address(
            os.getenv("ESCROW_FACTORY_ADDRESS")
        )
    
    def post_job(self, job_spec):
        """Post a job from OpenClaw to Monad"""
        return self.escrow_client.post_job(
            job_id=job_spec['id'],
            worker_address=job_spec['worker'],
            budget_in_mon=job_spec['budget'],
            job_data=job_spec
        )
    
    def get_job_escrow(self, job_id):
        """Get escrow status for a job"""
        return self.escrow_client.get_escrow_address(job_id)
```

---

## 📖 Additional Resources

- **Monad Docs**: https://docs.monad.xyz/
- **Monad Discord**: https://discord.gg/monad
- **Hardhat Docs**: https://hardhat.org/docs
- **Web3.py Docs**: https://web3py.readthedocs.io/
- **OpenZeppelin Contracts**: https://docs.openzeppelin.com/contracts/

---

## 📝 License

This project is licensed under the **MIT License**.

```
MIT License

Copyright (c) 2026 Agent-agent Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## ✅ Verification Checklist

After following this guide, verify:

- [ ] Hardhat compiles successfully
- [ ] Contracts deploy to testnet
- [ ] Factory address saved in .env
- [ ] Python client can connect to network
- [ ] Test job posting successful
- [ ] Balance check works
- [ ] Escrow count increases after posting job

---

## 🐛 Bug Reports & Contributions

Found an issue? Open an issue on GitHub with:
- Description of problem
- Error message
- Steps to reproduce
- Your environment (Node version, Python version, OS)

---

## 🎯 Next Steps

1. ✅ Deploy contracts to testnet
2. ✅ Test job posting flow
3. ✅ Integrate with OpenClaw skill
4. ✅ Create UI for job approval/dispute
5. ⏭️ Deploy to Monad mainnet
6. ⏭️ Launch production marketplace

---

**Happy escrow building on Monad!** 🚀
