
def run_hitl(run_id: str, mapping_candidates: list):
    """
    Manages the Human-in-the-Loop validation process via an interactive CLI.

    Args:
        run_id: The unique identifier for this workflow run.
        mapping_candidates: The list of mapping candidates from the Mapper Agent.

    Returns:
        A list of approved mappings.
    """
    print(f"HITL Agent: Starting HITL process for run {run_id}")
    print("Please review the following mapping candidates. Enter 'y' to approve or 'n' to reject.")

    approved_mappings = []
    
    if not mapping_candidates:
        print("HITL Agent: No mapping candidates to review.")
    
    for mapping in mapping_candidates:
        source = mapping['source_column']
        target = mapping['target_column']
        confidence = mapping['confidence']
        
        # Present the mapping to the user
        prompt = (f"\nApprove mapping:\n"
                  f"  Source: {source}\n"
                  f"  Target: {target}\n"
                  f"  Confidence: {confidence:.2f}\n"
                  f"Approve? (y/n): ")
        
        while True:
            user_input = input(prompt).lower().strip()
            if user_input in ['y', 'yes']:
                approved_mappings.append(mapping)
                print(f"--> Approved mapping from {source} to {target}")
                break
            elif user_input in ['n', 'no']:
                print(f"--> Rejected mapping from {source} to {target}")
                break
            else:
                print("Invalid input. Please enter 'y' or 'n'.")

    print(f"\nHITL Agent: HITL process finished for run {run_id}. Approved {len(approved_mappings)} mappings.")
    return approved_mappings

if __name__ == '__main__':
    # Example usage for testing
    test_candidates = [
        {"source_column": "borrower.borrower_id", "target_column": "dim_borrower.borrower_key", "confidence": 0.95},
        {"source_column": "loan.loan_amount", "target_column": "fact_loan_snapshot.loan_amount", "confidence": 0.88},
        {"source_column": "guarantor.guarantor_name", "target_column": "dim_guarantor.guarantor_name", "confidence": 0.92},
    ]
    run_hitl("run_test_interactive", test_candidates)
