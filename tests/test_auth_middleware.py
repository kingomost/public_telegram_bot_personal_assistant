import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from aiogram.types import CallbackQuery, Message

import config
from middlewares.auth_middleware import AuthMiddleware


class AuthMiddlewareTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.owner_id = 123456789
        owner_patch = patch.object(config, "OWNER_ID", self.owner_id)
        owner_patch.start()
        self.addCleanup(owner_patch.stop)
        self.middleware = AuthMiddleware()

    async def test_owner_message_reaches_handler(self) -> None:
        event = Mock(spec=Message)
        event.from_user = SimpleNamespace(id=self.owner_id)
        handler = AsyncMock(return_value="handled")

        result = await self.middleware(handler, event, {})

        self.assertEqual(result, "handled")
        handler.assert_awaited_once_with(event, {})

    async def test_non_owner_message_is_rejected(self) -> None:
        event = Mock(spec=Message)
        event.from_user = SimpleNamespace(id=self.owner_id + 1)
        event.reply = AsyncMock()
        handler = AsyncMock()

        result = await self.middleware(handler, event, {})

        self.assertIsNone(result)
        handler.assert_not_awaited()
        event.reply.assert_not_awaited()

    async def test_non_owner_callback_is_rejected(self) -> None:
        event = Mock(spec=CallbackQuery)
        event.from_user = SimpleNamespace(id=self.owner_id + 1)
        event.answer = AsyncMock()
        handler = AsyncMock()

        result = await self.middleware(handler, event, {})

        self.assertIsNone(result)
        handler.assert_not_awaited()
        event.answer.assert_awaited_once_with()

    async def test_event_without_user_is_rejected(self) -> None:
        event = Mock()
        event.from_user = None
        handler = AsyncMock()

        result = await self.middleware(handler, event, {})

        self.assertIsNone(result)
        handler.assert_not_awaited()
