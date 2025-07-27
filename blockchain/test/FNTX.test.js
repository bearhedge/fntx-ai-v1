const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("FNTX Token", function () {
  let fntx;
  let owner;
  let addr1;
  let addr2;

  beforeEach(async function () {
    // Get signers
    [owner, addr1, addr2] = await ethers.getSigners();

    // Deploy FNTX token
    const FNTX = await ethers.getContractFactory("FNTX");
    fntx = await FNTX.deploy();
    await fntx.deployed();
  });

  describe("Deployment", function () {
    it("Should set the right name and symbol", async function () {
      expect(await fntx.name()).to.equal("FNTX");
      expect(await fntx.symbol()).to.equal("FNTX");
    });

    it("Should assign the total supply to the deployer", async function () {
      const ownerBalance = await fntx.balanceOf(owner.address);
      const totalSupply = await fntx.totalSupply();
      expect(ownerBalance).to.equal(totalSupply);
    });

    it("Should have 1 trillion tokens total supply", async function () {
      const totalSupply = await fntx.totalSupply();
      const expectedSupply = ethers.utils.parseEther("1000000000000"); // 1 trillion
      expect(totalSupply).to.equal(expectedSupply);
    });

    it("Should have 18 decimals", async function () {
      expect(await fntx.decimals()).to.equal(18);
    });
  });

  describe("Transfers", function () {
    it("Should transfer tokens between accounts", async function () {
      const amount = ethers.utils.parseEther("1000");
      
      await fntx.transfer(addr1.address, amount);
      expect(await fntx.balanceOf(addr1.address)).to.equal(amount);
      
      await fntx.connect(addr1).transfer(addr2.address, amount);
      expect(await fntx.balanceOf(addr2.address)).to.equal(amount);
      expect(await fntx.balanceOf(addr1.address)).to.equal(0);
    });

    it("Should fail if sender doesn't have enough tokens", async function () {
      const initialOwnerBalance = await fntx.balanceOf(owner.address);
      
      await expect(
        fntx.connect(addr1).transfer(owner.address, 1)
      ).to.be.revertedWith("ERC20: transfer amount exceeds balance");
      
      expect(await fntx.balanceOf(owner.address)).to.equal(initialOwnerBalance);
    });
  });

  describe("Burning", function () {
    it("Should allow users to burn their own tokens", async function () {
      const burnAmount = ethers.utils.parseEther("1000");
      const initialSupply = await fntx.totalSupply();
      
      await fntx.burn(burnAmount);
      
      expect(await fntx.totalSupply()).to.equal(initialSupply.sub(burnAmount));
      expect(await fntx.balanceOf(owner.address)).to.equal(initialSupply.sub(burnAmount));
    });

    it("Should allow approved burning from another account", async function () {
      const burnAmount = ethers.utils.parseEther("1000");
      
      // Transfer some tokens to addr1
      await fntx.transfer(addr1.address, burnAmount.mul(2));
      
      // Approve addr2 to burn tokens from addr1
      await fntx.connect(addr1).approve(addr2.address, burnAmount);
      
      // Burn tokens from addr1's account by addr2
      await fntx.connect(addr2).burnFrom(addr1.address, burnAmount);
      
      expect(await fntx.balanceOf(addr1.address)).to.equal(burnAmount);
    });
  });
});