// scripts/deploy.js
const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  console.log("🚀 Starting deployment to Monad Testnet...");
  
  // Get deployer account
  const [deployer] = await ethers.getSigners();
  console.log(`📝 Deploying contracts with account: ${deployer.address}`);
  
  // Check balance
  const balance = await ethers.provider.getBalance(deployer.address);
  console.log(`💰 Account balance: ${ethers.formatEther(balance)} MON`);
  
  if (balance === 0n) {
    console.error("❌ Insufficient balance. Please get test tokens from Monad faucet.");
    process.exit(1);
  }
  
  try {
    // Deploy EscrowFactory
    console.log("\n📦 Deploying EscrowFactory...");
    const EscrowFactory = await ethers.getContractFactory("EscrowFactory");
    const factory = await EscrowFactory.deploy();
    await factory.waitForDeployment();
    const factoryAddress = await factory.getAddress();
    
    console.log(`✅ EscrowFactory deployed to: ${factoryAddress}`);
    
    // Save deployment addresses
    const deploymentInfo = {
      network: "monadTestnet",
      chainId: 10143,
      deployer: deployer.address,
      escrowFactory: factoryAddress,
      deploymentTimestamp: new Date().toISOString(),
      deploymentBlock: await ethers.provider.getBlockNumber(),
    };
    
    // Write to deployment file
    const deploymentPath = path.join(__dirname, "../deployments/monad-testnet.json");
    const deploymentsDir = path.dirname(deploymentPath);
    
    if (!fs.existsSync(deploymentsDir)) {
      fs.mkdirSync(deploymentsDir, { recursive: true });
    }
    
    fs.writeFileSync(deploymentPath, JSON.stringify(deploymentInfo, null, 2));
    console.log(`\n📄 Deployment info saved to: ${deploymentPath}`);
    
    // Verify deployment
    console.log("\n✔️ Verifying deployment...");
    const escrowCount = await factory.getEscrowCount();
    console.log(`✅ EscrowFactory is functional. Current escrow count: ${escrowCount}`);
    
    console.log("\n🎉 Deployment successful!");
    console.log(`\n📋 Next steps:`);
    console.log(`1. Update your .env file with ESCROW_FACTORY_ADDRESS=${factoryAddress}`);
    console.log(`2. Use this address in your OpenClaw skill integration`);
    
    return deploymentInfo;
    
  } catch (error) {
    console.error("\n❌ Deployment failed:");
    console.error(error);
    process.exit(1);
  }
}

main();
