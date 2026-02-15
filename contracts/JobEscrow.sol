// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract JobEscrow {
    address public client;
    address public worker;
    uint256 public amount;
    uint256 public jobId;
    uint256 public deadline;
    bool public released;
    
    enum State { CREATED, IN_PROGRESS, COMPLETED, DISPUTED, RELEASED }
    State public state;
    
    event WorkStarted(uint256 indexed jobId, address indexed worker);
    event WorkSubmitted(uint256 indexed jobId, address indexed worker);
    event WorkApproved(uint256 indexed jobId, address indexed client);
    event DisputeRaised(uint256 indexed jobId, address indexed raiser);
    event DisputeResolved(uint256 indexed jobId, address indexed winner);
    event AutoReleased(uint256 indexed jobId);
    
    modifier onlyClient() { 
        require(msg.sender == client, "Only client can call this"); 
        _; 
    }
    
    modifier onlyWorker() { 
        require(msg.sender == worker, "Only worker can call this"); 
        _; 
    }
    
    modifier onlyParties() {
        require(msg.sender == client || msg.sender == worker, "Unauthorized");
        _;
    }
    
    modifier notReleased() {
        require(!released, "Funds already released");
        _;
    }
    
    constructor(
        address _client, 
        address _worker, 
        uint256 _amount, 
        uint256 _jobId, 
        uint256 _deadline
    ) payable {
        require(_client != address(0), "Invalid client address");
        require(_worker != address(0), "Invalid worker address");
        require(msg.value == _amount, "Incorrect amount sent");
        require(_amount > 0, "Amount must be greater than 0");
        require(_deadline > block.timestamp, "Deadline must be in the future");
        
        client = _client;
        worker = _worker;
        amount = _amount;
        jobId = _jobId;
        deadline = _deadline;
        state = State.CREATED;
        released = false;
    }
    
    /**
     * @dev Worker starts the job
     */
    function startWork() external onlyWorker notReleased {
        require(state == State.CREATED, "Invalid state for starting work");
        state = State.IN_PROGRESS;
        emit WorkStarted(jobId, worker);
    }
    
    /**
     * @dev Worker submits completed work
     */
    function submitWork() external onlyWorker notReleased {
        require(state == State.IN_PROGRESS, "Work not in progress");
        state = State.COMPLETED;
        emit WorkSubmitted(jobId, worker);
    }
    
    /**
     * @dev Client approves work and releases payment
     */
    function approveWork() external onlyClient notReleased {
        require(state == State.COMPLETED, "Work not completed");
        
        state = State.RELEASED;
        released = true;
        
        // Use call instead of transfer for better safety
        (bool success, ) = payable(worker).call{value: amount}("");
        require(success, "Payment transfer failed");
        
        emit WorkApproved(jobId, client);
    }
    
    /**
     * @dev Either party can raise a dispute
     */
    function raiseDispute() external onlyParties notReleased {
        require(
            state == State.IN_PROGRESS || state == State.COMPLETED, 
            "Invalid state for dispute"
        );
        state = State.DISPUTED;
        emit DisputeRaised(jobId, msg.sender);
    }
    
    /**
     * @dev Resolve dispute - in MVP, either party can resolve
     * @dev In production, restrict to admin/arbitrator multisig
     * @param winner Address of the dispute winner
     */
    function resolveDispute(address winner) external onlyParties notReleased {
        require(state == State.DISPUTED, "No active dispute");
        require(
            winner == client || winner == worker, 
            "Winner must be client or worker"
        );
        
        state = State.RELEASED;
        released = true;
        
        // Use call instead of transfer for better safety
        (bool success, ) = payable(winner).call{value: amount}("");
        require(success, "Payment transfer failed");
        
        emit DisputeResolved(jobId, winner);
    }
    
    /**
     * @dev Auto-release funds if deadline passed and work is completed
     * Can be called by anyone (e.g., a keeper service)
     */
    function autoRelease() external notReleased {
        require(block.timestamp > deadline, "Deadline not yet passed");
        require(state == State.COMPLETED, "Work not completed");
        
        state = State.RELEASED;
        released = true;
        
        // Use call instead of transfer for better safety
        (bool success, ) = payable(worker).call{value: amount}("");
        require(success, "Payment transfer failed");
        
        emit AutoReleased(jobId);
    }
    
    /**
     * @dev Get current escrow state
     * @return uint256 representing the current state
     */
    function getState() external view returns (uint256) {
        return uint256(state);
    }
    
    /**
     * @dev Get remaining time until deadline
     * @return uint256 seconds until deadline (0 if passed)
     */
    function getTimeUntilDeadline() external view returns (uint256) {
        if (block.timestamp >= deadline) {
            return 0;
        }
        return deadline - block.timestamp;
    }
    
    /**
     * @dev Check if escrow is still active (funds locked)
     * @return bool true if funds are still locked
     */
    function isActive() external view returns (bool) {
        return !released;
    }
}
