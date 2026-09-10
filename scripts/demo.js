const { ethers } = require("hardhat");
async function main() {
  const [arbitrator, client, worker] = await ethers.getSigners();
  const factory = await ethers.deployContract("EscrowFactory", [], arbitrator);
  await factory.waitForDeployment();
  const amount = ethers.parseEther("0.1");
  await (await factory.connect(client).createEscrow(1, worker.address, amount, { value: amount })).wait();
  const job = await ethers.getContractAt("JobEscrow", await factory.getEscrow(1));
  await (await job.connect(worker).startWork()).wait();
  await (await job.connect(worker).submitWork()).wait();
  await (await job.connect(client).approveWork()).wait();
  await (await job.connect(worker).withdraw(worker.address)).wait();
  if (await ethers.provider.getBalance(await job.getAddress()) !== 0n) throw new Error("Unpaid escrow");
  console.log("Created, started, submitted, approved, and paid escrow #1 on a local chain.");
}
main().catch(error => { console.error(error); process.exitCode = 1; });
