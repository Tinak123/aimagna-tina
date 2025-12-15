import os
from dotenv import load_dotenv

from src.orchestrator_agent.main import run_orchestration

# Load environment variables from .env file
load_dotenv()

def main():
    """
    Main function to start the multi-agent data integration workflow.
    """
    print("Starting the multi-agent data integration workflow...")

    # TODO: Implement the trigger mechanism (e.g., chatbot, file upload)
    run_id = "run_12345"  # Example run_id

    # Start the orchestration
    run_orchestration(run_id)

    print("Multi-agent data integration workflow finished.")

if __name__ == "__main__":
    main()
