"""
HITL (Human-in-the-Loop) Agent - Manages approval of mapping candidates.
Refactored to support both web-based (Firestore) and CLI-based approval.
Enhanced with detailed logging for debugging and monitoring.
"""

import time
from typing import Optional
from src.core_tools.logger import AgentLogger

# Initialize logger
logger = AgentLogger("HITLAgent")


def run_hitl(run_id: str, mapping_candidates: list, hitl_store=None):
    """
    Manages the Human-in-the-Loop validation process.
    Supports both web-based approval (via Firestore) and CLI fallback.

    Args:
        run_id: The unique identifier for this workflow run.
        mapping_candidates: The list of mapping candidates from the Mapper Agent.
        hitl_store: HITLStateStore instance for web-based approval (optional).

    Returns:
        A list of approved mappings.
    """
    logger.set_run_id(run_id)
    start_time = time.time()
    
    logger.header("HITL AGENT")
    logger.info("Starting Human-in-the-Loop validation process", data={
        "candidates": len(mapping_candidates),
        "web_mode": hitl_store is not None
    })

    if not mapping_candidates:
        logger.warning("No mapping candidates to review - returning empty list")
        return []

    # Determine approval method
    if hitl_store:
        logger.info("Using web-based approval via Firestore")
        result = _wait_for_web_approvals(run_id, mapping_candidates, hitl_store)
    else:
        logger.info("Using CLI-based approval (fallback mode)")
        result = _cli_approval(run_id, mapping_candidates)

    duration_ms = int((time.time() - start_time) * 1000)
    logger.separator()
    logger.success("HITL process completed", data={
        "approved": len(result),
        "rejected": len(mapping_candidates) - len(result),
        "duration_ms": duration_ms
    })
    
    return result


def _wait_for_web_approvals(run_id: str, mapping_candidates: list, hitl_store, timeout: int = 3600):
    """
    Wait for web-based approvals via Firestore.
    Polls Firestore every 2 seconds until all mappings are reviewed or timeout.

    Args:
        run_id: Workflow run identifier
        mapping_candidates: List of mapping candidates
        hitl_store: HITLStateStore instance
        timeout: Maximum wait time in seconds (default: 1 hour)

    Returns:
        List of approved mappings
    """
    logger.info(f"Waiting for web-based approval", data={
        "mappings": len(mapping_candidates),
        "timeout_seconds": timeout,
        "timeout_minutes": timeout // 60
    })

    elapsed_time = 0
    poll_interval = 2  # Poll every 2 seconds
    last_pending_count = len(mapping_candidates)

    while elapsed_time < timeout:
        # Check if all mappings have been reviewed
        if hitl_store.all_mappings_reviewed(run_id):
            logger.success("All mappings have been reviewed!")
            break

        # Wait before next poll
        time.sleep(poll_interval)
        elapsed_time += poll_interval

        # Check progress every 10 seconds
        if elapsed_time % 10 == 0:
            pending = hitl_store.get_pending_mappings(run_id)
            pending_count = len(pending)
            
            if pending_count != last_pending_count:
                reviewed = last_pending_count - pending_count
                logger.info(f"Progress update: {reviewed} mapping(s) reviewed", data={
                    "pending": pending_count,
                    "elapsed_seconds": elapsed_time
                })
                last_pending_count = pending_count
            elif elapsed_time % 30 == 0:
                logger.debug(f"Still waiting for approvals", data={
                    "pending": pending_count,
                    "elapsed_seconds": elapsed_time
                })

    # Check timeout
    if elapsed_time >= timeout:
        logger.warning(f"Timeout reached after {timeout} seconds")
        logger.warning("Proceeding with currently approved mappings")

    # Retrieve approved mappings
    logger.info("Retrieving approved mappings from Firestore")
    approved_mappings_data = hitl_store.get_approved_mappings(run_id)

    # Convert back to original format
    approved_mappings = []
    for mapping_data in approved_mappings_data:
        approved_mappings.append({
            "source_table": mapping_data.get("source_table", ""),
            "source_column": mapping_data.get("source_column", ""),
            "target_table": mapping_data.get("target_table", ""),
            "target_column": mapping_data.get("target_column", ""),
            "confidence": mapping_data.get("confidence", 0.0),
            "rationale": mapping_data.get("rationale", "")
        })

    logger.success(f"Retrieved {len(approved_mappings)} approved mappings")
    return approved_mappings


