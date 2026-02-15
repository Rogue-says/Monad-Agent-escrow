require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config();

module.exports = {
  solidity: {
    version: "0.8.20",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200,
      },
    },
  },
  networks: {
    hardhat: {
      chainId: 1337,
    },
    monadTestnet: {
      url: process.env.MONAD_TESTNET_RPC || "https://testnet-rpc.monad.xyz/",
      accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : [],
      chainId: 10143,
      gasPrice: 52000000000, // 52 gwei
    },
    // TODO: Update chainId and RPC URL when Monad mainnet launches
    monadMainnet: {
      url: process.env.MONAD_MAINNET_RPC || "https://mainnet-rpc.monad.xyz/",
      accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : [],
      chainId: 0, // PLACEHOLDER — replace with actual mainnet chainId when available
      gasPrice: "auto",
    },
    sepolia: {
      url: process.env.SEPOLIA_RPC || "https://sepolia.infura.io/v3/YOUR_INFURA_KEY",
      accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : [],
      chainId: 11155111,
    },
  },
  etherscan: {
    apiKey: {
      monadTestnet: process.env.ETHERSCAN_API_KEY || "nokey",
      monadMainnet: process.env.ETHERSCAN_API_KEY || "nokey",
      sepolia: process.env.ETHERSCAN_API_KEY || "nokey",
    },
    customChains: [
      {
        network: "monadTestnet",
        chainId: 10143,
        urls: {
          apiURL: "https://testnet-explorer.monad.xyz/api",
          browserURL: "https://testnet-explorer.monad.xyz",
        },
      },
      {
        network: "monadMainnet",
        chainId: 10143,
        urls: {
          apiURL: "https://explorer.monad.xyz/api",
          browserURL: "https://explorer.monad.xyz",
        },
      },
    ],
  },
  paths: {
    sources: "./contracts",
    tests: "./test",
    cache: "./cache",
    artifacts: "./artifacts",
  },
};
