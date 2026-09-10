import uuid
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_conversation import ChatConversation
from app.models.chat_message import ChatMessage


class ChatHistoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_conversation(
        self, user_id: uuid.UUID, business_date: date
    ) -> ChatConversation | None:
        return await self.session.scalar(
            select(ChatConversation).where(
                ChatConversation.user_id == user_id,
                ChatConversation.business_date == business_date,
            )
        )

    async def create_conversation(
        self, user_id: uuid.UUID, business_date: date, expires_at: datetime
    ) -> ChatConversation:
        conversation = ChatConversation(
            user_id=user_id,
            business_date=business_date,
            expires_at=expires_at,
        )
        self.session.add(conversation)
        await self.session.flush()
        return conversation

    async def list_messages(self, conversation_id: uuid.UUID) -> list[ChatMessage]:
        statement = (
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conversation_id)
            .order_by(ChatMessage.sequence_number)
        )
        return list((await self.session.scalars(statement)).all())

    async def get_turn_by_client_message_id(
        self, user_id: uuid.UUID, business_date: date, client_message_id: uuid.UUID
    ) -> tuple[ChatConversation, list[ChatMessage]] | None:
        user_message = await self.session.scalar(
            select(ChatMessage)
            .join(ChatConversation)
            .where(
                ChatConversation.user_id == user_id,
                ChatConversation.business_date == business_date,
                ChatMessage.client_message_id == client_message_id,
            )
        )
        if user_message is None:
            return None
        conversation = await self.session.get(ChatConversation, user_message.conversation_id)
        if conversation is None:
            return None
        messages = list(
            (
                await self.session.scalars(
                    select(ChatMessage)
                    .where(
                        ChatMessage.conversation_id == user_message.conversation_id,
                        ChatMessage.sequence_number.in_(
                            [user_message.sequence_number, user_message.sequence_number + 1]
                        ),
                    )
                    .order_by(ChatMessage.sequence_number)
                )
            ).all()
        )
        return conversation, messages

    async def next_sequence_number(self, conversation_id: uuid.UUID) -> int:
        highest = await self.session.scalar(
            select(func.max(ChatMessage.sequence_number)).where(
                ChatMessage.conversation_id == conversation_id
            )
        )
        return (highest or 0) + 1

    async def create_turn(
        self,
        conversation_id: uuid.UUID,
        sequence_number: int,
        client_message_id: uuid.UUID,
        query: str,
        answer: str,
    ) -> list[ChatMessage]:
        messages = [
            ChatMessage(
                conversation_id=conversation_id,
                client_message_id=client_message_id,
                role="user",
                content=query,
                sequence_number=sequence_number,
            ),
            ChatMessage(
                conversation_id=conversation_id,
                role="assistant",
                content=answer,
                sequence_number=sequence_number + 1,
            ),
        ]
        self.session.add_all(messages)
        await self.session.flush()
        return messages
