from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from bot.core.constants import (
    MGR_COMPARE_TEXTS,
    MGR_EXPORT_TEXTS,
    MGR_STATS_TEXTS,
    OPERATOR_CANCEL_TEXTS,
    OP_INTERNET_TEXTS,
    OP_MOBILE_TEXTS,
)
from bot.keyboards.dynamic_selectors import branch_selector, dealer_selector, rate_plan_selector, period_selector
from bot.keyboards.roles import cancel_keyboard
from bot.utils.role_menu import reply_menu_for_user
from bot.utils.role_access import ensure_roles
from backend.repositories.user_repository import UserRepo
from backend.services.manual_sale_service import (
    create_manual_internet_sale,
    create_manual_mobile_sale,
)
from backend.services.excel_export_service import build_period_export
from backend.models import (
    InternetSale,
    MobileSale,
    ServiceType,
    UserRole,
    ReportPeriod,
    Branch,
    Dealer,
    RatePlan,
)
from bot.states.roles import OperatorInternetState, OperatorMobileState, ManagerStatsState, ManagerExportState, ManagerCompareState

router = Router()

_SALES_ROLES = (UserRole.OPERATOR, UserRole.MANAGER)
_MANAGER_ONLY = (UserRole.MANAGER,)


def tr(lang: str, uz: str, ru: str) -> str:
    return ru if lang == "ru" else uz


def _parse_callback_id(call_data: str, prefix: str) -> int | None:
    if not call_data.startswith(prefix):
        return None
    try:
        return int(call_data.split(":")[2])
    except (IndexError, ValueError):
        return None

# ================================
# CANCEL BUTTON
# ================================
@router.message(F.text.in_(OPERATOR_CANCEL_TEXTS))
async def cancel_handler(message: Message, state: FSMContext, session: AsyncSession):
    if not await ensure_roles(message, session, *_SALES_ROLES):
        return
    if not await state.get_state():
        return
    await state.clear()
    menu, lang = await reply_menu_for_user(session, message.from_user.id)
    await message.answer(
        tr(lang, "❌ Amal bekor qilindi.", "❌ Действие отменено."),
        reply_markup=menu,
    )

# ================================
# INTERNET (шпд): Filial → Bo'lim → MSISDN → Tarif
# ================================
@router.message(F.text.in_(OP_INTERNET_TEXTS))
async def start_internet_sale(message: Message, state: FSMContext, session: AsyncSession):
    if not await ensure_roles(message, session, *_SALES_ROLES):
        return
    await state.clear()
    user = await UserRepo.get_user(session, message.from_user.id)
    lang = user.lang if user else "uz"
    kb = await branch_selector(session)
    await message.answer(
        tr(lang, "🏢 Filialni tanlang:", "🏢 Выберите филиал:"),
        reply_markup=kb,
    )
    await state.set_state(OperatorInternetState.choosing_branch)

