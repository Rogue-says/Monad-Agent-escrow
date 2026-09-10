// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @notice Native-token escrow with independent arbitration and pull payments.
/// @dev Experimental, unaudited. The arbitrator is trusted and can delay disputes.
contract JobEscrow {
    address public immutable client;
    address public immutable worker;
    address public immutable arbitrator;
    uint256 public immutable amount;
    uint256 public immutable jobId;
    uint256 public immutable deadline;
    uint256 public constant REVIEW_PERIOD = 2 days;
    uint256 public reviewDeadline;
    bool public released;
    address public beneficiary;
    uint256 public withdrawable;
    enum State { CREATED, IN_PROGRESS, COMPLETED, DISPUTED, RELEASED, REFUNDED }
    State public state;

    event WorkStarted(uint256 indexed jobId, address indexed worker);
    event WorkSubmitted(uint256 indexed jobId, address indexed worker);
    event WorkApproved(uint256 indexed jobId, address indexed client);
    event DisputeRaised(uint256 indexed jobId, address indexed raiser);
    event DisputeResolved(uint256 indexed jobId, address indexed winner);
    event AutoReleased(uint256 indexed jobId);
    event Refunded(uint256 indexed jobId);
    event Withdrawn(address indexed recipient, uint256 amount);

    modifier onlyClient() { require(msg.sender == client, "Only client"); _; }
    modifier onlyWorker() { require(msg.sender == worker, "Only worker"); _; }
    modifier notReleased() { require(!released, "Funds already released"); _; }

    constructor(address _client, address _worker, uint256 _amount,
        uint256 _jobId, uint256 _deadline, address _arbitrator) payable {
        require(_client != address(0) && _worker != address(0), "Invalid party");
        require(_client != _worker, "Parties must differ");
        require(_arbitrator != address(0) && _arbitrator != _client && _arbitrator != _worker,
            "Arbitrator must be independent");
        require(_amount > 0 && msg.value == _amount, "Incorrect funding");
        require(_deadline > block.timestamp, "Invalid deadline");
        client = _client; worker = _worker; amount = _amount; jobId = _jobId;
        deadline = _deadline; arbitrator = _arbitrator;
    }

    function startWork() external onlyWorker notReleased {
        require(state == State.CREATED, "Invalid state for starting work");
        require(block.timestamp < deadline, "Work deadline passed");
        state = State.IN_PROGRESS;
        emit WorkStarted(jobId, worker);
    }

    function submitWork() external onlyWorker notReleased {
        require(state == State.IN_PROGRESS, "Work not in progress");
        require(block.timestamp < deadline, "Work deadline passed");
        state = State.COMPLETED;
        reviewDeadline = block.timestamp + REVIEW_PERIOD;
        emit WorkSubmitted(jobId, worker);
    }

    function approveWork() external onlyClient notReleased {
        require(state == State.COMPLETED, "Work not completed");
        _settle(worker);
        emit WorkApproved(jobId, client);
    }

    function raiseDispute() external notReleased {
        require(msg.sender == client || msg.sender == worker, "Unauthorized");
        require(state == State.IN_PROGRESS || state == State.COMPLETED, "Invalid state for dispute");
        require(block.timestamp < (state == State.COMPLETED ? reviewDeadline : deadline), "Dispute window closed");
        state = State.DISPUTED;
        emit DisputeRaised(jobId, msg.sender);
    }

    function resolveDispute(address winner) external notReleased {
        require(msg.sender == arbitrator, "Only arbitrator");
        require(state == State.DISPUTED, "No active dispute");
        require(winner == client || winner == worker, "Invalid winner");
        _settle(winner);
        emit DisputeResolved(jobId, winner);
    }

    /// @notice A keeper or either party must submit this transaction; no automatic scheduler.
    function autoRelease() external notReleased {
        require(state == State.COMPLETED, "Work not completed");
        require(block.timestamp >= reviewDeadline, "Review period active");
        _settle(worker);
        emit AutoReleased(jobId);
    }

    function refund() external onlyClient notReleased {
        require(state == State.CREATED || state == State.IN_PROGRESS, "Not refundable");
        require(block.timestamp >= deadline, "Work deadline active");
        _settle(client);
        emit Refunded(jobId);
    }

    function _settle(address winner) private {
        released = true;
        state = winner == client ? State.REFUNDED : State.RELEASED;
        beneficiary = winner;
        withdrawable = amount;
    }

    /// @notice The beneficiary can redirect payment if its own receive function rejects tokens.
    function withdraw(address payable recipient) external {
        require(msg.sender == beneficiary, "Only beneficiary");
        require(recipient != address(0), "Invalid recipient");
        uint256 value = withdrawable;
        require(value > 0, "Nothing to withdraw");
        withdrawable = 0;
        (bool success,) = recipient.call{value: value}("");
        require(success, "Transfer failed");
        emit Withdrawn(recipient, value);
    }

    function getState() external view returns (uint256) { return uint256(state); }
    function getTimeUntilDeadline() external view returns (uint256) {
        return block.timestamp >= deadline ? 0 : deadline - block.timestamp;
    }
    function isActive() external view returns (bool) { return !released; }
}
