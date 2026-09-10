require("@nomicfoundation/hardhat-ethers");
require("@nomicfoundation/hardhat-chai-matchers");
require("dotenv").config();
// Use the pinned local compiler: tests do not download solc from a second server.
const { subtask } = require("hardhat/config");
const { TASK_COMPILE_SOLIDITY_GET_SOLC_BUILD } = require("hardhat/builtin-tasks/task-names");
subtask(TASK_COMPILE_SOLIDITY_GET_SOLC_BUILD).setAction(async ({ solcVersion }, hre, runSuper) => {
  if (solcVersion === "0.8.20") return { compilerPath: require.resolve("solc/soljson.js"),
    isSolcJs: true, version: solcVersion, longVersion: require("solc").version() };
  return runSuper();
});
const key = process.env.PRIVATE_KEY;
const accounts = key ? [key.startsWith("0x") ? key : `0x${key}`] : [];
module.exports = {
  solidity: { version: "0.8.20", settings: { optimizer: { enabled: true, runs: 200 } } },
  networks: {
    hardhat: { chainId: 1337 },
    localhost: { url: "http://127.0.0.1:8545", chainId: 1337 },
    monadTestnet: { url: process.env.MONAD_TESTNET_RPC || "https://testnet-rpc.monad.xyz", accounts, chainId: 10143 }
  }
};
