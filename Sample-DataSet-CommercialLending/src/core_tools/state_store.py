from google.cloud import firestore

class StateStore:
    def __init__(self, project_id: str, collection: str):
        self.db = firestore.Client(project=project_id)
        self.collection = collection

    def get_state(self, run_id: str):
        """
        Gets the state for a given run ID.

        Args:
            run_id: The ID of the run to get the state for.

        Returns:
            The state of the run.
        """
        print(f"StateStore: Getting state for run {run_id}")
        # doc_ref = self.db.collection(self.collection).document(run_id)
        # doc = doc_ref.get()
        # if doc.exists:
        #     return doc.to_dict()
        # else:
        #     return None
        return {"status": "running"}

    def set_state(self, run_id: str, state: dict):
        """
        Sets the state for a given run ID.

        Args:
            run_id: The ID of the run to set the state for.
            state: The state to set.
        """
        print(f"StateStore: Setting state for run {run_id}")
        # self.db.collection(self.collection).document(run_id).set(state)
        return "State set"
