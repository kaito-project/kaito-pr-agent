import base64
from unittest.mock import MagicMock, patch

import pytest

from pr_agent.algo.types import EDIT_TYPE
from pr_agent.tools.pr_rag_engine import PRRagEngine


def test_documents():
    return [
        {
            "doc_id": "doc1",
            "text": "print('hello')",
            "metadata": {
                "file_name": "test_file.py",
                "language": "python",
                "split_type": "code",
            }
        },
        {
            "doc_id": "doc2",
            "text": "print('for modify')",
            "metadata": {
                "file_name": "mod.py",
                "language": "python",
                "split_type": "code",
            }
        },
        {
            "doc_id": "doc3",
            "text": "print('for delete')",
            "metadata": {
                "file_name": "del.py",
                "language": "python",
                "split_type": "code",
            }
        }
    ]

@pytest.fixture
def mock_rag_client():
    client = MagicMock()
    client.list_indexes.return_value = ["owner_repo_main", "owner_repo_feature_test"]
    client.delete_index.return_value = {"status": "deleted"}
    client.index_documents.return_value = {"status": "success"}
    client.update_documents.return_value = {"status": "updated"}
    client.delete_documents.return_value = {"status": "deleted"}
    client.list_documents.return_value = {"documents": test_documents()}
    client.persist_index.return_value = {"status": "persisted"}
    client.load_index.return_value = {"status": "loaded"}
    return client

@pytest.fixture
def mock_git_provider():
    provider = MagicMock()
    provider.repo = "owner/repo"
    provider.get_pr_branch.return_value = "feature/test"
    provider.repo_obj.default_branch = "main"
    provider.repo_obj.get_branch.return_value = MagicMock(commit=MagicMock(sha="sha123"))
    provider.repo_obj.get_git_tree.return_value.tree = [MagicMock(path="test_file.py", mode="100644", type="blob")]
    provider.repo_obj.get_git_blob.return_value.content = base64.encodebytes(b"print('hello world')")
    provider.get_diff_files.return_value = [MagicMock(
        filename="test_file.py",
        head_file="print('hello world')",
        edit_type=EDIT_TYPE.MODIFIED,
    )]
    provider.pr.base.ref = "main"
    provider.get_pr_file_content.return_value = "print('hello world')"
    return provider

def test_create_new_pr_index_with_diff_files(mock_rag_client, mock_git_provider):
    engine = PRRagEngine("http://fake-url")
    engine.rag_client = mock_rag_client

    # Patch index_name creation
    with patch.object(engine, '_get_git_provider', return_value=mock_git_provider):
        engine.create_new_pr_index("http://pr-url")
        mock_rag_client.persist_index.assert_called_once()
        mock_rag_client.load_index.assert_called_once()
        mock_rag_client.list_documents.assert_called_once()
        args, kwargs = mock_rag_client.list_documents.call_args
        assert args[0] == "owner_repo_feature_test"
        assert kwargs == {"metadata_filter": {"file_name": "test_file.py"}}
        mock_rag_client.update_documents.assert_called_once()
        args, kwargs = mock_rag_client.update_documents.call_args
        assert args[0] == "owner_repo_feature_test"
        assert args[1][0]["metadata"]["file_name"] == "test_file.py"
        assert args[1][0]["metadata"]["language"] == "python"
        assert args[1][0]["metadata"]["split_type"] == "code"

def test_update_index_add_modify_delete(mock_rag_client, mock_git_provider):
    engine = PRRagEngine("http://fake-url")
    engine.rag_client = mock_rag_client

    mock_git_provider.get_diff_files.return_value = [
        MagicMock(
            filename="added.py",
            head_file="print('added')",
            edit_type=EDIT_TYPE.ADDED,
        ),
        MagicMock(
            filename="mod.py",
            head_file="print('mod')",
            edit_type=EDIT_TYPE.MODIFIED,
        ),
        MagicMock(
            filename="del.py",
            head_file="print('del')",
            edit_type=EDIT_TYPE.DELETED,
        ),
    ]


    # Patch index name
    with patch.object(engine, '_get_git_provider', return_value=mock_git_provider):
        engine.update_pr_index("http://pr-url")
        mock_rag_client.index_documents.assert_called_once()
        mock_rag_client.update_documents.assert_called_once()
        mock_rag_client.delete_documents.assert_called_once()

def test_create_new_base_index(mock_rag_client, mock_git_provider):
    mock_rag_client.list_indexes.return_value = []
    engine = PRRagEngine("http://fake-url")
    engine.rag_client = mock_rag_client
    with patch.object(engine, '_get_git_provider', return_value=mock_git_provider):
        engine.create_base_branch_index("http://pr-url")
        mock_rag_client.list_indexes.assert_called_once()
        mock_rag_client.index_documents.assert_called_once()
        args, kwargs = mock_rag_client.index_documents.call_args
        assert args[0] == "owner_repo_main"
        assert args[1][0]["text"] == "print('hello world')"
        assert args[1][0]["metadata"]["file_name"] == "test_file.py"
        assert args[1][0]["metadata"]["language"] == "python"
        assert args[1][0]["metadata"]["split_type"] == "code"

def test_delete_pr_index(mock_rag_client, mock_git_provider):
    engine = PRRagEngine("http://fake-url")
    engine.rag_client = mock_rag_client

    with patch.object(engine, '_get_git_provider', return_value=mock_git_provider):
        engine.delete_pr_index("http://pr-url")
        mock_rag_client.list_indexes.assert_called_once()
        mock_rag_client.delete_index.assert_called_once()
        args, kwargs = mock_rag_client.delete_index.call_args
        assert args[0] == "owner_repo_feature_test"
