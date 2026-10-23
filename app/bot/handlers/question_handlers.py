import math
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, Document
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from app.locales.uz import t
from app.models.user import User
from app.services.question_service import QuestionService
from app.bot.keyboards import (
    get_questions_menu_keyboard,
    get_questions_list_keyboard,
    get_question_detail_keyboard,
    get_options_select_keyboard,
    get_skip_keyboard,
    get_sets_picker_keyboard,
    get_sets_list_keyboard,
    get_set_detail_keyboard,
    get_cancel_keyboard,
    get_start_keyboard,
)

router = Router(name="question_router")

PAGE_SIZE = 5


class AddQuestionStates(StatesGroup):
    waiting_for_text = State()
    waiting_for_options = State()
    waiting_for_correct = State()
    waiting_for_explanation = State()
    waiting_for_set = State()


class SearchQuestionStates(StatesGroup):
    waiting_for_query = State()


class CreateSetStates(StatesGroup):
    waiting_for_name = State()


class CsvImportStates(StatesGroup):
    waiting_for_file = State()


@router.callback_query(F.data == "cab:questions")
async def show_questions_menu(
    callback: CallbackQuery, state: FSMContext, user: User | None, db_session: AsyncSession
):
    if not user:
        await callback.answer(t("login_invalid_credentials"), show_alert=True)
        return

    await state.clear()
    q_count = await QuestionService.count_user_questions(db_session, user.id)
    s_count = await QuestionService.count_user_sets(db_session, user.id)

    await callback.message.edit_text(
        t("questions_menu_title", questions_count=q_count, sets_count=s_count),
        reply_markup=get_questions_menu_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


# --- Add Question Flow ---
@router.callback_query(F.data == "q:add")
async def start_add_question(callback: CallbackQuery, state: FSMContext, user: User | None):
    if not user:
        await callback.answer(t("login_invalid_credentials"), show_alert=True)
        return

    await state.set_state(AddQuestionStates.waiting_for_text)
    await callback.message.edit_text(
        t("add_q_enter_text"),
        reply_markup=get_cancel_keyboard(),
    )
    await callback.answer()


@router.message(AddQuestionStates.waiting_for_text, F.text, F.chat.type == "private")
async def process_q_text(message: Message, state: FSMContext, user: User | None):
    if not user:
        await message.answer(t("login_invalid_credentials"), reply_markup=get_start_keyboard())
        return

    text = message.text.strip()
    if not (1 <= len(text) <= 300):
        await message.answer(t("add_q_text_too_long"), reply_markup=get_cancel_keyboard())
        return

    await state.update_data(q_text=text)
    await state.set_state(AddQuestionStates.waiting_for_options)
    await message.answer(t("add_q_enter_options"), reply_markup=get_cancel_keyboard())


@router.message(AddQuestionStates.waiting_for_options, F.text, F.chat.type == "private")
async def process_q_options(message: Message, state: FSMContext, user: User | None):
    if not user:
        await message.answer(t("login_invalid_credentials"), reply_markup=get_start_keyboard())
        return

    raw_lines = [line.strip() for line in message.text.splitlines() if line.strip()]
    if not (2 <= len(raw_lines) <= 10) or any(len(line) > 100 for line in raw_lines):
        await message.answer(t("add_q_options_invalid"), reply_markup=get_cancel_keyboard())
        return

    await state.update_data(q_options=raw_lines)
    await state.set_state(AddQuestionStates.waiting_for_correct)

    options_preview = "\n".join(f"{i+1}. {opt}" for i, opt in enumerate(raw_lines))
    await message.answer(
        t("add_q_select_correct") + f"\n\n{options_preview}",
        reply_markup=get_options_select_keyboard(len(raw_lines)),
    )


@router.callback_query(AddQuestionStates.waiting_for_correct, F.data.startswith("q:opt:"))
async def process_q_correct(callback: CallbackQuery, state: FSMContext, user: User | None):
    if not user:
        await callback.answer(t("login_invalid_credentials"), show_alert=True)
        return

    opt_idx = int(callback.data.split(":")[2])
    await state.update_data(q_correct=opt_idx)
    await state.set_state(AddQuestionStates.waiting_for_explanation)

    await callback.message.edit_text(
        t("add_q_enter_explanation"),
        reply_markup=get_skip_keyboard(skip_cb="q:skip_expl"),
    )
    await callback.answer()


@router.callback_query(AddQuestionStates.waiting_for_explanation, F.data == "q:skip_expl")
async def skip_q_explanation(
    callback: CallbackQuery, state: FSMContext, user: User | None, db_session: AsyncSession
):
    if not user:
        await callback.answer(t("login_invalid_credentials"), show_alert=True)
        return

    await state.update_data(q_explanation="")
    await proceed_to_set_selection(callback.message, state, user, db_session)
    await callback.answer()


@router.message(AddQuestionStates.waiting_for_explanation, F.text, F.chat.type == "private")
async def process_q_explanation(
    message: Message, state: FSMContext, user: User | None, db_session: AsyncSession
):
    if not user:
        await message.answer(t("login_invalid_credentials"), reply_markup=get_start_keyboard())
        return

    explanation = message.text.strip()
    if len(explanation) > 200:
        await message.answer(t("add_q_explanation_too_long"), reply_markup=get_cancel_keyboard())
        return

    await state.update_data(q_explanation=explanation)
    await proceed_to_set_selection(message, state, user, db_session)


async def proceed_to_set_selection(
    message: Message, state: FSMContext, user: User, db_session: AsyncSession
):
    await state.set_state(AddQuestionStates.waiting_for_set)
    sets = await QuestionService.get_user_sets(db_session, user.id)
    await message.answer(
        t("add_q_select_set"),
        reply_markup=get_sets_picker_keyboard(sets, none_cb="q:set:none"),
    )


@router.callback_query(AddQuestionStates.waiting_for_set, F.data.startswith("q:set:"))
async def process_q_set(
    callback: CallbackQuery, state: FSMContext, user: User | None, db_session: AsyncSession
):
    if not user:
        await callback.answer(t("login_invalid_credentials"), show_alert=True)
        return

    set_id_raw = callback.data.split(":")[2]
    test_set_id = None if set_id_raw == "none" else set_id_raw

    data = await state.get_data()
    q_text = data.get("q_text")
    q_options = data.get("q_options")
    q_correct = data.get("q_correct")
    q_expl = data.get("q_explanation", "")

    question, err = await QuestionService.create_question(
        session=db_session,
        owner_id=user.id,
        text=q_text,
        options=q_options,
        correct_option_id=q_correct,
        explanation=q_expl,
        test_set_id=test_set_id,
    )

    await state.clear()
    if err:
        await callback.message.edit_text(t(err), reply_markup=get_questions_menu_keyboard())
    else:
        await callback.message.edit_text(t("add_q_success"), reply_markup=get_questions_menu_keyboard())
    await callback.answer()


# --- Questions List & Pagination ---
@router.callback_query(F.data.startswith("q:list:"))
async def list_questions(
    callback: CallbackQuery, user: User | None, db_session: AsyncSession
):
    if not user:
        await callback.answer(t("login_invalid_credentials"), show_alert=True)
        return

    page = int(callback.data.split(":")[2])
    questions, total = await QuestionService.get_user_questions(
        session=db_session, owner_id=user.id, page=page, page_size=PAGE_SIZE
    )

    total_pages = max(1, math.ceil(total / PAGE_SIZE))

    header = t("questions_list_header", page=page, total_pages=total_pages)
    if not questions:
        header += "Savollar mavjud emas."

    await callback.message.edit_text(
        header,
        reply_markup=get_questions_list_keyboard(questions, page, total_pages),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("q:v:"))
async def view_question_detail(
    callback: CallbackQuery, user: User | None, db_session: AsyncSession
):
    if not user:
        await callback.answer(t("login_invalid_credentials"), show_alert=True)
        return

    question_id = callback.data[4:]
    question = await QuestionService.get_question_by_id(db_session, question_id, user.id)
    if not question:
        await callback.answer("Savol topilmadi.", show_alert=True)
        return

    options_formatted = "\n".join(
        f"{i+1}. {opt} {'(To\'g\'ri)' if i == question.correct_option_id else ''}"
        for i, opt in enumerate(question.options)
    )
    set_name = question.test_set.name if question.test_set else "Umumiy"
    correct_text = question.options[question.correct_option_id]

    text = t(
        "question_detail",
        text=question.text,
        options_text=options_formatted,
        correct_option=correct_text,
        explanation=question.explanation or "Mavjud emas",
        set_name=set_name,
    )

    await callback.message.edit_text(
        text,
        reply_markup=get_question_detail_keyboard(question.id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("q:del:"))
async def delete_question_handler(
    callback: CallbackQuery, user: User | None, db_session: AsyncSession
):
    if not user:
        await callback.answer(t("login_invalid_credentials"), show_alert=True)
        return

    question_id = callback.data[6:]
    success = await QuestionService.delete_question(db_session, question_id, user.id)
    if success:
        await callback.answer(t("question_deleted"), show_alert=True)
    else:
        await callback.answer("Savol topilmadi.", show_alert=True)

    # Return to questions list page 1
    questions, total = await QuestionService.get_user_questions(
        session=db_session, owner_id=user.id, page=1, page_size=PAGE_SIZE
    )
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    await callback.message.edit_text(
        t("questions_list_header", page=1, total_pages=total_pages),
        reply_markup=get_questions_list_keyboard(questions, 1, total_pages),
        parse_mode="HTML",
    )


# --- Search Questions ---
@router.callback_query(F.data == "q:search")
async def start_search_questions(callback: CallbackQuery, state: FSMContext, user: User | None):
    if not user:
        await callback.answer(t("login_invalid_credentials"), show_alert=True)
        return

    await state.set_state(SearchQuestionStates.waiting_for_query)
    await callback.message.edit_text(
        t("search_enter_query"),
        reply_markup=get_cancel_keyboard(),
    )
    await callback.answer()


@router.message(SearchQuestionStates.waiting_for_query, F.text, F.chat.type == "private")
async def process_search_query(
    message: Message, state: FSMContext, user: User | None, db_session: AsyncSession
):
    if not user:
        await message.answer(t("login_invalid_credentials"), reply_markup=get_start_keyboard())
        return

    query = message.text.strip()
    questions, total = await QuestionService.get_user_questions(
        session=db_session, owner_id=user.id, page=1, page_size=PAGE_SIZE, search_query=query
    )
    await state.clear()
    total_pages = max(1, math.ceil(total / PAGE_SIZE))

    header = f"🔍 <b>Qidiruv natijalari ('{query}'):</b>\n\n"
    if not questions:
        header += "Hech qanday savol topilmadi."

    await message.answer(
        header,
        reply_markup=get_questions_list_keyboard(questions, 1, total_pages, search_query=query),
        parse_mode="HTML",
    )


# --- Test Sets Management ---
@router.callback_query(F.data == "set:list")
async def list_sets(callback: CallbackQuery, user: User | None, db_session: AsyncSession):
    if not user:
        await callback.answer(t("login_invalid_credentials"), show_alert=True)
        return

    sets = await QuestionService.get_user_sets(db_session, user.id)
    text = t("sets_list_title")
    if not sets:
        text += t("sets_empty")
    else:
        for s in sets:
            text += t("set_item", name=s.name, count=len(s.questions))

    await callback.message.edit_text(
        text,
        reply_markup=get_sets_list_keyboard(sets),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "set:add")
async def start_create_set(callback: CallbackQuery, state: FSMContext, user: User | None):
    if not user:
        await callback.answer(t("login_invalid_credentials"), show_alert=True)
        return

    await state.set_state(CreateSetStates.waiting_for_name)
    await callback.message.edit_text(
        t("create_set_enter_name"),
        reply_markup=get_cancel_keyboard(),
    )
    await callback.answer()


@router.message(CreateSetStates.waiting_for_name, F.text, F.chat.type == "private")
async def process_create_set_name(
    message: Message, state: FSMContext, user: User | None, db_session: AsyncSession
):
    if not user:
        await message.answer(t("login_invalid_credentials"), reply_markup=get_start_keyboard())
        return

    name = message.text.strip()
    if not (1 <= len(name) <= 100):
        await message.answer("Nom 1 dan 100 belgiga ega bo'lishi kerak.", reply_markup=get_cancel_keyboard())
        return

    await QuestionService.create_test_set(db_session, user.id, name)
    await state.clear()
    await message.answer(t("create_set_success"), reply_markup=get_questions_menu_keyboard())


@router.callback_query(F.data.startswith("set:v:"))
async def view_set_detail(
    callback: CallbackQuery, user: User | None, db_session: AsyncSession
):
    if not user:
        await callback.answer(t("login_invalid_credentials"), show_alert=True)
        return

    set_id = callback.data[6:]
    test_set = await QuestionService.get_set_by_id(db_session, set_id, user.id)
    if not test_set:
        await callback.answer("To'plam topilmadi.", show_alert=True)
        return

    await callback.message.edit_text(
        t("set_detail", name=test_set.name, description=test_set.description or "Yo'q", count=len(test_set.questions)),
        reply_markup=get_set_detail_keyboard(test_set.id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set:del:"))
async def delete_set_handler(
    callback: CallbackQuery, user: User | None, db_session: AsyncSession
):
    if not user:
        await callback.answer(t("login_invalid_credentials"), show_alert=True)
        return

    set_id = callback.data[8:]
    await QuestionService.delete_test_set(db_session, set_id, user.id)
    await callback.answer(t("set_deleted"), show_alert=True)

    sets = await QuestionService.get_user_sets(db_session, user.id)
    await callback.message.edit_text(
        t("sets_list_title") + (t("sets_empty") if not sets else ""),
        reply_markup=get_sets_list_keyboard(sets),
        parse_mode="HTML",
    )


# --- CSV Import ---
@router.callback_query(F.data == "q:template")
async def send_csv_template(callback: CallbackQuery, user: User | None):
    if not user:
        await callback.answer(t("login_invalid_credentials"), show_alert=True)
        return

    template_code = t("csv_template_text")
    await callback.message.answer(
        f"📄 <b>CSV Shablon nusxasi:</b>\n\n<pre>{template_code}</pre>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "q:import_csv")
async def start_csv_import(callback: CallbackQuery, state: FSMContext, user: User | None):
    if not user:
        await callback.answer(t("login_invalid_credentials"), show_alert=True)
        return

    await state.set_state(CsvImportStates.waiting_for_file)
    await callback.message.edit_text(
        t("csv_import_prompt"),
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(CsvImportStates.waiting_for_file, F.document, F.chat.type == "private")
async def process_csv_document(
    message: Message, state: FSMContext, user: User | None, db_session: AsyncSession
):
    if not user:
        await message.answer(t("login_invalid_credentials"), reply_markup=get_start_keyboard())
        return

    doc: Document = message.document
    if not doc.file_name or not doc.file_name.lower().endswith(".csv"):
        await message.answer("Iltimos, faqat .csv kengaytmali fayl yuboring.", reply_markup=get_cancel_keyboard())
        return

    file_io = await message.bot.download(doc)
    content = file_io.read().decode("utf-8", errors="replace")

    count, err = await QuestionService.import_questions_from_csv(db_session, user.id, content)
    await state.clear()

    if err:
        await message.answer(
            t("csv_import_error", error=err),
            reply_markup=get_questions_menu_keyboard(),
            parse_mode="HTML",
        )
    else:
        await message.answer(
            t("csv_import_success", count=count),
            reply_markup=get_questions_menu_keyboard(),
            parse_mode="HTML",
        )
