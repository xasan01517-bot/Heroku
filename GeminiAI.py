# scope: requires google-genai
import os

from google import genai
from herokutl.tl.types import User

from .. import loader


@loader.tds
class GeminiAIMod(loader.Module):
    """AI автоответчик на Gemini."""

    strings = {
        "name": "GeminiAI",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "enabled",
                False,
                lambda: "Включить AI-автоответчик",
                validator=loader.validators.Boolean(),
            ),
        )
        self.replied_users = set()
        self.client = None

    async def client_ready(self, client, db):
        self.client = client

        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            return

        self.gemini = genai.Client(api_key=api_key)

        saved = self.get("replied_users", [])

        if isinstance(saved, list):
            self.replied_users = set(str(x) for x in saved)

    def _save(self):
        self.set("replied_users", list(self.replied_users))

    async def watcher(self, message):
        if not self.config["enabled"]:
            return

        if message.out:
            return

        if not message.is_private:
            return

        sender = await message.get_sender()

        if not isinstance(sender, User):
            return

        if getattr(sender, "bot", False):
            return

        user_id = str(sender.id)

        if user_id in self.replied_users:
            return

        if self.client is None or not hasattr(self, "gemini"):
            return

        text = getattr(message, "text", None)

        if not text:
            return

        try:
            prompt = (
                "Ты — дружелюбный AI-помощник в Telegram. "
                "Отвечай естественно, коротко и по делу. "
                "Не говори, что ты человек.\n\n"
                f"Сообщение пользователя:\n{text}"
            )

            response = self.gemini.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )

            answer = getattr(response, "text", None)

            if not answer:
                return

            await message.reply(answer)

            self.replied_users.add(user_id)
            self._save()

        except Exception:
            return

    @loader.command()
    async def aion(self, message):
        """Включить AI."""
        self.config["enabled"] = True
        await self.client.send_message(
            message.chat_id,
            "🤖 Gemini AI включён."
        )

    @loader.command()
    async def aioff(self, message):
        """Выключить AI."""
        self.config["enabled"] = False
        await self.client.send_message(
            message.chat_id,
            "🔴 Gemini AI выключен."
        )

    @loader.command()
    async def aistatus(self, message):
        """Показать статус AI."""
        enabled = self.config["enabled"]

        await self.client.send_message(
            message.chat_id,
            "🤖 <b>Gemini AI</b>\n\n"
            f"Состояние: {'🟢 включён' if enabled else '🔴 выключен'}\n"
            f"Ответов отправлено: {len(self.replied_users)}"
        )

    @loader.command()
    async def aireset(self, message):
        """Разрешить AI снова отвечать всем пользователям."""
        self.replied_users.clear()
        self._save()

        await self.client.send_message(
            message.chat_id,
            "♻️ Список пользователей очищен. AI снова сможет ответить им."
        )
