# HITL/client/label_studio_client.py
"""Label Studio client wrapper for HITL OCR workflow using direct API calls."""

import os
from typing import List, Optional

import requests
from dotenv import load_dotenv


class HITLClient:
    """Client for interacting with Label Studio for HITL OCR workflow."""

    def __init__(self, url: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize the client.

        Args:
            url: Label Studio URL (default: from env LABEL_STUDIO_URL)
            api_key: API key (default: from env LABEL_STUDIO_API_KEY)
        """
        load_dotenv()

        self.url = url or os.environ.get(
            'LABEL_STUDIO_URL',
            f"http://localhost:{os.environ.get('LABEL_STUDIO_PORT', '8080')}"
        )
        self.api_key = api_key or os.environ.get('LABEL_STUDIO_API_KEY')

        if not self.api_key:
            raise ValueError(
                "API key required. Set LABEL_STUDIO_API_KEY env var or pass api_key parameter. "
                "Get your API key from Label Studio > Account & Settings > Access Token"
            )

        # Handle Personal Access Tokens (JWT format starting with 'eyJ')
        # PATs are refresh tokens that must be exchanged for access tokens
        if self.api_key.startswith('eyJ'):
            self.access_token = self._exchange_pat_for_access_token(self.api_key)
            self.auth_header = {"Authorization": f"Bearer {self.access_token}"}
        else:
            # Legacy token - use Token auth
            self.access_token = self.api_key
            self.auth_header = {"Authorization": f"Token {self.api_key}"}

        self.session = requests.Session()
        self.session.headers.update(self.auth_header)

    def _exchange_pat_for_access_token(self, pat: str) -> str:
        """Exchange a Personal Access Token (refresh token) for a short-lived access token."""
        response = requests.post(
            f"{self.url}/api/token/refresh",
            headers={"Content-Type": "application/json"},
            json={"refresh": pat}
        )
        response.raise_for_status()
        return response.json()['access']

    def _request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make an authenticated request to the Label Studio API."""
        url = f"{self.url}{endpoint}"
        response = self.session.request(method, url, **kwargs)
        response.raise_for_status()
        return response

    def create_project(
        self,
        name: str,
        labeling_config_path: str,
        description: str = ""
    ) -> int:
        """
        Create a new Label Studio project.

        Args:
            name: Project name
            labeling_config_path: Path to labeling_config.xml
            description: Optional project description

        Returns:
            Project ID
        """
        with open(labeling_config_path, 'r') as f:
            labeling_config = f.read()

        response = self._request(
            "POST",
            "/api/projects",
            json={
                "title": name,
                "label_config": labeling_config,
                "description": description
            }
        )

        return response.json()['id']

    def configure_ml_backend(
        self,
        project_id: int,
        ml_backend_url: str,
        title: str = "Tesseract OCR"
    ) -> int:
        """
        Connect an ML backend to a project with interactive predictions enabled.

        Args:
            project_id: Project ID
            ml_backend_url: URL of the ML backend
            title: Display name for the ML backend

        Returns:
            ML backend ID
        """
        response = self._request(
            "POST",
            "/api/ml",
            json={
                "project": project_id,
                "url": ml_backend_url,
                "title": title,
                "is_interactive": True  # Enable auto-predictions when opening tasks
            }
        )

        return response.json()['id']

    def configure_webhook(
        self,
        project_id: int,
        webhook_url: str,
        actions: Optional[List[str]] = None
    ) -> int:
        """
        Set up a webhook for annotation events.

        Args:
            project_id: Project ID
            webhook_url: URL to receive webhooks
            actions: List of actions to trigger webhook (default: ANNOTATION_CREATED, ANNOTATION_UPDATED)

        Returns:
            Webhook ID
        """
        if actions is None:
            actions = ['ANNOTATION_CREATED', 'ANNOTATION_UPDATED']

        response = self._request(
            "POST",
            "/api/webhooks",
            json={
                "url": webhook_url,
                "project": project_id,
                "send_payload": True,
                "send_for_all_actions": False,
                "actions": actions
            }
        )

        return response.json()['id']

    def create_task(
        self,
        project_id: int,
        image_path: str
    ) -> int:
        """
        Create a task with an image.

        Args:
            project_id: Project ID
            image_path: Path or URL to the image

        Returns:
            Task ID
        """
        response = self._request(
            "POST",
            f"/api/projects/{project_id}/import",
            json=[{"image": image_path}]
        )

        return response.json()[0]['id']

    def create_tasks_from_directory(
        self,
        project_id: int,
        directory: str,
        extensions: Optional[List[str]] = None
    ) -> List[int]:
        """
        Create tasks for all images in a directory.

        Args:
            project_id: Project ID
            directory: Path to directory containing images
            extensions: File extensions to include (default: jpg, jpeg, png)

        Returns:
            List of task IDs
        """
        if extensions is None:
            extensions = ['.jpg', '.jpeg', '.png']

        # Find all image files
        tasks_data = []
        filenames = []
        for filename in sorted(os.listdir(directory)):
            ext = os.path.splitext(filename)[1].lower()
            if ext in extensions:
                # Use local file serving path
                tasks_data.append({
                    "image": f"/data/local-files/?d=images/{filename}"
                })
                filenames.append(filename)

        if not tasks_data:
            return []

        # Get existing task count
        existing_tasks = self._request("GET", f"/api/projects/{project_id}/tasks").json()
        existing_count = len(existing_tasks)

        # Import new tasks
        response = self._request(
            "POST",
            f"/api/projects/{project_id}/import",
            json=tasks_data
        )
        import_result = response.json()
        new_count = import_result.get('task_count', 0)

        # Get the newly created task IDs
        all_tasks = self._request("GET", f"/api/projects/{project_id}/tasks").json()
        # Sort by ID descending to get newest first, then take the new ones
        all_tasks_sorted = sorted(all_tasks, key=lambda t: t['id'], reverse=True)
        new_task_ids = [t['id'] for t in all_tasks_sorted[:new_count]]

        return new_task_ids

    def get_projects(self) -> List[dict]:
        """Get all projects."""
        response = self._request("GET", "/api/projects")
        return response.json().get('results', [])

    def get_annotations(
        self,
        project_id: int,
        only_completed: bool = True
    ) -> List[dict]:
        """
        Get annotations for a project.

        Args:
            project_id: Project ID
            only_completed: Only return completed annotations

        Returns:
            List of annotations
        """
        response = self._request("GET", f"/api/projects/{project_id}/tasks")
        tasks = response.json()

        annotations = []
        for task in tasks:
            if only_completed and not task.get('annotations'):
                continue
            for annotation in task.get('annotations', []):
                annotations.append({
                    'task_id': task['id'],
                    'annotation_id': annotation['id'],
                    'result': annotation['result'],
                    'created_at': annotation.get('created_at')
                })

        return annotations

    def trigger_predictions(self, project_id: int, ml_backend_id: int):
        """
        Trigger ML backend predictions for all tasks in a project.

        Args:
            project_id: Project ID
            ml_backend_id: ML backend ID
        """
        self._request("POST", f"/api/ml/{ml_backend_id}/predict")

    def configure_local_storage(
        self,
        project_id: int,
        path: str,
        title: str = "Local Images"
    ) -> int:
        """
        Configure local file storage for a project.

        Args:
            project_id: Project ID
            path: Path to local files inside the container
            title: Display name for the storage

        Returns:
            Storage ID
        """
        response = self._request(
            "POST",
            "/api/storages/localfiles",
            json={
                "project": project_id,
                "title": title,
                "path": path,
                "use_blob_urls": True
            }
        )

        storage_id = response.json()['id']

        # Sync the storage to make files available
        self._request("POST", f"/api/storages/localfiles/{storage_id}/sync")

        return storage_id
