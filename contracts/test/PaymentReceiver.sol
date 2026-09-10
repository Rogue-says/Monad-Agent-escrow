// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
interface IJob {
    function startWork() external;
    function submitWork() external;
    function withdraw(address payable recipient) external;
}
/// @dev Regression fixture only, never deploy as a real worker.
contract PaymentReceiver {
    IJob public job;
    bool public reject;
    bool public reentered;
    uint256 public received;
    function configure(address target, bool shouldReject) external { job = IJob(target); reject = shouldReject; }
    function work() external { job.startWork(); job.submitWork(); }
    function collect(address payable recipient) external { job.withdraw(recipient); }
    receive() external payable {
        require(!reject, "Reject payment");
        received += msg.value;
        try job.withdraw(payable(address(this))) { reentered = true; } catch {}
    }
}
