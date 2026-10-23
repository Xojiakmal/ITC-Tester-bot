import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from aiogram.fsm.storage.base import StorageKey
from app.models.user import User
from app.services.question_service import QuestionService
from app.bot.fsm_storage import DatabaseFsmStorage


@pytest.mark.asyncio
async def test_csv_import_success_and_validation(
    db_session: AsyncSession, user_a: User
):
    csv_text = (
        "question,option1,option2,option3,option4,correct_option,explanation,set_name\n"
        "What is asyncio in Python?,Library for async IO,Graphics library,Database engine,Audio player,1,asyncio is an async IO library,Python Basics\n"
        "Which keyword defines a function?,def,func,fn,define,1,def defines a function in Python,Python Basics\n"
        "What is the output of 2**3?,6,8,9,5,2,2 to the power of 3 is 8,Math\n"
    )

    imported_count, err = await QuestionService.import_questions_from_csv(
        session=db_session,
        owner_id=user_a.id,
        csv_content=csv_text,
    )

    assert err is None
    assert imported_count == 3

    # Check imported questions and created sets
    questions, total = await QuestionService.get_user_questions(
        session=db_session, owner_id=user_a.id
    )
    assert total == 3

    sets = await QuestionService.get_user_sets(db_session, user_a.id)
    set_names = {s.name for s in sets}
    assert "Python Basics" in set_names
    assert "Math" in set_names


@pytest.mark.asyncio
async def test_csv_import_malformed_handling(
    db_session: AsyncSession, user_a: User
):
    bad_csv = (
        "question,option1,correct_option\n"
        "Short question,OnlyOneOption,1\n"
    )
    count, err = await QuestionService.import_questions_from_csv(
        session=db_session,
        owner_id=user_a.id,
        csv_content=bad_csv,
    )
    assert err is not None
    assert "yetarli emas" in err


@pytest.mark.asyncio
async def test_fsm_database_persistence_across_restarts(test_engine):
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    storage_1 = DatabaseFsmStorage(session_factory=session_factory)
    key = StorageKey(bot_id=123, chat_id=99999, user_id=99999)

    # User in Step 2 of registration / quiz creation
    await storage_1.set_state(key, "AddQuestionStates:waiting_for_options")
    await storage_1.set_data(key, {"q_text": "What is 2+2?", "draft_id": 42})
    await storage_1.close()

    # Simulate bot restart: new DatabaseFsmStorage instance created
    storage_2 = DatabaseFsmStorage(session_factory=session_factory)
    recovered_state = await storage_2.get_state(key)
    recovered_data = await storage_2.get_data(key)
    await storage_2.close()

    assert recovered_state == "AddQuestionStates:waiting_for_options"
    assert recovered_data.get("q_text") == "What is 2+2?"
    assert recovered_data.get("draft_id") == 42