@router.callback_query(OperatorInternetState.choosing_branch, F.data.startswith("sel:branch_page:"))
async def internet_branch_page_selected(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    page = _parse_callback_id(call.data, "sel:branch_page:")
    if page is None:
        await call.answer("⚠️ Noto'g'ri sahifa kodi", show_alert=True)
        return
    kb = await branch_selector(session, page=page)
    await call.message.edit_text("🏢 Filialni tanlang:", reply_markup=kb)
    await call.answer()

@router.callback_query(OperatorInternetState.choosing_branch, F.data.startswith("sel:branch:"))
async def internet_branch_selected(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    branch_id = _parse_callback_id(call.data, "sel:branch:")
    if branch_id is None:
        await call.answer("⚠️ Noto'g'ri filial kodi", show_alert=True)
        return
    if branch_id == 0:
        await call.answer("🏢 Filial yo'q", show_alert=True)
        return
    await state.update_data(branch_id=branch_id)
    user = await UserRepo.get_user(session, call.from_user.id)
    lang = user.lang if user else "uz"
    await call.message.edit_text("✅ Filial tanlandi.")
    await call.message.answer(
        "🏛 Bo'lim / RUT nomini kiriting (masalan: Фаришский РУТ):",
        reply_markup=cancel_keyboard(lang),
    )
    await state.set_state(OperatorInternetState.entering_department)


@router.message(OperatorInternetState.entering_department)
async def internet_department(message: Message, state: FSMContext, session: AsyncSession):
    dept = (message.text or "").strip()
    if not dept:
        await message.answer("⚠️ Iltimos, bo'lim (DEPARTMENTS) nomini kiriting.")
        return
    await state.update_data(department_name_raw=dept)
    user = await UserRepo.get_user(session, message.from_user.id)
    lang = user.lang if user else "uz"
    await message.answer(
        "📱 Akkaunt yoki MSISDN kiriting (masalan: m1460972):",
        reply_markup=cancel_keyboard(lang),
    )
    await state.set_state(OperatorInternetState.entering_msisdn)


@router.message(OperatorInternetState.entering_msisdn)
async def internet_msisdn(message: Message, state: FSMContext, session: AsyncSession):
    msisdn = message.text.strip()
    if not msisdn:
        await message.answer("⚠️ Iltimos, MSISDN kiriting.")
        return
    await state.update_data(msisdn=msisdn)
    kb = await rate_plan_selector(session, ServiceType.INTERNET)
    if kb.inline_keyboard and kb.inline_keyboard[0][0].callback_data != "sel:rateplan:0":
        await message.answer("📶 Tarif rejasini tanlang:", reply_markup=kb)
        await state.set_state(OperatorInternetState.choosing_rate_plan)
    else:
        # Tarif yo'q — darhol saqlash
        await state.update_data(rate_plan_id=None)
        await _save_internet_sale(message, state, session)

@router.callback_query(OperatorInternetState.choosing_rate_plan, F.data.startswith("sel:rateplan:"))
async def internet_rate_selected(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    rp_id = _parse_callback_id(call.data, "sel:rateplan:")
    if rp_id is None:
        await call.answer("⚠️ Noto'g'ri tarif kodi", show_alert=True)
        return
    await state.update_data(rate_plan_id=rp_id if rp_id > 0 else None)
    await call.message.delete()
    await _save_internet_sale(call.message, state, session, operator_id=call.from_user.id)

async def _save_internet_sale(message: Message, state: FSMContext, session: AsyncSession, operator_id: int = None):
    data = await state.get_data()
    tg_id = operator_id or message.from_user.id
    await create_manual_internet_sale(
        session,
        operator_tg_id=tg_id,
        branch_id=data["branch_id"],
        department_name_raw=data.get("department_name_raw", ""),
        msisdn=data.get("msisdn", ""),
        rate_plan_id=data.get("rate_plan_id"),
    )
    menu, _ = await reply_menu_for_user(session, tg_id)
    await message.answer("✅ Internet sotuv muvaffaqiyatli saqlandi!", reply_markup=menu)
    await state.clear()


# ================================
# MOBILE (номер 1): Diler → Filial → MSISDN → Tarif
# ================================
@router.message(F.text.in_(OP_MOBILE_TEXTS))
async def start_mobile_sale(message: Message, state: FSMContext, session: AsyncSession):
    if not await ensure_roles(message, session, *_SALES_ROLES):
        return
    await state.clear()
    user = await UserRepo.get_user(session, message.from_user.id)
    lang = user.lang if user else "uz"
    kb = await dealer_selector(session)
    await message.answer(
        tr(lang, "🏪 Dilerni tanlang:", "🏪 Выберите дилера:"),
        reply_markup=kb,
    )
    await state.set_state(OperatorMobileState.choosing_dealer)

@router.callback_query(OperatorMobileState.choosing_dealer, F.data.startswith("sel:dealer_page:"))
async def mobile_dealer_page_selected(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    page = _parse_callback_id(call.data, "sel:dealer_page:")
    if page is None:
        await call.answer("⚠️ Noto'g'ri sahifa kodi", show_alert=True)
        return
    kb = await dealer_selector(session, page=page)
    await call.message.edit_text("📱 Dilerni tanlang:", reply_markup=kb)
    await call.answer()

@router.callback_query(OperatorMobileState.choosing_dealer, F.data.startswith("sel:dealer:"))
async def mobile_dealer_selected(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    dealer_id = _parse_callback_id(call.data, "sel:dealer:")
    if dealer_id is None:
        await call.answer("⚠️ Noto'g'ri diler kodi", show_alert=True)
        return
    if dealer_id == 0:
        await call.answer("🏪 Diler yo'q", show_alert=True)
        return
    dealer = await session.get(Dealer, dealer_id)
    if not dealer:
        await call.answer("⚠️ Diler topilmadi", show_alert=True)
        return

    user = await UserRepo.get_user(session, call.from_user.id)
    lang = user.lang if user else "uz"
    data_update = {"dealer_id": dealer_id}

    if dealer.branch_id:
        data_update["branch_id"] = dealer.branch_id
        await state.update_data(**data_update)
        await call.message.edit_text("✅ Diler tanlandi.")
        await call.message.answer(
            "📱 Mijozning yangi raqamini kiriting:",
            reply_markup=cancel_keyboard(lang),
        )
        await state.set_state(OperatorMobileState.entering_msisdn)
        return

    await state.update_data(**data_update)
    kb = await branch_selector(session)
    await call.message.edit_text("🏢 Filialni tanlang:", reply_markup=kb)
    await state.set_state(OperatorMobileState.choosing_branch)


@router.callback_query(OperatorMobileState.choosing_branch, F.data.startswith("sel:branch_page:"))
async def mobile_branch_page_selected(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    page = _parse_callback_id(call.data, "sel:branch_page:")
    if page is None:
        await call.answer("⚠️ Noto'g'ri sahifa kodi", show_alert=True)
        return
    kb = await branch_selector(session, page=page)
    await call.message.edit_text("🏢 Filialni tanlang:", reply_markup=kb)
    await call.answer()

@router.callback_query(OperatorMobileState.choosing_branch, F.data.startswith("sel:branch:"))
async def mobile_branch_selected(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    branch_id = _parse_callback_id(call.data, "sel:branch:")
    if branch_id is None:
        await call.answer("⚠️ Noto'g'ri filial kodi", show_alert=True)
        return
    if branch_id == 0:
        await call.answer("🏢 Filial yo'q", show_alert=True)
        return
    await state.update_data(branch_id=branch_id)
    user = await UserRepo.get_user(session, call.from_user.id)
    lang = user.lang if user else "uz"
    await call.message.edit_text("✅ Filial tanlandi.")
    await call.message.answer(
        "📱 Mijozning yangi raqamini kiriting:",
        reply_markup=cancel_keyboard(lang),
    )
    await state.set_state(OperatorMobileState.entering_msisdn)

@router.message(OperatorMobileState.entering_msisdn)
async def mobile_msisdn(message: Message, state: FSMContext, session: AsyncSession):
    msisdn = message.text.strip()
    if not msisdn:
        await message.answer("⚠️ Iltimos, MSISDN kiriting.")
        return
    await state.update_data(msisdn=msisdn)
    kb = await rate_plan_selector(session, ServiceType.MOBILE)
    if kb.inline_keyboard and kb.inline_keyboard[0][0].callback_data != "sel:rateplan:0":
        await message.answer("📶 Tarif rejasini tanlang:", reply_markup=kb)
        await state.set_state(OperatorMobileState.choosing_rate_plan)
    else:
        # Tarif yo'q — darhol saqlash
        await state.update_data(rate_plan_id=None)
        await _save_mobile_sale(message, state, session)

@router.callback_query(OperatorMobileState.choosing_rate_plan, F.data.startswith("sel:rateplan:"))
async def mobile_rate_selected(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    rp_id = _parse_callback_id(call.data, "sel:rateplan:")
    if rp_id is None:
        await call.answer("⚠️ Noto'g'ri tarif kodi", show_alert=True)
        return
    await state.update_data(rate_plan_id=rp_id if rp_id > 0 else None)
    await call.message.delete()
    await _save_mobile_sale(call.message, state, session, operator_id=call.from_user.id)

async def _save_mobile_sale(message: Message, state: FSMContext, session: AsyncSession, operator_id: int = None):
    data = await state.get_data()
    tg_id = operator_id or message.from_user.id
    await create_manual_mobile_sale(
        session,
        operator_tg_id=tg_id,
        dealer_id=data["dealer_id"],
        branch_id=data["branch_id"],
        msisdn=data.get("msisdn", ""),
        rate_plan_id=data.get("rate_plan_id"),
    )
    menu, _ = await reply_menu_for_user(session, tg_id)
    await message.answer("✅ Mobil sotuv muvaffaqiyatli saqlandi!", reply_markup=menu)
    await state.clear()


# ================================
# MANAGER STATS (Batafsil statistika)
# ================================
@router.message(F.text.in_(MGR_STATS_TEXTS))
async def manager_stats(message: Message, state: FSMContext, session: AsyncSession):
    if not await ensure_roles(message, session, *_MANAGER_ONLY):
        return
    await state.clear()
    kb = await period_selector(session)
    await message.answer("📊 Qaysi oy uchun statistika kerak?", reply_markup=kb)
    await state.set_state(ManagerStatsState.choosing_period)

@router.callback_query(ManagerStatsState.choosing_period, F.data.startswith("sel:period:"))
async def stats_period_selected(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    period_id = _parse_callback_id(call.data, "sel:period:")
    if period_id is None:
        await call.answer("⚠️ Noto'g'ri davr kodi", show_alert=True)
        return
    if period_id == 0:
        await call.answer("📅 Davr yo'q!", show_alert=True)
        return
        
    stmt = select(ReportPeriod).where(ReportPeriod.id == period_id)
    period = (await session.execute(stmt)).scalar()
    
    # Umumiy sonlar
    inet_count = (await session.execute(
        select(func.count(InternetSale.id)).where(InternetSale.period_id == period_id)
    )).scalar() or 0
    
    mob_count = (await session.execute(
        select(func.count(MobileSale.id)).where(MobileSale.period_id == period_id)
    )).scalar() or 0
    
    total = inet_count + mob_count
    inet_percent = round((inet_count / total * 100), 1) if total > 0 else 0
    mob_percent = round((mob_count / total * 100), 1) if total > 0 else 0
    
    txt = f"📊 <b>{period.name} YAKUNIY STATISTIKASI</b>\n"
    txt += f"━━━━━━━━━━━━━━━━━━━━\n\n"
    
    txt += f"📈 <b>UMUMIY KO'RSATKICHLAR</b>\n"
    txt += f"🔹 Jami sotuvlar: <b>{total}</b> ta\n"
    txt += f"   └ 🌐 Internet: <b>{inet_count}</b> ta ({inet_percent}%)\n"
    txt += f"   └ 📱 Mobil: <b>{mob_count}</b> ta ({mob_percent}%)\n"
    
    # Top 5 filiallar (internet)
    top_branches_inet = (await session.execute(
        select(
            func.coalesce(Branch.name, InternetSale.branch_name_raw).label('b_name'),
            func.count(InternetSale.id).label('cnt')
        )
        .select_from(InternetSale)
        .outerjoin(Branch, InternetSale.branch_id == Branch.id)
        .where(InternetSale.period_id == period_id)
        .group_by(func.coalesce(Branch.name, InternetSale.branch_name_raw))
        .having(func.coalesce(Branch.name, InternetSale.branch_name_raw) != '')
        .having(func.coalesce(Branch.name, InternetSale.branch_name_raw).is_not(None))
        .order_by(desc('cnt')).limit(5)
    )).all()
    
    if top_branches_inet:
        txt += f"\n━━━━━━━━━━━━━━━━━━━━\n"
        txt += f"🏢 <b>TOP FILIALLAR (Internet):</b>\n"
        for i, (name, cnt) in enumerate(top_branches_inet, 1):
            txt += f"  {i}. {name} • <b>{cnt}</b> ta\n"
    
    # Top 5 dilerlar (mobil)
    top_dealers = (await session.execute(
        select(
            func.coalesce(Dealer.name, MobileSale.dealer_name_raw).label('d_name'),
            func.count(MobileSale.id).label('cnt')
        )
        .select_from(MobileSale)
        .outerjoin(Dealer, MobileSale.dealer_id == Dealer.id)
        .where(MobileSale.period_id == period_id)
        .group_by(func.coalesce(Dealer.name, MobileSale.dealer_name_raw))
        .having(func.coalesce(Dealer.name, MobileSale.dealer_name_raw) != '')
        .having(func.coalesce(Dealer.name, MobileSale.dealer_name_raw).is_not(None))
        .order_by(desc('cnt')).limit(5)
    )).all()
    
    if top_dealers:
        txt += f"\n🏪 <b>TOP DILERLAR (Mobil):</b>\n"
        for i, (name, cnt) in enumerate(top_dealers, 1):
            txt += f"  {i}. {name} • <b>{cnt}</b> ta\n"
    
    # Top 5 operatorlar (ikkala tur bo'yicha)
    top_ops_inet = (await session.execute(
        select(InternetSale.navi_user, func.count(InternetSale.id).label('cnt'))
        .where(InternetSale.period_id == period_id, InternetSale.navi_user != '')
        .group_by(InternetSale.navi_user)
        .order_by(desc('cnt')).limit(5)
    )).all()
    
    top_ops_mob = (await session.execute(
        select(MobileSale.navi_user, func.count(MobileSale.id).label('cnt'))
        .where(MobileSale.period_id == period_id, MobileSale.navi_user != '')
        .group_by(MobileSale.navi_user)
        .order_by(desc('cnt')).limit(5)
    )).all()
    
    if top_ops_inet or top_ops_mob:
        txt += f"\n━━━━━━━━━━━━━━━━━━━━\n"
        
    if top_ops_inet:
        txt += f"👤 <b>TOP OPERATORLAR (Internet):</b>\n"
        for i, (name, cnt) in enumerate(top_ops_inet, 1):
            txt += f"  {i}. {name} • <b>{cnt}</b> ta\n"
            
    if top_ops_mob:
        if top_ops_inet:
            txt += "\n"
        txt += f"👤 <b>TOP OPERATORLAR (Mobil):</b>\n"
        for i, (name, cnt) in enumerate(top_ops_mob, 1):
            txt += f"  {i}. {name} • <b>{cnt}</b> ta\n"
    
    # Top 5 tariflar
    top_tarifs_inet = (await session.execute(
        select(
            func.coalesce(RatePlan.name, InternetSale.rate_plan_raw).label('r_name'),
            func.count(InternetSale.id).label('cnt')
        )
        .select_from(InternetSale)
        .outerjoin(RatePlan, InternetSale.rate_plan_id == RatePlan.id)
        .where(InternetSale.period_id == period_id)
        .group_by(func.coalesce(RatePlan.name, InternetSale.rate_plan_raw))
        .having(func.coalesce(RatePlan.name, InternetSale.rate_plan_raw) != '')
        .having(func.coalesce(RatePlan.name, InternetSale.rate_plan_raw).is_not(None))
        .order_by(desc('cnt')).limit(5)
    )).all()
    
    if top_tarifs_inet:
        txt += f"\n━━━━━━━━━━━━━━━━━━━━\n"
        txt += f"📶 <b>TOP TARIFLAR (Internet):</b>\n"
        for i, (name, cnt) in enumerate(top_tarifs_inet, 1):
            txt += f"  {i}. {name} • <b>{cnt}</b> ta\n"
    

    await call.message.edit_text(txt, parse_mode="HTML")
    await state.clear()


# ================================
# MANAGER EXPORT
# ================================
@router.message(F.text.in_(MGR_EXPORT_TEXTS))
async def manager_export(message: Message, state: FSMContext, session: AsyncSession):
    if not await ensure_roles(message, session, *_MANAGER_ONLY):
        return
    await state.clear()
    kb = await period_selector(session)
    await message.answer("📤 Qaysi oyni eksport qilmoqchisiz?", reply_markup=kb)
    await state.set_state(ManagerExportState.choosing_period)

@router.callback_query(ManagerExportState.choosing_period, F.data.startswith("sel:period:"))
async def export_period_selected(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    period_id = _parse_callback_id(call.data, "sel:period:")
    if period_id is None:
        await call.answer("⚠️ Noto'g'ri davr kodi", show_alert=True)
        return
    if period_id == 0:
         await call.answer("📅 Davr yo'q!", show_alert=True)
         return
         
    await call.message.edit_text("⏳ Excel fayli shakllantirilmoqda...")
    export_path = await build_period_export(session, period_id)
    from aiogram.types import FSInputFile
    doc = FSInputFile(export_path)
    menu, _ = await reply_menu_for_user(session, call.from_user.id)
    await call.message.answer_document(doc, caption="✅ Eksport tayyor!", reply_markup=menu)
    await call.message.delete()
    await state.clear()


# ================================
# MANAGER COMPARE & PERIODS
# ================================
@router.message(F.text.in_(MGR_COMPARE_TEXTS))
async def manager_compare(message: Message, state: FSMContext, session: AsyncSession):
    if not await ensure_roles(message, session, *_MANAGER_ONLY):
        return
    await state.clear()
    kb = await period_selector(session)
    if kb.inline_keyboard and kb.inline_keyboard[0][0].callback_data == "sel:period:0":
        await message.answer("📈 Taqqoslash uchun tizimda davrlar mavjud emas.")
        return
    await message.answer("📈 Taqqoslash uchun 1-oyni tanlang:", reply_markup=kb)
    await state.set_state(ManagerCompareState.choosing_first_period)

@router.callback_query(ManagerCompareState.choosing_first_period, F.data.startswith("sel:period:"))
async def compare_first_period_selected(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    period_id = _parse_callback_id(call.data, "sel:period:")
    if period_id is None:
        await call.answer("⚠️ Noto'g'ri davr kodi", show_alert=True)
        return
    if period_id == 0:
         await call.answer("📅 Davr yo'q!", show_alert=True)
         return
    await state.update_data(p1_id=period_id)
    kb = await period_selector(session)
    await call.message.edit_text("📈 Endi taqqoslash uchun 2-oyni tanlang:", reply_markup=kb)
    await state.set_state(ManagerCompareState.choosing_second_period)

@router.callback_query(ManagerCompareState.choosing_second_period, F.data.startswith("sel:period:"))
async def compare_second_period_selected(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    p2_id = _parse_callback_id(call.data, "sel:period:")
    if p2_id is None:
        await call.answer("⚠️ Noto'g'ri davr kodi", show_alert=True)
        return
    if p2_id == 0:
         await call.answer("📅 Davr yo'q!", show_alert=True)
         return
         
    data = await state.get_data()
    p1_id = data.get('p1_id')
    
    if p1_id == p2_id:
        await call.answer("⚠️ Bir xil oyni o'z-o'zi bilan taqqoslab bo'lmaydi! Boshqa oy tanlang.", show_alert=True)
        return
        
    await call.message.edit_text("⏳ Taqqoslanmoqda...")
        
    stmt = select(ReportPeriod).where(ReportPeriod.id.in_([p1_id, p2_id]))
    periods = (await session.execute(stmt)).scalars().all()
    
    if len(periods) < 2:
        await call.answer("⚠️ Xatolik: Davrlar topilmadi.", show_alert=True)
        await state.clear()
        return
        
    p1 = next((p for p in periods if p.id == p1_id), None)
    p2 = next((p for p in periods if p.id == p2_id), None)
    
    p1_inet = (await session.execute(select(func.count(InternetSale.id)).where(InternetSale.period_id == p1.id))).scalar() or 0
    p2_inet = (await session.execute(select(func.count(InternetSale.id)).where(InternetSale.period_id == p2.id))).scalar() or 0
    inet_diff = p1_inet - p2_inet
    inet_pct = round((inet_diff / p2_inet * 100), 1) if p2_inet > 0 else 0
    inet_icon = "📈" if inet_diff > 0 else ("📉" if inet_diff < 0 else "➖")
    
    p1_mob = (await session.execute(select(func.count(MobileSale.id)).where(MobileSale.period_id == p1.id))).scalar() or 0
    p2_mob = (await session.execute(select(func.count(MobileSale.id)).where(MobileSale.period_id == p2.id))).scalar() or 0
    mob_diff = p1_mob - p2_mob
    mob_pct = round((mob_diff / p2_mob * 100), 1) if p2_mob > 0 else 0
    mob_icon = "📈" if mob_diff > 0 else ("📉" if mob_diff < 0 else "➖")
    
    p1_total = p1_inet + p1_mob
    p2_total = p2_inet + p2_mob
    total_diff = p1_total - p2_total
    total_pct = round((total_diff / p2_total * 100), 1) if p2_total > 0 else 0
    total_icon = "📈" if total_diff > 0 else ("📉" if total_diff < 0 else "➖")
    
    txt = f"📊 <b>Oylarni taqqoslash:</b>\n<i>{p1.name} 🆚 {p2.name}</i>\n\n"
    
    txt += f"📋 <b>Umumiy:</b>\n"
    txt += f"  {p1.name}: <b>{p1_total}</b> ta\n"
    txt += f"  {p2.name}: <b>{p2_total}</b> ta\n"
    txt += f"  {total_icon} Farq: <b>{abs(total_diff)}</b> ta ({'+' if total_diff >= 0 else ''}{total_pct}%)\n\n"
    
    txt += f"🌐 <b>Internet:</b>\n"
    txt += f"  {p1.name}: <b>{p1_inet}</b> ta\n"
    txt += f"  {p2.name}: <b>{p2_inet}</b> ta\n"
    txt += f"  {inet_icon} Farq: <b>{abs(inet_diff)}</b> ta ({'+' if inet_diff >= 0 else ''}{inet_pct}%)\n\n"
    
    txt += f"📱 <b>Mobil:</b>\n"
    txt += f"  {p1.name}: <b>{p1_mob}</b> ta\n"
    txt += f"  {p2.name}: <b>{p2_mob}</b> ta\n"
    txt += f"  {mob_icon} Farq: <b>{abs(mob_diff)}</b> ta ({'+' if mob_diff >= 0 else ''}{mob_pct}%)\n\n"
    
    # Top o'sgan filiallar (internet)
    p1_by_branch = dict((await session.execute(
        select(
            func.coalesce(Branch.name, InternetSale.branch_name_raw).label('b_name'),
            func.count(InternetSale.id).label('cnt')
        )
        .select_from(InternetSale)
        .outerjoin(Branch, InternetSale.branch_id == Branch.id)
        .where(InternetSale.period_id == p1.id)
        .group_by(func.coalesce(Branch.name, InternetSale.branch_name_raw))
        .having(func.coalesce(Branch.name, InternetSale.branch_name_raw) != '')
        .having(func.coalesce(Branch.name, InternetSale.branch_name_raw).is_not(None))
    )).all())
    
    p2_by_branch = dict((await session.execute(
        select(
            func.coalesce(Branch.name, InternetSale.branch_name_raw).label('b_name'),
            func.count(InternetSale.id).label('cnt')
        )
        .select_from(InternetSale)
        .outerjoin(Branch, InternetSale.branch_id == Branch.id)
        .where(InternetSale.period_id == p2.id)
        .group_by(func.coalesce(Branch.name, InternetSale.branch_name_raw))
        .having(func.coalesce(Branch.name, InternetSale.branch_name_raw) != '')
        .having(func.coalesce(Branch.name, InternetSale.branch_name_raw).is_not(None))
    )).all())
    
    all_branches = set(list(p1_by_branch.keys()) + list(p2_by_branch.keys()))
    branch_diffs = []
    for br in all_branches:
        c1 = p1_by_branch.get(br, 0)
        c2 = p2_by_branch.get(br, 0)
        branch_diffs.append((br, c1, c2, c1 - c2))
    
    branch_diffs.sort(key=lambda x: x[3], reverse=True)
    
    if branch_diffs:
        txt += f"🏢 <b>Filiallar bo'yicha (Internet):</b>\n"
        for br, c1, c2, diff in branch_diffs[:5]:
            icon = "🔺" if diff > 0 else ("🔻" if diff < 0 else "➖")
            txt += f"  {icon} {br}: {c2} → {c1} ({'+' if diff >= 0 else ''}{diff})\n"
    
    await call.message.edit_text(txt, parse_mode="HTML")
    await state.clear()
