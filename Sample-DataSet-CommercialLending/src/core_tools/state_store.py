"""
State Store for managing workflow state in Firestore.
Handles persistence of workflow status, HITL approvals, and run metadata.
"""

from google.cloud import firestore
from datetime import datetime
from typing import Dict, List, Optional


class StateStore:
    """Manages workflow state persistence in Firestore."""

    def __init__(self, project_id: str, collection: str):
        """
        Initialize Firestore client.

        Args:
            project_id: GCP project ID
            collection: Firestore collection name
        """
        try:
            self.db = firestore.Client(project=project_id)
            self.collection = collection
            print(f"StateStore: Initialized with collection '{collection}'")
        except Exception as e:
            print(f"StateStore: Warning - Could not initialize Firestore: {e}")
            print(f"StateStore: Running in mock mode. Run 'gcloud auth application-default login' to enable Firestore.")
            self.db = None
            self.collection = collection

    def create_run(self, run_id: str, metadata: dict) -> dict:
        """
        Create a new workflow run record.

        Args:
            run_id: Unique run identifier
            metadata: Initial run metadata (files, created_by, etc.)

        Returns:
            Created run document
        """
        run_data = {
            "run_id": run_id,
            "status": "pending",
            "current_step": "initialized",
            "progress": 0,
            "created_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP,
            **metadata
        }

        if self.db:
            try:
                self.db.collection(self.collection).document(run_id).set(run_data)
                print(f"StateStore: Created run {run_id}")
            except Exception as e:
                print(f"StateStore: Error creating run: {e}")
        else:
            print(f"StateStore: (Mock) Created run {run_id}")

        return run_data

    def update_workflow_step(self, run_id: str, step: str, progress: int, status: str = None, data: dict = None):
        """
        Update the current workflow step and progress.

        Args:
            run_id: Workflow run identifier
            step: Current step name (profiler, mapper, hitl, transform, validator, completed)
            progress: Progress percentage (0-100)
            status: Status of the step (started, completed, failed)
            data: Additional step data to store
        """
        update_data = {
            "current_step": step,
            "progress": progress,
            "updated_at": firestore.SERVER_TIMESTAMP
        }

        if status:
            update_data["status"] = status

        if data:
            update_data[f"step_data_{step}"] = data

        if self.db:
            try:
                self.db.collection(self.collection).document(run_id).update(update_data)
                print(f"StateStore: Updated run {run_id}: step={step}, progress={progress}%")
            except Exception as e:
                print(f"StateStore: Error updating workflow step: {e}")
        else:
            print(f"StateStore: (Mock) Updated run {run_id}: step={step}, progress={progress}%")

    def get_run_status(self, run_id: str) -> Optional[dict]:
        """
        Get the current status of a workflow run.

        Args:
            run_id: Workflow run identifier

        Returns:
            Run status document or None if not found
        """
        if self.db:
            try:
                doc_ref = self.db.collection(self.collection).document(run_id)
                doc = doc_ref.get()
                if doc.exists:
                    return doc.to_dict()
                else:
                    return None
            except Exception as e:
                print(f"StateStore: Error getting run status: {e}")
                return None
        else:
            # Mock response
            return {
                "run_id": run_id,
                "status": "running",
                "current_step": "profiler",
                "progress": 50
            }

    def get_state(self, run_id: str) -> Optional[dict]:
        """
        Legacy method - alias for get_run_status.

        Args:
            run_id: The ID of the run to get the state for.

        Returns:
            The state of the run.
        """
        return self.get_run_status(run_id)

    def set_state(self, run_id: str, state: dict):
        """
        Legacy method - sets complete state for a run.

        Args:
            run_id: The ID of the run to set the state for.
            state: The state to set.
        """
        state["updated_at"] = firestore.SERVER_TIMESTAMP

        if self.db:
            try:
                self.db.collection(self.collection).document(run_id).set(state, merge=True)
                print(f"StateStore: Set state for run {run_id}")
            except Exception as e:
                print(f"StateStore: Error setting state: {e}")
        else:
            print(f"StateStore: (Mock) Set state for run {run_id}")

    def mark_run_complete(self, run_id: str, results: dict = None):
        """
        Mark a workflow run as completed.

        Args:
            run_id: Workflow run identifier
            results: Final results data
        """
        update_data = {
            "status": "completed",
            "current_step": "completed",
            "progress": 100,
            "completed_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP
        }

        if results:
            update_data["results"] = results

        if self.db:
            try:
                self.db.collection(self.collection).document(run_id).update(update_data)
                print(f"StateStore: Marked run {run_id} as completed")
            except Exception as e:
                print(f"StateStore: Error marking run complete: {e}")
        else:
            print(f"StateStore: (Mock) Marked run {run_id} as completed")

    def mark_run_failed(self, run_id: str, error: str):
        """
        Mark a workflow run as failed.

        Args:
            run_id: Workflow run identifier
            error: Error message
        """
        update_data = {
            "status": "failed",
            "error": error,
            "failed_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP
        }

        if self.db:
            try:
                self.db.collection(self.collection).document(run_id).update(update_data)
                print(f"StateStore: Marked run {run_id} as failed: {error}")
            except Exception as e:
                print(f"StateStore: Error marking run failed: {e}")
        else:
            print(f"StateStore: (Mock) Marked run {run_id} as failed: {error}")

    def list_runs(self, limit: int = 10, offset: int = 0) -> List[dict]:
        """
        List all workflow runs.

        Args:
            limit: Maximum number of runs to return
            offset: Number of runs to skip

        Returns:
            List of run documents
        """
        if self.db:
            try:
                query = self.db.collection(self.collection).order_by(
                    "created_at", direction=firestore.Query.DESCENDING
                ).limit(limit).offset(offset)

                runs = []
                for doc in query.stream():
                    runs.append(doc.to_dict())

                return runs
            except Exception as e:
                print(f"StateStore: Error listing runs: {e}")
                return []
        else:
            # Mock response
            return [{
                "run_id": "run_12345",
                "status": "completed",
                "current_step": "completed",
                "progress": 100
            }]


