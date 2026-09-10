const { expect } = require('chai');
const { ethers } = require('hardhat');
const { time } = require('@nomicfoundation/hardhat-network-helpers');
describe('Escrow lifecycle', function () {
  let arb, client, worker, stranger, factory, job;
  const amount = ethers.parseEther('0.1');
  beforeEach(async function () {
    [arb, client, worker, stranger] = await ethers.getSigners();
    factory = await ethers.deployContract('EscrowFactory');
    await factory.connect(client).createEscrow(1, worker.address, amount, { value: amount });
    job = await ethers.getContractAt('JobEscrow', await factory.getEscrow(1));
  });
  async function submit() { await job.connect(worker).startWork(); await job.connect(worker).submitWork(); }
  it('funds the child and prevents duplicate IDs', async function () {
    expect(await ethers.provider.getBalance(await job.getAddress())).to.equal(amount);
    await expect(factory.connect(client).createEscrow(1, worker.address, amount, {value: amount})).to.be.revertedWith('Job already exists');
  });
  it('requires independent parties and arbitrator', async function () {
    await expect(factory.createEscrow(2, worker.address, amount, {value: amount})).to.be.revertedWith('Arbitrator must be independent');
    await expect(factory.connect(client).createEscrow(2, client.address, amount, {value: amount})).to.be.revertedWith('Parties must differ');
  });
  it('enforces roles and transitions', async function () {
    await expect(job.connect(stranger).startWork()).to.be.revertedWith('Only worker');
    await expect(job.connect(client).approveWork()).to.be.revertedWith('Work not completed');
    await expect(job.connect(worker).submitWork()).to.be.revertedWith('Work not in progress');
  });
  it('approves and withdraws exactly once', async function () {
    await submit(); await job.connect(client).approveWork();
    await expect(job.connect(stranger).withdraw(stranger.address)).to.be.revertedWith('Only beneficiary');
    await expect(job.connect(worker).withdraw(worker.address)).to.changeEtherBalances([job, worker], [-amount, amount]);
    await expect(job.connect(worker).withdraw(worker.address)).to.be.revertedWith('Nothing to withdraw');
    await expect(job.connect(client).approveWork()).to.be.revertedWith('Funds already released');
  });
  it('does not let parties award themselves disputed funds', async function () {
    await submit(); await job.connect(client).raiseDispute();
    for (const signer of [client, worker, stranger]) {
      await expect(job.connect(signer).resolveDispute(signer.address)).to.be.revertedWith('Only arbitrator');
    }
    await expect(job.resolveDispute(stranger.address)).to.be.revertedWith('Invalid winner');
    await job.resolveDispute(client.address);
    expect(await job.getState()).to.equal(5);
    await expect(job.connect(client).withdraw(client.address)).to.changeEtherBalance(client, amount);
  });
  it('refunds unstarted and unfinished jobs after expiry', async function () {
    await job.connect(worker).startWork();
    await expect(job.connect(client).refund()).to.be.revertedWith('Work deadline active');
    await time.increaseTo(await job.deadline());
    await expect(job.connect(worker).submitWork()).to.be.revertedWith('Work deadline passed');
    await job.connect(client).refund();
    expect(await job.beneficiary()).to.equal(client.address);
  });
  it('refunds a job the worker never starts', async function () {
    await time.increaseTo(await job.deadline());
    await expect(job.connect(worker).startWork()).to.be.revertedWith('Work deadline passed');
    await job.connect(client).refund();
  });
  it('gives late submissions a full review window', async function () {
    await job.connect(worker).startWork();
    await time.increaseTo((await job.deadline()) - 10n);
    await job.connect(worker).submitWork();
    await time.increaseTo(await job.deadline());
    await expect(job.autoRelease()).to.be.revertedWith('Review period active');
    await expect(job.connect(client).refund()).to.be.revertedWith('Not refundable');
    await time.increaseTo(await job.reviewDeadline());
    await job.connect(stranger).autoRelease();
    expect(await job.beneficiary()).to.equal(worker.address);
  });
  it('does not auto-release an active dispute', async function () {
    await submit(); await job.connect(client).raiseDispute();
    await time.increase(9 * 86400);
    await expect(job.autoRelease()).to.be.revertedWith('Work not completed');
    await expect(job.connect(client).refund()).to.be.revertedWith('Not refundable');
  });
  it('preserves rejected credits and blocks reentrant withdrawals', async function () {
    const receiver = await ethers.deployContract('PaymentReceiver');
    await factory.connect(client).createEscrow(2, await receiver.getAddress(), amount, {value: amount});
    const other = await ethers.getContractAt('JobEscrow', await factory.getEscrow(2));
    await receiver.configure(await other.getAddress(), true);
    await receiver.work(); await other.connect(client).approveWork();
    await expect(receiver.collect(await receiver.getAddress())).to.be.revertedWith('Transfer failed');
    expect(await other.withdrawable()).to.equal(amount);
    await receiver.configure(await other.getAddress(), false);
    await receiver.collect(await receiver.getAddress());
    expect(await receiver.received()).to.equal(amount);
    expect(await receiver.reentered()).to.equal(false);
    expect(await other.withdrawable()).to.equal(0);
  });
});
