import csv
import io
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy import select, func, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.question import Question, TestSet
from app.config import get_settings

settings = get_settings()


class QuestionService:
    @staticmethod
    async def count_user_questions(session: AsyncSession, owner_id: str) -> int:
        stmt = select(func.count(Question.id)).where(Question.owner_id == owner_id)
        result = await session.execute(stmt)
        return result.scalar_one() or 0

    @staticmethod
    async def count_user_sets(session: AsyncSession, owner_id: str) -> int:
        stmt = select(func.count(TestSet.id)).where(TestSet.owner_id == owner_id)
        result = await session.execute(stmt)
        return result.scalar_one() or 0

    @staticmethod
    async def get_user_questions(
        session: AsyncSession,
        owner_id: str,
        page: int = 1,
        page_size: int = 5,
        search_query: Optional[str] = None,
        test_set_id: Optional[str] = None,
    ) -> Tuple[List[Question], int]:
        """Tenant-isolated question listing with pagination and search."""
        query = select(Question).where(Question.owner_id == owner_id)

        if search_query:
            query = query.where(Question.text.ilike(f"%{search_query.strip()}%"))
        if test_set_id:
            query = query.where(Question.test_set_id == test_set_id)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        count_res = await session.execute(count_query)
        total = count_res.scalar_one() or 0

        # Paginate
        offset = (page - 1) * page_size
        stmt = query.order_by(Question.created_at.desc()).offset(offset).limit(page_size)
        result = await session.execute(stmt)
        return list(result.scalars().all()), total

    @staticmethod
    async def get_question_by_id(
        session: AsyncSession, question_id: str, owner_id: str
    ) -> Optional[Question]:
        """Strictly tenant-isolated fetch of a single question."""
        stmt = select(Question).where(
            Question.id == question_id, Question.owner_id == owner_id
        )
        result = await session.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def create_question(
        session: AsyncSession,
        owner_id: str,
        text: str,
        options: List[str],
        correct_option_id: int,
        explanation: str = "",
        test_set_id: Optional[str] = None,
    ) -> Tuple[Optional[Question], Optional[str]]:
        """Validate limits and create question strictly for owner."""
        count = await QuestionService.count_user_questions(session, owner_id)
        if count >= settings.MAX_QUESTIONS_PER_USER:
            return None, "question_quota_exceeded"

        # Validate limits against Telegram quiz-poll Bot API constraints:
        # question <= 300 chars, option <= 100, explanation <= 200, 2..10 options
        clean_text = text.strip()
        if not (1 <= len(clean_text) <= 300):
            return None, "add_q_text_too_long"

        if not (2 <= len(options) <= 10):
            return None, "add_q_options_invalid"

        clean_options = [opt.strip() for opt in options]
        for opt in clean_options:
            if not (1 <= len(opt) <= 100):
                return None, "add_q_options_invalid"

        if not (0 <= correct_option_id < len(clean_options)):
            return None, "add_q_options_invalid"

        clean_explanation = (explanation or "").strip()
        if len(clean_explanation) > 200:
            return None, "add_q_explanation_too_long"

        # Verify test set ownership if specified
        if test_set_id:
            set_stmt = select(TestSet).where(
                TestSet.id == test_set_id, TestSet.owner_id == owner_id
            )
            set_res = await session.execute(set_stmt)
            if not set_res.scalars().first():
                test_set_id = None

        question = Question(
            owner_id=owner_id,
            test_set_id=test_set_id,
            text=clean_text,
            options=clean_options,
            correct_option_id=correct_option_id,
            explanation=clean_explanation,
        )
        session.add(question)
        await session.commit()
        await session.refresh(question)
        return question, None

    @staticmethod
    async def delete_question(
        session: AsyncSession, question_id: str, owner_id: str
    ) -> bool:
        """Tenant-isolated question deletion."""
        stmt = delete(Question).where(
            Question.id == question_id, Question.owner_id == owner_id
        )
        res = await session.execute(stmt)
        await session.commit()
        return res.rowcount > 0

    @staticmethod
    async def get_user_sets(session: AsyncSession, owner_id: str) -> List[TestSet]:
        stmt = (
            select(TestSet)
            .where(TestSet.owner_id == owner_id)
            .order_by(TestSet.created_at.desc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_set_by_id(
        session: AsyncSession, set_id: str, owner_id: str
    ) -> Optional[TestSet]:
        stmt = select(TestSet).where(TestSet.id == set_id, TestSet.owner_id == owner_id)
        result = await session.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def create_test_set(
        session: AsyncSession, owner_id: str, name: str, description: str = ""
    ) -> TestSet:
        test_set = TestSet(
            owner_id=owner_id,
            name=name.strip()[:100],
            description=description.strip()[:255],
        )
        session.add(test_set)
        await session.commit()
        await session.refresh(test_set)
        return test_set

    @staticmethod
    async def delete_test_set(
        session: AsyncSession, set_id: str, owner_id: str
    ) -> bool:
        stmt = delete(TestSet).where(
            TestSet.id == set_id, TestSet.owner_id == owner_id
        )
        res = await session.execute(stmt)
        await session.commit()
        return res.rowcount > 0

    @staticmethod
    async def import_questions_from_csv(
        session: AsyncSession, owner_id: str, csv_content: str
    ) -> Tuple[int, Optional[str]]:
        """Parse CSV and import questions safely for owner."""
        f = io.StringIO(csv_content.strip())
        sample = f.read(2048)
        f.seek(0)

        # Detect delimiter (comma or semicolon)
        delimiter = ";" if ";" in sample and "," not in sample else ","
        reader = csv.reader(f, delimiter=delimiter)

        rows = list(reader)
        if not rows:
            return 0, "CSV fayl bo'sh."

        # Check if first row is header
        header = [h.strip().lower() for h in rows[0]]
        start_idx = 1 if "question" in header[0] else 0

        imported_count = 0
        current_count = await QuestionService.count_user_questions(session, owner_id)

        # Cache existing test sets for owner
        existing_sets = await QuestionService.get_user_sets(session, owner_id)
        sets_map = {s.name.lower(): s.id for s in existing_sets}

        for i, row in enumerate(rows[start_idx:], start=start_idx + 1):
            if not row or not any(row):
                continue
            if current_count + imported_count >= settings.MAX_QUESTIONS_PER_USER:
                break

            # Expected format:
            # col 0: question text
            # col 1..N-3: options
            # col N-2: correct_option (1-based index or option text)
            # col N-1: explanation (optional)
            # col N: set_name (optional)
            if len(row) < 4:
                return imported_count, f"{i}-qatorda ustunlar yetarli emas."

            q_text = row[0].strip()
            if not (1 <= len(q_text) <= 300):
                return imported_count, f"{i}-qatorda savol matni 1-300 belgi bo'lishi kerak."

            # Determine where options end and metadata starts
            # If standard 8 columns: q, opt1, opt2, opt3, opt4, correct, expl, set
            if len(row) == 8:
                raw_options = [row[1], row[2], row[3], row[4]]
                correct_raw = row[5].strip()
                explanation = row[6].strip()[:200]
                set_name = row[7].strip()
            elif len(row) >= 5:
                # Dynamic options
                set_name = row[-1].strip() if len(row) >= 6 else ""
                explanation = row[-2].strip()[:200] if len(row) >= 5 else ""
                correct_raw = row[-3].strip() if len(row) >= 5 else row[-1].strip()
                raw_options = row[1:-3] if len(row) >= 6 else row[1:-2]
            else:
                return imported_count, f"{i}-qatorda format noto'g'ri."

            options = [o.strip() for o in raw_options if o.strip()]
            if not (2 <= len(options) <= 10):
                return imported_count, f"{i}-qatorda variantlar soni 2 dan 10 gacha bo'lishi kerak."

            # Determine correct_option_id
            correct_id = -1
            if correct_raw.isdigit():
                idx = int(correct_raw)
                if 1 <= idx <= len(options):
                    correct_id = idx - 1
                elif 0 <= idx < len(options):
                    correct_id = idx
            else:
                for idx, opt in enumerate(options):
                    if opt.lower() == correct_raw.lower():
                        correct_id = idx
                        break

            if correct_id < 0 or correct_id >= len(options):
                return imported_count, f"{i}-qatorda to'g'ri javob topilmadi: '{correct_raw}'."

            # Resolve or create test set if set_name provided
            test_set_id = None
            if set_name:
                set_key = set_name.lower()
                if set_key in sets_map:
                    test_set_id = sets_map[set_key]
                else:
                    new_set = await QuestionService.create_test_set(session, owner_id, set_name)
                    test_set_id = new_set.id
                    sets_map[set_key] = test_set_id

            q = Question(
                owner_id=owner_id,
                test_set_id=test_set_id,
                text=q_text,
                options=options,
                correct_option_id=correct_id,
                explanation=explanation,
            )
            session.add(q)
            imported_count += 1

        await session.commit()
        return imported_count, None
