const { ethers, network } = require("hardhat");
const fs = require("node:fs");
const path = require("node:path");
async function main() {
  const [deployer] = await ethers.getSigners();
  if (!deployer) throw new Error("No deployment account configured");
  const factory = await ethers.deployContract("EscrowFactory");
  await factory.waitForDeployment();
  const receipt = await factory.deploymentTransaction().wait();
  const info = { network: network.name, chainId: Number((await ethers.provider.getNetwork()).chainId),
    deployer: deployer.address, arbitrator: deployer.address, escrowFactory: await factory.getAddress(),
    deploymentBlock: receipt.blockNumber, deploymentTimestamp: new Date().toISOString() };
  const dir = path.join(__dirname, "../deployments");
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, `${network.name}.json`), JSON.stringify(info, null, 2));
  console.log(info);
}
main().catch(error => { console.error(error); process.exitCode = 1; });
