import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from endpoints.backlog import delete_backlog_task
from interfaces.document import DocumentType
from interfaces.state import FullState
from keyboards import BacklogSelectDelete
from memory.documents import Documents
from memory.memory import Memory


class BacklogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.original_data_dir = Memory.DATA_DIR
        Memory.DATA_DIR = Path(self.directory.name) / ".data"
        state = Memory("state.json", FullState)
        state.data.bot_dialog_message_id = 42
        state.save()

    def tearDown(self) -> None:
        Memory.DATA_DIR = self.original_data_dir
        self.directory.cleanup()

    def test_delete_backlog_task_removes_document(self) -> None:
        document = Documents().create(
            {"name": "Delete me"},
            type_hint=DocumentType.TASK_MODEL,
        )
        callback = AsyncMock()

        with patch("endpoints.backlog.render_menu", new=AsyncMock()) as render:
            asyncio.run(
                delete_backlog_task(
                    callback,
                    BacklogSelectDelete(uuid=document.uuid),
                    AsyncMock(),
                )
            )

        self.assertEqual(
            Documents().get_list(type=DocumentType.TASK_MODEL), []
        )
        self.assertIn("deleted from backlog", render.await_args.args[2])
        callback.answer.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
