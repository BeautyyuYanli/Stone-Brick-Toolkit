from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from stone_brick.backend.ctx import Ctx
from stone_brick.oauth_login.providers.common import UserInfo


class User(SQLModel, table=True):
    """User model to store user information"""

    id: UUID = Field(default_factory=uuid4, primary_key=True, exclude=True)
    email: str = Field(unique=True, index=True)
    name: str | None = None
    photo_url: str | None = None


async def create_user_if_not_exists(ctx: Ctx, user_info: UserInfo) -> User:
    async with AsyncSession(ctx.resource.db) as db:
        # Check if user exists
        user = (
            await db.exec(select(User).where(User.email == user_info.email))
        ).one_or_none()

        if not user:
            # Create new user if doesn't exist
            user = User.model_validate(user_info, from_attributes=True)
            db.add(user)
            await db.commit()
            await db.refresh(user)

        return user
