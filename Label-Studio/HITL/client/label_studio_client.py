# HITL/client/label_studio_client.py
"""Label Studio SDK client wrapper for HITL OCR workflow."""

import os
from typing import List, Optional

from dotenv import load_dotenv
from label_studio_sdk import Client


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

        self.client = Client(url=self.url, api_key=self.api_key)

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

        project = self.client.start_project(
            title=name,
            label_config=labeling_config,
            description=description
        )

        return project.id

    def configure_ml_backend(
        self,
        project_id: int,
        ml_backend_url: str,
        title: str = "Tesseract OCR"
    ) -> int:
        """
        Connect an ML backend to a project.

        Args:
            project_id: Project ID
            ml_backend_url: URL of the ML backend
            title: Display name for the ML backend

        Returns:
            ML backend ID
        """
        project = self.client.get_project(project_id)

        ml_backend = project.connect_ml_backend(
            url=ml_backend_url,
            title=title
        )

        return ml_backend.id

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

        project = self.client.get_project(project_id)

        # Use the webhooks API directly
        import requests
        response = requests.post(
            f"{self.url}/api/webhooks",
            headers={"Authorization": f"Token {self.api_key}"},
            json={
                "url": webhook_url,
                "project": project_id,
                "send_payload": True,
                "send_for_all_actions": False,
                "actions": actions
            }
        )
        response.raise_for_status()

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
        project = self.client.get_project(project_id)

        task = project.import_tasks([
            {"image": image_path}
        ])

        return task[0]['id']

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

        project = self.client.get_project(project_id)

        # Find all image files
        tasks_data = []
        for filename in os.listdir(directory):
            ext = os.path.splitext(filename)[1].lower()
            if ext in extensions:
                # Use local file serving path
                tasks_data.append({
                    "image": f"/data/local-files/?d=images/{filename}"
                })

        if not tasks_data:
            return []

        tasks = project.import_tasks(tasks_data)
        return [t['id'] for t in tasks]

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
        project = self.client.get_project(project_id)

        tasks = project.get_labeled_tasks() if only_completed else project.get_tasks()

        annotations = []
        for task in tasks:
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
        import requests
        response = requests.post(
            f"{self.url}/api/ml/{ml_backend_id}/predict",
            headers={"Authorization": f"Token {self.api_key}"}
        )
        response.raise_for_status()
