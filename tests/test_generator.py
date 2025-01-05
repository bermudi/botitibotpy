import unittest
import os
import shutil
from unittest.mock import MagicMock, patch
from src.content.generator import ContentGenerator
from llama_index.core import VectorStoreIndex

class TestContentGenerator(unittest.TestCase):
    def setUp(self):
        self.content_generator = ContentGenerator()
        # Mock the chroma_collection to control its behavior
        self.content_generator.chroma_collection = MagicMock()
        # Mock the index to track insert calls
        self.content_generator.index = MagicMock()

    def tearDown(self):
        if hasattr(self, 'test_dir') and os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    @patch('src.content.generator.VectorStoreIndex.from_documents')
    def test_load_content_source_new_index(self, mock_from_documents):
        # Arrange
        self.content_generator.index = None
        self.test_dir = "test_content_dir"
        os.makedirs(self.test_dir, exist_ok=True)
        with open(os.path.join(self.test_dir, "test_doc.txt"), "w") as f:
            f.write("Test content")

        # Set up mock behavior
        self.content_generator.chroma_collection.count.return_value = 0
        mock_from_documents.return_value = MagicMock()
        # Act
        result = self.content_generator.load_content_source(self.test_dir)

        # Assert
        self.assertTrue(result)
        self.assertEqual(self.content_generator.chroma_collection.count(), 0)
        mock_from_documents.assert_called_once()

    def test_load_index_existing(self):
        # Arrange
        self.content_generator.chroma_collection.count = lambda: 1  # Mock non-empty collection
        self.content_generator.vector_store = MagicMock()
        VectorStoreIndex.from_vector_store = MagicMock(return_value="mocked_index")

        # Act
        result = self.content_generator.load_index()

        # Assert
        self.assertTrue(result)
        self.assertEqual(self.content_generator.index, "mocked_index")
        VectorStoreIndex.from_vector_store.assert_called_once_with(
            self.content_generator.vector_store,
            embed_model=self.content_generator.embed_model
        )


    @patch('src.content.generator.VectorStoreIndex.from_documents')
    def test_load_content_source_update_index(self, mock_from_documents):
        # Arrange
        self.test_dir = "test_content_dir"
        os.makedirs(self.test_dir, exist_ok=True)
        with open(os.path.join(self.test_dir, "test_doc.txt"), "w") as f:
            f.write("Initial content")

        # Initial load
        self.content_generator.load_content_source(self.test_dir)

        # Modify existing file and add new file
        with open(os.path.join(self.test_dir, "test_doc.txt"), "w") as f:
            f.write("Modified content")
        with open(os.path.join(self.test_dir, "new_doc.txt"), "w") as f:
            f.write("New content")

        # Reset mock calls
        self.content_generator.index.insert.reset_mock()
        # Act - Reload content
        result = self.content_generator.load_content_source(self.test_dir)

        # Assert
        self.assertTrue(result)
        self.assertEqual(self.content_generator.index.insert.call_count, 2)

if __name__ == '__main__':
    unittest.main()
