import vertexai
from google.cloud import aiplatform
from vertexai.language_models import TextEmbeddingModel
from vertexai.preview.generative_models import GenerativeModel

class VertexAI:
    def __init__(self, project_id: str, location: str):
        aiplatform.init(project=project_id, location=location)

    def get_embeddings(self, texts: list):
        """
        Gets embeddings for a list of texts.

        Args:
            texts: A list of strings to get embeddings for.

        Returns:
            A list of embeddings.
        """
        print(f"VertexAI: Getting embeddings for {len(texts)} texts using text-embedding-004 model")
        model = TextEmbeddingModel.from_pretrained("text-embedding-004")
        embeddings = model.get_embeddings(texts)
        return [embedding.values for embedding in embeddings]

    def generate_text(self, prompt: str):
        """
        Generates text using a large language model.

        Args:
            prompt: The prompt to use for text generation.

        Returns:
            The generated text.
        """
        print(f"VertexAI: Generating text for prompt using gemini-2.0-flash-001 model")
        model = GenerativeModel("gemini-2.0-flash-001")
        response = model.generate_content(prompt)
        return response.text
