// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./JobEscrow.sol";

contract EscrowFactory {
    address public owner;
    uint256 public escrowCount;
    mapping(uint256 => address) public escrows;
    mapping(uint256 => bool) public jobExists;
    
    event EscrowCreated(uint256 indexed jobId, address indexed escrowAddress, address indexed creator, uint256 amount);
    event EscrowClosed(uint256 indexed jobId, address escrowAddress);
    
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this function");
        _;
    }
    
    constructor() {
        owner = msg.sender;
        escrowCount = 0;
    }
    
    /**
     * @dev Create a new escrow contract for a job
     * @param jobId Unique identifier for the job
     * @param _worker Address of the worker
     * @param _amount Payment amount in wei
     * @return address of the newly created JobEscrow contract
     */
    function createEscrow(
        uint256 jobId, 
        address _worker, 
        uint256 _amount
    ) external payable returns (address) {
        require(_worker != address(0), "Invalid worker address");
        require(_amount > 0, "Amount must be greater than 0");
        require(msg.value == _amount, "Sent value does not match amount");
        require(!jobExists[jobId], "Job already exists");
        
        // Deploy a new JobEscrow contract
        JobEscrow escrow = new JobEscrow{value: msg.value}(
            msg.sender,  // client
            _worker,     // worker
            _amount,     // payment amount
            jobId,
            block.timestamp + 7 days // auto-release deadline
        );
        
        escrows[jobId] = address(escrow);
        jobExists[jobId] = true;
        escrowCount++;
        
        emit EscrowCreated(jobId, address(escrow), msg.sender, _amount);
        return address(escrow);
    }
    
    /**
     * @dev Get the escrow address for a specific job
     * @param jobId The job ID
     * @return address of the JobEscrow contract or address(0) if not found
     */
    function getEscrow(uint256 jobId) external view returns (address) {
        return escrows[jobId];
    }
    
    /**
     * @dev Check if a job escrow exists
     * @param jobId The job ID
     * @return bool indicating if job exists
     */
    function escrowExists(uint256 jobId) external view returns (bool) {
        return jobExists[jobId];
    }
    
    /**
     * @dev Get total number of escrows created
     * @return uint256 total escrow count
     */
    function getEscrowCount() external view returns (uint256) {
        return escrowCount;
    }
}