class HITLStateStore:
    """Manages HITL approval state in Firestore."""

    def __init__(self, project_id: str, collection: str = "hitl_approvals"):
        """
        Initialize HITL state store.

        Args:
            project_id: GCP project ID
            collection: Firestore collection name for HITL approvals
        """
        try:
            self.db = firestore.Client(project=project_id)
            self.collection = collection
            print(f"HITLStateStore: Initialized with collection '{collection}'")
        except Exception as e:
            print(f"HITLStateStore: Warning - Could not initialize Firestore: {e}")
            print(f"HITLStateStore: Running in mock mode. Run 'gcloud auth application-default login' to enable.")
            self.db = None
            self.collection = collection

    def store_hitl_mappings(self, run_id: str, mappings: List[dict]):
        """
        Store HITL mapping candidates for approval.

        Args:
            run_id: Workflow run identifier
            mappings: List of mapping candidates with confidence scores
        """
        if self.db:
            try:
                batch = self.db.batch()

                for idx, mapping in enumerate(mappings):
                    doc_id = f"{run_id}_{idx}"
                    doc_ref = self.db.collection(self.collection).document(doc_id)

                    mapping_data = {
                        "run_id": run_id,
                        "mapping_id": str(idx),
                        "source_table": mapping.get("source_table", ""),
                        "source_column": mapping.get("source_column", ""),
                        "target_table": mapping.get("target_table", ""),
                        "target_column": mapping.get("target_column", ""),
                        "confidence": mapping.get("confidence", 0.0),
                        "rationale": mapping.get("rationale", ""),
                        "status": "pending",
                        "created_at": firestore.SERVER_TIMESTAMP
                    }

                    batch.set(doc_ref, mapping_data)

                batch.commit()
                print(f"HITLStateStore: Stored {len(mappings)} mappings for run {run_id}")
            except Exception as e:
                print(f"HITLStateStore: Error storing mappings: {e}")
        else:
            print(f"HITLStateStore: (Mock) Stored {len(mappings)} mappings for run {run_id}")

    def get_pending_mappings(self, run_id: str) -> List[dict]:
        """
        Get all pending HITL mappings for a run.

        Args:
            run_id: Workflow run identifier

        Returns:
            List of pending mapping documents
        """
        if self.db:
            try:
                query = self.db.collection(self.collection).where(
                    "run_id", "==", run_id
                ).where("status", "==", "pending")

                mappings = []
                for doc in query.stream():
                    mappings.append(doc.to_dict())

                return mappings
            except Exception as e:
                print(f"HITLStateStore: Error getting pending mappings: {e}")
                return []
        else:
            # Mock response
            return []

    def approve_mapping(self, run_id: str, mapping_id: str):
        """
        Approve a specific mapping.

        Args:
            run_id: Workflow run identifier
            mapping_id: Mapping identifier
        """
        doc_id = f"{run_id}_{mapping_id}"

        if self.db:
            try:
                self.db.collection(self.collection).document(doc_id).update({
                    "status": "approved",
                    "reviewed_at": firestore.SERVER_TIMESTAMP
                })
                print(f"HITLStateStore: Approved mapping {mapping_id} for run {run_id}")
            except Exception as e:
                print(f"HITLStateStore: Error approving mapping: {e}")
        else:
            print(f"HITLStateStore: (Mock) Approved mapping {mapping_id}")

    def reject_mapping(self, run_id: str, mapping_id: str):
        """
        Reject a specific mapping.

        Args:
            run_id: Workflow run identifier
            mapping_id: Mapping identifier
        """
        doc_id = f"{run_id}_{mapping_id}"

        if self.db:
            try:
                self.db.collection(self.collection).document(doc_id).update({
                    "status": "rejected",
                    "reviewed_at": firestore.SERVER_TIMESTAMP
                })
                print(f"HITLStateStore: Rejected mapping {mapping_id} for run {run_id}")
            except Exception as e:
                print(f"HITLStateStore: Error rejecting mapping: {e}")
        else:
            print(f"HITLStateStore: (Mock) Rejected mapping {mapping_id}")

    def get_approved_mappings(self, run_id: str) -> List[dict]:
        """
        Get all approved mappings for a run.

        Args:
            run_id: Workflow run identifier

        Returns:
            List of approved mapping documents
        """
        if self.db:
            try:
                query = self.db.collection(self.collection).where(
                    "run_id", "==", run_id
                ).where("status", "==", "approved")

                mappings = []
                for doc in query.stream():
                    mappings.append(doc.to_dict())

                return mappings
            except Exception as e:
                print(f"HITLStateStore: Error getting approved mappings: {e}")
                return []
        else:
            # Mock response
            return []

    def all_mappings_reviewed(self, run_id: str) -> bool:
        """
        Check if all mappings for a run have been reviewed.

        Args:
            run_id: Workflow run identifier

        Returns:
            True if all mappings reviewed, False otherwise
        """
        pending = self.get_pending_mappings(run_id)
        return len(pending) == 0