def _cli_approval(run_id: str, mapping_candidates: list):
    """
    CLI-based approval (fallback mode).
    Interactive terminal-based approval process.

    Args:
        run_id: Workflow run identifier
        mapping_candidates: List of mapping candidates

    Returns:
        List of approved mappings
    """
    logger.info("Starting interactive CLI approval process")
    print("\n" + "=" * 60)
    print("HUMAN-IN-THE-LOOP APPROVAL")
    print("=" * 60)
    print("Please review the following mapping candidates.")
    print("Enter 'y' to approve or 'n' to reject.\n")

    approved_mappings = []
    approved_count = 0
    rejected_count = 0

    for idx, mapping in enumerate(mapping_candidates, 1):
        source = mapping.get('source_column', 'unknown')
        target = mapping.get('target_column', 'unknown')
        confidence = mapping.get('confidence', 0.0)
        rationale = mapping.get('rationale', 'No rationale provided')

        logger.info(f"Presenting mapping {idx}/{len(mapping_candidates)}", data={
            "source": source,
            "target": target,
            "confidence": f"{confidence:.2%}"
        })

        # Present the mapping to the user
        print(f"\n{'=' * 60}")
        print(f"Mapping {idx}/{len(mapping_candidates)}")
        print(f"{'=' * 60}")
        print(f"  Source: {source}")
        print(f"  Target: {target}")
        print(f"  Confidence: {confidence:.2%}")
        print(f"  Rationale: {rationale}")
        print(f"{'=' * 60}")

        prompt = "Approve? (y/n): "

        while True:
            user_input = input(prompt).lower().strip()
            if user_input in ['y', 'yes']:
                approved_mappings.append(mapping)
                approved_count += 1
                logger.success(f"Mapping approved: {source} -> {target}")
                print(f"✓ Approved mapping from {source} to {target}")
                break
            elif user_input in ['n', 'no']:
                rejected_count += 1
                logger.info(f"Mapping rejected: {source} -> {target}")
                print(f"✗ Rejected mapping from {source} to {target}")
                break
            else:
                print("Invalid input. Please enter 'y' or 'n'.")

    print(f"\n{'=' * 60}")
    print(f"HITL APPROVAL COMPLETE")
    print(f"Approved: {approved_count} | Rejected: {rejected_count}")
    print(f"{'=' * 60}\n")

    logger.info("CLI approval completed", data={
        "approved": approved_count,
        "rejected": rejected_count
    })

    return approved_mappings


if __name__ == '__main__':
    # Example usage for testing CLI mode
    print("Testing HITL Agent in CLI mode...\n")

    test_candidates = [
        {
            "source_table": "borrower",
            "source_column": "borrower.borrower_id",
            "target_table": "dim_borrower",
            "target_column": "dim_borrower.borrower_key",
            "confidence": 0.95,
            "rationale": "High confidence semantic match based on column name similarity"
        },
        {
            "source_table": "loan",
            "source_column": "loan.loan_amount",
            "target_table": "fact_loan_snapshot",
            "target_column": "fact_loan_snapshot.outstanding_principal",
            "confidence": 0.88,
            "rationale": "Strong match - both represent monetary loan values"
        },
        {
            "source_table": "guarantor",
            "source_column": "guarantor.guarantor_name",
            "target_table": "dim_guarantor",
            "target_column": "dim_guarantor.guarantor_name",
            "confidence": 0.92,
            "rationale": "Exact name match with high semantic similarity"
        },
    ]

    approved = run_hitl("run_test_interactive", test_candidates, hitl_store=None)
    print(f"\nFinal result: {len(approved)} mappings approved")
