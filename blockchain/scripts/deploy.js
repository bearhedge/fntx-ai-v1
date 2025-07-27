const hre = require("hardhat");

async function main() {
  console.log("Starting FNTX deployment...");

  // Get the deployer account
  const [deployer] = await hre.ethers.getSigners();
  console.log("Deploying contracts with account:", deployer.address);

  // Check deployer balance
  const balance = await deployer.getBalance();
  console.log("Account balance:", hre.ethers.utils.formatEther(balance), "MATIC");

  // Deploy FNTX Token
  console.log("\n1. Deploying FNTX Token...");
  const FNTX = await hre.ethers.getContractFactory("FNTX");
  const fntx = await FNTX.deploy();
  await fntx.deployed();
  console.log("FNTX Token deployed to:", fntx.address);

  // Verify total supply
  const totalSupply = await fntx.totalSupply();
  console.log("Total supply:", hre.ethers.utils.formatEther(totalSupply), "FNTX");

  // Deploy TrackRecord (Upgradeable)
  console.log("\n2. Deploying TrackRecord contract...");
  const TrackRecord = await hre.ethers.getContractFactory("TrackRecord");
  
  // Initial burn amount: 10 FNTX
  const initialBurnAmount = hre.ethers.utils.parseEther("10");
  
  // Deploy as upgradeable proxy
  const trackRecord = await hre.upgrades.deployProxy(
    TrackRecord,
    [fntx.address, initialBurnAmount],
    { initializer: 'initialize' }
  );
  await trackRecord.deployed();
  console.log("TrackRecord deployed to:", trackRecord.address);

  // Get implementation address
  const implementationAddress = await hre.upgrades.erc1967.getImplementationAddress(
    trackRecord.address
  );
  console.log("TrackRecord implementation:", implementationAddress);

  // Save deployment addresses
  const deploymentInfo = {
    network: hre.network.name,
    deployer: deployer.address,
    timestamp: new Date().toISOString(),
    contracts: {
      FNTX: {
        address: fntx.address,
        totalSupply: totalSupply.toString()
      },
      TrackRecord: {
        proxy: trackRecord.address,
        implementation: implementationAddress,
        burnAmount: initialBurnAmount.toString()
      }
    }
  };

  // Write deployment info to file
  const fs = require("fs");
  const path = require("path");
  const deploymentPath = path.join(__dirname, "..", "deployments", `${hre.network.name}.json`);
  
  // Create deployments directory if it doesn't exist
  const deploymentsDir = path.join(__dirname, "..", "deployments");
  if (!fs.existsSync(deploymentsDir)) {
    fs.mkdirSync(deploymentsDir);
  }
  
  fs.writeFileSync(deploymentPath, JSON.stringify(deploymentInfo, null, 2));
  console.log("\nDeployment info saved to:", deploymentPath);

  console.log("\n✅ Deployment complete!");
  console.log("\nNext steps:");
  console.log("1. Verify contracts on PolygonScan");
  console.log("2. Update .env with contract addresses");
  console.log("3. Test with small amounts first");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });